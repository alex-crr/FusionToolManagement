# Publishing Tool Inventory to the Autodesk App Store

## Build the bundle

```
python build_bundle.py
```

Produces `dist/ADSK.FusionToolManagement.ToolInventory.bundle/`
(`PackageContents.xml` + `Contents/`).

## Test the bundle locally (fresh-install path)

Copy the `.bundle` folder into the App Store install location and restart Fusion:

- Windows: `%APPDATA%\Autodesk\ApplicationPlugins\`
- Mac: `~/Library/Application Support/Autodesk/ApplicationPlugins/`

Confirm: it loads on startup, **View Inventory** appears in Milling → Manage next
to Tool Library, the palette opens, Settings/Export work, and `stop` (disable in
Scripts and Add-Ins) leaves no orphaned buttons. Settings now persist under
`%APPDATA%\Autodesk\ToolInventory\config.json`, so they survive an update.

> Do this on a machine/profile that does **not** have the dev junction install,
> or disable the dev install first — otherwise two copies register.

## Versioning (every submission)

- Bump `version` in `ToolInventory/ToolInventory.manifest` → flows into `AppVersion`.
- `build_bundle.py` mints a fresh `ProductCode` automatically.
- `UpgradeCode` in `build_bundle.py` is **stable** — never change it (it's how the
  store recognizes updates of the same app).

## Before you submit — edit these placeholders

`build_bundle.py`: `VENDOR_URL` points to the GitHub repo (must be public for the store reviewer to reach it). Confirm `VENDOR` / `VENDOR_EMAIL`.

## Code requirements — status

| Requirement | Status |
|---|---|
| No custom toolbar tab/panel (use native) | ✅ uses native `CAMManagePanel` |
| `run()` only wires events, no heavy work | ✅ |
| No dev `importlib.reload` in `run()` | ✅ (none present) |
| Clean `stop()` / uninstall | ✅ idempotent `_cleanup` |
| Settings survive update | ✅ stored outside the bundle |
| **Load time < 0.005 s** | ⚠️ verify: set env `APPLOG_FOR_PERFORMANCE=yes`, read "ran script" time in the AppLogFile |
| Works on latest Fusion, no undocumented API | ⚠️ re-test on current release before submit |

## Submission materials (Publisher Center — not code)

These are uploaded in the form, not shipped in the bundle:

- App icon + store/screenshot images.
- A clear, actionable **help page** (the form's documentation becomes the shipped help).
- Description, price/licensing model, supported OS: Windows only (Mac untested; re-add `mac` / `MacOS` once tested).

Submit at: https://aps.autodesk.com/app-store/publisher-center/fusion-360
Guidelines: https://apps.autodesk.com/Publisher/ProductGuidelines

## Notes

- `migrate/excel_to_inventory.py` ships in the bundle but is a standalone CLI (not
  loaded by Fusion); harmless. Add it to `EXCLUDE_FILES`-style handling in
  `build_bundle.py` if you'd rather keep it out.
- The end user's sidecar inventory `.json` lives on their own share (set in
  Settings) — it is never part of the bundle.
