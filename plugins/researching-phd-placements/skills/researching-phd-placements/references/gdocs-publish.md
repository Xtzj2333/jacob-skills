# Publishing the Google Doc

## New doc

1. `python3 scripts/validate_people.py people.json` — fix every ERROR, read every warning.
2. `python3 scripts/build_gdoc.py people.json --intro intro.txt --out gdoc.html`
3. `bash scripts/upload_gdoc.sh gdoc.html "berkeley:Berkeley/Placement" "<Program> PhD placements"` — prints the link.
   Drive's HTML import keeps Heading 2, nested bullets, bold, italic and the yellow highlight. rclone prints a notice
   that its shared Google client_id is being retired in 2026; if uploads start failing on auth/quota, that is why
   (fallback: Chrome paste into a blank Doc, memory `gdocs-edit-via-chrome-paste`).
4. **Give the headings IDs (required).** Imported headings have no heading IDs, so a table of contents inserted on top
   of them links nowhere (Drive readback shows `#heading=)`; clicking an entry jumps to "Tab 1"). Re-applying
   Heading 2 alone does nothing; switching each heading to Normal text and back does. In a Claude-in-Chrome tab on the
   doc:
   ```js
   // javascript_tool, once: list the outline and define a clicker
   window.__hd=[...document.querySelectorAll('.navigation-item')].map(e=>e.innerText.trim());
   window.__go=i=>{const el=[...document.querySelectorAll('.navigation-item')].find(e=>e.innerText.trim()===window.__hd[i]);
     if(!el) return 'MISSING '+i; for(const t of ['mousedown','mouseup','click'])
     el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window})); return 'clicked '+i;}; window.__hd.length
   ```
   Then, per heading i, in one `browser_batch` of ~10 headings: `javascript_tool window.__go(i)` → wait 0.5 s →
   key `cmd+alt+0` → key `cmd+alt+2` → wait 0.7 s. Clicking an outline item puts the cursor at the start of that
   heading. Afterwards check the outline still lists the same headings (`window.__hd`).
5. **Un-bold the counts (required).** Re-applying Heading 2 re-bolds the whole heading, undoing the builder's
   normal-weight count (seen 2026-10-25: all 37 Princeton headings). Get each heading's name and count lengths:
   ```js
   window.__len=window.__hd.map(t=>{const k=t.indexOf('（');return [k,[...t].length-[...t.slice(0,k)].length];}); JSON.stringify(window.__len)
   ```
   Then per heading i, batched: `window.__go(i)` → wait 0.6 s → key `Right` with `repeat` = name length → key
   `shift+Right` with `repeat` = count length → key `cmd+b`. Zoom on the first one to see that exactly the count was
   selected before doing the rest.
6. **Insert the TOC:** cursor at the top (`cmd+Up`), Insert → Page elements → Table of contents → the first style (page
   numbers). If the TOC already exists, click inside it and press its refresh button (left of the box).
7. **Read back** with the Drive connector (`read_file_content`; save large results and slice with jq), write the
   markdown to a file, and run `python3 scripts/check_readback.py readback.md --people N`: every TOC link has a
   heading ID, heading count matches, counts are normal weight, person count matches. Then look at it in Docs once.

## Changing a doc that already exists

Never trash and re-upload a Doc Jacob has seen: that changes its link. Decide by whether anyone else has touched it:

- **Untouched since your last change** — Drive `modifiedTime` matches your last edit, the readback diffs clean against
  your previous build, and `read_file_content` with `includeComments` shows no comments. Rebuild `gdoc.html` and run
  `bash scripts/upload_gdoc.sh --replace gdoc.html "<folder>" "<title>"`. rclone (v1.74) replaces a native Doc's
  content under the same ID when the import and export formats are both html; the script refuses if a duplicate
  appears. Version history keeps the old text. The TOC goes with the old content, so redo steps 4–7.
- **Edited or commented by someone** — keep their changes: edit in place (Chrome paste or targeted UI edits).
- Either way, diff the new readback against the old one: only the lines you meant to change should differ.
- Never edit Jacob's own docs (e.g. the Berkeley one) unless asked; build the new doc next to them.
- Scratch docs for format tests go to Drive root with a "claude scratch" title and are trashed when done.
