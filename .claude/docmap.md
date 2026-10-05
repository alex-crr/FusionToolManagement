# Docmap — FusionToolManagement

Spec: `tool-inventory-requirements.md` (Phase 1 implemented; Phase 2 = cloud/APS, future).

## ToolInventory/ — Fusion 360 add-in (Python, stdlib only)

Entry: `ToolInventory.py` — `run()/stop()`; adds 3 buttons to the shared
`CAMManagePanel` (Manage) on `CAMEnvironment` → `MillingTab`, inserted right
after the native `IronToolLibrary` (Tool Library) button. Only `toolInventoryView`
is promoted; Export + Settings have `isPromoted=False` so they sit in the panel's
expand/overflow flyout. CAMManagePanel is shared, so the buttons also show in the
Utilities tab's Manage panel (same as the native Tool Library button itself).
`run()` calls `_cleanup()` first (idempotent) so a re-run cannot stack duplicate
commandCreated handlers → fixes the duplicated Settings-dialog inputs. `_cleanup()`
removes our controls + cmd defs + palette and deletes the legacy
`toolInventoryPanel` if an earlier build left one. Manifest: `ToolInventory.manifest`.

### core/ (adsk-free except live_library; migration imports only library_reader)
- `config.py` — load/save `config.json` (library_name, inventory_path, default_min_stock).
  Stored under `%APPDATA%\Autodesk\ToolInventory\` (mac: `~/Library/Application Support/...`),
  NOT in the add-in dir, so App Store updates (which replace `Contents/`) don't wipe
  settings. Legacy `<addin>/config.json` is read as a fallback + one-time migration.
- `library_reader.py` — `parse_tools(raw) -> (tools, skipped)` for HSM-format tool dicts;
  key = `guid` (fallback `product-id`); inch→mm via `unit`. `read_library(path)` = file wrapper.
- `live_library.py` — imports adsk.cam; `list_local_libraries()`,
  `read_local_library(name)` re-reads the local Fusion library on every call
  (new tools appear on Refresh). Verified: re-read picks up added tools.
- `inventory_store.py` — sidecar JSON read/write. `read_inventory` (lockless),
  `update_tool` (read-modify-write under `.lock` file; `LockHeldError` if lock < 30 s old,
  stale lock taken over; atomic write via tmp+`os.replace`).
- `csv_exporter.py` — `build_rows` (join library+sidecar; absent ⇒ on_hand=-1
  `UNSTOCKED`). On-hand semantics: -1 unstocked / 0 none (used up or in machine) /
  >0 in the boxes. `status_of`: <0 ⇒ UNSTOCKED, else <min ⇒ LOW, else OK.
  `export_csv`, `default_filename`.

### commands/ (adsk-dependent)
- `InventoryPanel.py` — palette `toolInventoryPalette` (HTML webview);
  `build_payload()` = joined rows from live library (used by palette AND ExportCSV);
  `_HTMLEventHandler`: PUSH protocol — JS fires `ready/refresh/save`, Python answers
  with `sendInfoToHTML('render'/'saveResult', json)`. HTMLEventArgs.returnData does
  NOT reach the page in this Fusion build (JS returns arrive as `response` events —
  ignored; they carry e.g. "rendered:60" for diagnostics). `show()` deletes and
  recreates the palette each time (webview caches the old page).
- `EditCount.py` — `apply_edit(config, tool_id, on_hand, min_stock) -> (ok, err)`;
  on_hand ≥ -1 (allows the unstocked sentinel), min_stock ≥ 0; writes via inventory_store.
- `ExportCSV.py` — immediate command (no inputs): InventoryPanel.build_payload →
  FileDialog → export_csv.
- `Settings.py` — command dialog (library dropdown from live_library + inventory
  path string + min-stock spinner) → config.save → palette refresh.

### palette/inventory.html
Single-file UI, **Fusion dark theme** (CSS vars in `:root`, dark only): filter
bar, "Group by type" toggle (default on: rows grouped under type headers with
counts, sorted by diameter then name), refresh, joined table (click row → edit
modal), status badges ✓ OK / ⚠ Low / – Unstocked. Edit modal On Hand accepts
-1 (unstocked); hint line documents the -1/0/1+ semantics. JS↔Python:
`adsk.fusionSendData` fire-and-forget out, pushes (`render`/`saveResult`) in
via `window.fusionJavaScriptHandler.handle`.

### migrate/excel_to_inventory.py
Standalone CLI (outside Fusion). Reads .xlsx via zipfile+ElementTree (no openpyxl),
prompts column mapping, matches ids against guid AND product-id, writes sidecar,
prints unmatched rows. Imports `core.library_reader` via sys.path insert.

## Data flow
Fusion local library ─live read→ live_library ─┐
                                               ├→ csv_exporter.build_rows → palette / CSV
sidecar .json ─read→ inventory_store ──────────┘
edits: palette → EditCount → inventory_store.update_tool (locked write)

## Install / data files
- Junction `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\ToolInventory`
  → project `ToolInventory/` (auto-listed + run on startup).
- `tool_inventory.json` (project root) — local sidecar with real shop counts; gitignored, never shipped.

## Packaging / App Store release
- `build_bundle.py` (repo root) → `dist/ADSK.FusionToolManagement.ToolInventory.bundle/`
  with `PackageContents.xml` + `Contents/` (a copy of `ToolInventory/`, minus
  `config.json`, `__pycache__`, `*.pyc/.lock/.tmp`). The XML is generated in-script
  (single source of truth): `UpgradeCode` constant, `ProductCode` fresh per build,
  `AppVersion` from the manifest's `version`. Verified schema against a shipped
  add-in (hanskellner/Fusion360WrapSketch) — uses `ProductType="Application"`,
  `ComponentEntry AppType="addin" ModuleName="./Contents/ToolInventory.py"`.
- `PUBLISHING.md` — release checklist + the manual Publisher Center steps
  (store icon, screenshots, help page) that aren't code.
- Why the add-in is store-ready: no custom tab/panel (uses native `CAMManagePanel`),
  `run()` only wires events, no dev `reload`, idempotent `stop()`/`_cleanup`.
  Remaining bar to verify before submit: load time <0.005 s (APPLOG).

## Verified facts (live Fusion, 2026-06-10)
- Tool JSON keys: `guid`, `product-id`, `description`, `type`, `unit`,
  `geometry.DC` (diameter), `geometry.NOF` (flutes).
- Workspace `CAMEnvironment`; tabs incl. `MillingTab`, `UtilitiesTab`.
- (2026-06-30) `CAMManagePanel` is the Manage panel and is **shared** across
  MillingTab + UtilitiesTab; native Tool Library = control id `IronToolLibrary`.
