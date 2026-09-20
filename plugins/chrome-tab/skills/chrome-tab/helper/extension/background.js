// chrome-tab helper: the extension half of chrome-tab's bridge.
//
// chrome-tab is a command-line tool. From outside the browser it can reach Chrome only
// through AppleScript, and AppleScript has three gaps. It has windows and tabs but no tab
// groups. Its "move" closes the tab and opens a blank one elsewhere. And every URL it sets
// asks macOS to bring Chrome forward. This service worker does those jobs through the
// extension API instead.
//
// It talks to a native-messaging host that Chrome starts for it (com.jacob_skills.chrome_tab).
// The host relays requests from a local Unix socket that only the user's account can open.
// The worker acts only on those requests, and it never reads page contents.

const HOST = "com.jacob_skills.chrome_tab";
const VERSION = chrome.runtime.getManifest().version;
const COLORS = ["blue", "red", "yellow", "green", "pink", "purple", "cyan", "orange", "grey"];

let port = null;

function connect() {
  if (port) return;
  let p;
  try {
    p = chrome.runtime.connectNative(HOST);
  } catch (e) {
    return; // the reconnect alarm tries again
  }
  port = p;
  p.onMessage.addListener(onRequest);
  p.onDisconnect.addListener(() => {
    void chrome.runtime.lastError; // e.g. "Specified native messaging host not found."
    if (port === p) port = null;
  });
  p.postMessage({ type: "hello", version: VERSION, extensionId: chrome.runtime.id });
}

// An open native port keeps this worker alive (Chrome 105+). If the host exits, Chrome
// may stop the worker; this alarm wakes it within a minute to reconnect.
chrome.alarms.create("chrome-tab-reconnect", { periodInMinutes: 1 });
chrome.alarms.onAlarm.addListener(connect);
chrome.runtime.onStartup.addListener(connect);
chrome.runtime.onInstalled.addListener(connect);
connect();

async function onRequest(msg) {
  if (!msg || msg.id === undefined) return;
  let reply;
  try {
    const handler = HANDLERS[msg.cmd];
    if (!handler) throw new Error(`unknown command: ${msg.cmd}`);
    reply = { id: msg.id, ok: true, result: await handler(msg.args || {}) };
  } catch (e) {
    reply = { id: msg.id, ok: false, error: String((e && e.message) || e) };
  }
  try {
    if (port) port.postMessage(reply);
  } catch (e) {
    // the host went away mid-request; chrome-tab times out and falls back
  }
}

// Same rule as chrome-tab's AppleScript path: an open copy counts even after an in-page
// link added a #fragment to its address.
function sameUrl(tabUrl, url) {
  return tabUrl === url || tabUrl.startsWith(url + "#");
}

function colorFor(title) {
  let h = 5381;
  for (const ch of title.toLowerCase()) h = ((h * 33) ^ ch.codePointAt(0)) >>> 0;
  return COLORS[h % COLORS.length];
}

function describeGroup(g, created) {
  return { id: g.id, title: g.title || "", color: g.color, collapsed: g.collapsed, created };
}

// Put a tab into the group titled `title` in its window, making the group if it's missing.
async function putInGroup(tabId, windowId, title, color) {
  const want = title.trim();
  const groups = await chrome.tabGroups.query({ windowId });
  const g =
    groups.find((x) => x.title === want) ||
    groups.find((x) => (x.title || "").toLowerCase() === want.toLowerCase());
  const tab = await chrome.tabs.get(tabId);
  if (g) {
    if (tab.groupId !== g.id) await chrome.tabs.group({ groupId: g.id, tabIds: [tabId] });
    return describeGroup(g, false);
  }
  const gid = await chrome.tabs.group({ tabIds: [tabId], createProperties: { windowId } });
  const made = await chrome.tabGroups.update(gid, {
    title: want,
    color: COLORS.includes(color) ? color : colorFor(want),
  });
  return describeGroup(made, true);
}

const HANDLERS = {
  async ping() {
    return { version: VERSION, extensionId: chrome.runtime.id };
  },

  // Normal windows with their groups. Chrome's extension API has no field for the name set
  // with "Name window…", so chrome-tab reads names through AppleScript and matches by id.
  // The ids are the same numbers on both sides.
  async windows() {
    const wins = await chrome.windows.getAll({ populate: true, windowTypes: ["normal"] });
    const groups = await chrome.tabGroups.query({});
    return wins.map((w) => ({
      id: w.id,
      focused: w.focused,
      state: w.state,
      incognito: w.incognito,
      tabs: w.tabs.length,
      groups: groups
        .filter((g) => g.windowId === w.id)
        .map((g) => ({
          ...describeGroup(g, false),
          tabs: w.tabs.filter((t) => t.groupId === g.id).length,
        })),
    }));
  },

  // Open `url` in window `windowId`, reusing an open copy unless the user is reading it.
  //
  // Which tab a window shows is the user's, never ours (0.5.0): tabs are created inactive
  // and a reload doesn't select. `select` — chrome-tab's --select, implied by --activate —
  // is the only way a page comes to the front. Before 0.5.0 a page opened while the user
  // was in another window took over that window's tab strip, which is what they came back
  // to; "sometimes it jumps to the new tab" was this.
  //
  // `looking` still matters for reuse: it means the user has this window in front right
  // now, so an open copy of the page is left alone and the fresh render goes in a tab
  // beside it — reloading would scroll them back to the top mid-read.
  //
  // The reply reports which tab the window showed before and after, so the caller can say
  // "nothing switched" as a measurement instead of a promise.
  async open({ url, windowId, group, color, reuse = true, looking = false, forceReload = false, select = false }) {
    if (!url) throw new Error("open: url is required");
    const win = await chrome.windows.get(windowId, { populate: true });
    const tabs = win.tabs || [];
    const before = tabs.find((t) => t.active);
    const copy = reuse ? tabs.find((t) => sameUrl(t.url || t.pendingUrl || "", url)) : null;
    let tab;
    let action;
    if (copy && !(looking && copy.active && !forceReload)) {
      await chrome.tabs.reload(copy.id);
      tab = copy;
      action = "reused";
    } else {
      tab = await chrome.tabs.create({ windowId, url, active: false });
      action = copy ? "added-beside" : "added";
    }
    const g = group ? await putInGroup(tab.id, windowId, group, color) : null;
    if (select) await chrome.tabs.update(tab.id, { active: true });
    const showing = (await chrome.tabs.query({ windowId, active: true }))[0];
    return {
      action,
      tabId: tab.id,
      windowId,
      group: g,
      select,
      showingBefore: before ? before.id : null,
      showing: showing ? showing.id : null,
    };
  },

  // A new unfocused window holding `url`. chrome-tab names it through AppleScript afterwards.
  async createWindow({ url, group, color }) {
    const w = await chrome.windows.create({ url, focused: false, type: "normal" });
    const tab = w.tabs && w.tabs[0];
    const g = group && tab ? await putInGroup(tab.id, w.id, group, color) : null;
    return { windowId: w.id, tabId: tab ? tab.id : null, group: g };
  },

  // One tab's whereabouts, for callers that must check before acting (the Claude-in-Chrome
  // mover moves only a lone, inactive tab in a brand-new group).
  async tab({ tabId }) {
    const t = await chrome.tabs.get(tabId);
    let group = null;
    if (t.groupId !== undefined && t.groupId !== -1) {
      const g = await chrome.tabGroups.get(t.groupId);
      const members = await chrome.tabs.query({ groupId: t.groupId });
      group = { ...describeGroup(g, false), tabs: members.length };
    }
    return {
      id: t.id,
      windowId: t.windowId,
      index: t.index,
      active: t.active,
      status: t.status,
      url: t.url || t.pendingUrl || "",
      group,
    };
  },

  // Move a tab to another window for real. AppleScript's move closes it and opens a blank
  // one. The moved tab is not made active, and no window is focused.
  async move({ tabId, windowId, index = -1 }) {
    const before = await chrome.tabs.get(tabId);
    if (before.windowId === windowId) {
      return { tabId, windowId, index: before.index, moved: false, fromWindowId: windowId };
    }
    const moved = await chrome.tabs.move(tabId, { windowId, index });
    const t = Array.isArray(moved) ? moved[0] : moved;
    return { tabId: t.id, windowId: t.windowId, index: t.index, moved: true, fromWindowId: before.windowId };
  },

  // Move a whole tab group to another window, keeping its title, colour and tabs.
  // Chromium's tabGroups.move detaches and re-inserts the group with the same token, so the
  // group id should survive. The reply records every groupId change its tabs reported while
  // it happened: Claude-in-Chrome's listener regroups a session's main tab if it sees -1,
  // so a caller needs to know whether that happened.
  // `afterGroupId` places it right after that group's last tab ("beside the session's
  // topic group"); otherwise it goes to the end of the tab strip.
  async moveGroup({ groupId, windowId, afterGroupId = null, settleMs = 300 }) {
    const before = await chrome.tabGroups.get(groupId);
    const members = await chrome.tabs.query({ groupId });
    const ids = new Set(members.map((t) => t.id));
    if (before.windowId === windowId) {
      return { groupId, windowId, moved: false, tabIds: [...ids], events: [] };
    }
    let index = -1;
    if (afterGroupId !== null && afterGroupId !== undefined) {
      const anchor = await chrome.tabs.query({ groupId: afterGroupId, windowId });
      if (anchor.length) index = Math.max(...anchor.map((t) => t.index)) + 1;
    }
    const events = [];
    const listener = (tabId, change) => {
      if (ids.has(tabId) && "groupId" in change) events.push({ tabId, groupId: change.groupId });
    };
    chrome.tabs.onUpdated.addListener(listener);
    try {
      await chrome.tabGroups.move(groupId, { windowId, index });
      await new Promise((r) => setTimeout(r, settleMs));
    } finally {
      chrome.tabs.onUpdated.removeListener(listener);
    }
    const after = await Promise.all([...ids].map((id) => chrome.tabs.get(id).catch(() => null)));
    return {
      groupId,
      windowId,
      moved: true,
      fromWindowId: before.windowId,
      index,
      tabs: after.filter(Boolean).map((t) => ({ id: t.id, windowId: t.windowId, groupId: t.groupId, active: t.active })),
      events,
    };
  },

  // Pick up a new copy of this extension's files (chrome-tab helper install calls this).
  async reload() {
    setTimeout(() => chrome.runtime.reload(), 200);
    return { reloading: true, version: VERSION };
  },
};
