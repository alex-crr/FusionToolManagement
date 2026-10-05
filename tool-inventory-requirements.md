# Fusion 360 Tool Inventory Add-in — Requirements Specification

**Version:** 0.1 (draft)  
**Date:** 2026-06-10  
**Status:** Pre-implementation review

---

## 1. Problem Statement

Tool definitions and cutting data live in Fusion 360 tool libraries (.json). Physical inventory counts live in a separate Excel file. These two sources drift out of sync and create ambiguity about what's actually available for a job. The goal is a single add-in that joins both, lives inside Fusion, and becomes the one place operators interact with tool inventory.

---

## 2. Scope

### In scope (Phase 1 — Local)
- Read tool definitions live from a local Fusion 360 tool library (via the Fusion API, so newly created tools appear on refresh)
- Store and edit per-tool inventory counts (on-hand quantity only)
- Display a joined view: tool definition + count in a single table
- Low-stock warning (configurable minimum per tool)
- Export full inventory to CSV
- Multi-user access via shared network path (file-based concurrency)
- One-time migration script from existing Excel

### In scope (Phase 2 — Cloud, future)
- Store inventory in Autodesk Platform Services (APS) Data Management API or a hosted key-value store
- Sync tool library from Fusion cloud libraries
- Real-time multi-user updates (replace file-locking with API)

### Out of scope
- Tool ordering / procurement workflow
- Integration with ERP or MES systems
- Tool condition tracking beyond a free-text notes field
- Cost or supplier data

---

## 3. Users

| Role | Description |
|------|-------------|
| Operator | Updates on-hand counts after tool use or restocking |
| Programmer | Reads inventory before selecting tools for a job |
| Admin | Configures min-stock thresholds, sets library path, exports CSV |

All roles use the same add-in. No authentication in Phase 1 (trust is implicit on the shared drive).

---

## 4. Architecture

### 4.1 Components

```
fusion360-tool-inventory/
├── manifest.json              # Fusion add-in manifest
├── ToolInventory.py           # Entry point, registers commands
├── commands/
│   ├── InventoryPanel.py      # Main palette / table view
│   ├── EditCount.py           # Inline edit dialog
│   └── ExportCSV.py           # Export command
├── core/
│   ├── library_reader.py      # Parses Fusion .json tool library
│   ├── inventory_store.py     # Reads/writes inventory JSON, handles locking
│   └── csv_exporter.py        # Joins tool data + counts, writes CSV
├── migrate/
│   └── excel_to_inventory.py  # One-time migration script (standalone)
└── config.json                # User-local config (paths, min-stock defaults)
```

### 4.2 Data flow

```
Fusion Tool Library (.json)  ──read──►  library_reader.py
                                              │
                                              ▼
                                     joined record
                                              │
Inventory Sidecar (.json)    ──read──►  inventory_store.py
  (shared network path)                       │
                                              ▼
                                     InventoryPanel (UI)
                                              │
                              ┌───────────────┼───────────────┐
                              ▼               ▼               ▼
                         EditCount       ExportCSV      (future: APS)
```

---

## 5. Data Model

### 5.1 Tool library (existing, read-only)

Standard Fusion 360 HSMWorks JSON format. Key fields consumed:

| Field | Description |
|-------|-------------|
| `guid` or `product_id` | Unique tool identifier (primary key) |
| `description` | Human-readable tool name |
| `type` | e.g. flat end mill, drill, tap |
| `diameter` | Cutting diameter |
| `number_of_flutes` | |
| `cutting_data` | Speeds/feeds — displayed but not modified |

The exact key name for the unique identifier must be confirmed against the user's actual library file before implementation.

### 5.2 Inventory sidecar (new, read-write)

Filename: `tool_inventory.json`  
Location: shared network path configured by admin (e.g. `\\server\shop\tool_inventory.json`)

```json
{
  "schema_version": 1,
  "last_updated": "2026-06-10T14:23:00Z",
  "last_updated_by": "WORKSTATION_A",
  "tools": {
    "<tool_guid>": {
      "on_hand": 4,
      "min_stock": 2
    },
    "<tool_guid>": {
      "on_hand": 1,
      "min_stock": 1
    }
  }
}
```

Tools present in the library but absent from the sidecar are shown with `on_hand = -1` (**unstocked**) — a tool newly created in the Fusion library appears in the inventory immediately, flagged as not-yet-counted rather than as a real zero. On-hand values mean: `-1` = unstocked (never counted), `0` = none in the boxes (used up or loaded in the machine), `>0` = quantity currently in the boxes. The join is live, so no separate "sync new tools" step is needed — every Refresh re-reads the Fusion library and shows any newly added tools as unstocked.

### 5.3 Config file (user-local, not shared)

Filename: `config.json`, stored in the add-in directory.

```json
{
  "library_name": "Shop Library",
  "inventory_path": "//server/shop/tool_inventory.json",
  "default_min_stock": 1
}
```

---

## 6. Multi-user Concurrency (Phase 1)

Phase 1 uses optimistic file-locking on the shared network path:

1. Before writing, create a lock file: `tool_inventory.json.lock` containing hostname + timestamp.
2. If a lock file already exists and is less than 30 seconds old, show "Inventory is being edited by another user — try again."
3. If the lock file is older than 30 seconds, assume stale and overwrite it (dead-client recovery).
4. After writing, delete the lock file.
5. All reads are lockless — reads never block.

This is sufficient for low-concurrency shop environments (typically 1–3 simultaneous users). Phase 2 replaces this entirely with APS.

---

## 7. UI

### 7.1 Panel location

Manufacture workspace → **Milling tab → Manage panel** (`CAMManagePanel`), right
after the native **Tool Library** button. Only **View Inventory** is promoted
(directly visible); **Export to CSV** and **Settings** sit in the Manage panel's
expand/overflow flyout. (The Manage panel is shared, so the buttons also appear
in the Utilities tab's Manage panel — matching the native Tool Library button.)

| Command | Visibility | Description |
|---------|------------|-------------|
| View Inventory | promoted | Opens main palette |
| Export to CSV | overflow flyout | Saves CSV immediately, shows save-file dialog |
| Settings | overflow flyout | Configure library path, inventory path, defaults |

### 7.2 Main inventory palette

A dockable palette (HTML/JS inside Fusion's webview) with:

- **Table columns:** Tool ID, Name, Type, Diameter, On Hand, Min Stock, Status
- **Status column:** ✓ OK / ⚠ Low / – Unstocked (on_hand = -1)
- **Filter bar:** free text search across ID and name
- **Click a row:** opens inline edit dialog for On Hand and Min Stock values
- **Refresh button:** re-reads library and sidecar from disk

### 7.3 Edit dialog

Simple modal with two numeric fields: On Hand (integer ≥ -1, where -1 = unstocked) and Min Stock (integer ≥ 0). Confirm saves and releases lock. Cancel discards.

---

## 8. CSV Export

Output columns:

```
tool_id, name, type, diameter_mm, on_hand, min_stock, status, last_updated
```

Filename pattern: `tool_inventory_YYYYMMDD_HHMMSS.csv`  
Encoding: UTF-8  
Delimiter: comma  
User chooses save location via standard file dialog.

---

## 9. Migration Script

Standalone Python script (run once, outside Fusion):

**Input:** existing Excel file  
**Output:** `tool_inventory.json` in sidecar format

Requirements:
- User maps Excel column names to `tool_guid` and `on_hand` fields via CLI prompts
- Script prints unmatched rows (tool IDs in Excel not found in the library) for manual review
- Does not modify the Excel file

---

## 10. Technical Constraints

| Constraint | Detail |
|-----------|--------|
| Language | Python 3 (Fusion 360 add-in runtime) |
| UI layer | HTML + vanilla JS in Fusion palette webview |
| External libraries | None — stdlib only for Phase 1 (no pip in Fusion runtime) |
| Fusion API version | Tested against Fusion 360 API 2.0 (adsk.fusion, adsk.core) |
| OS | Windows primary target; Mac secondary |
| Network | UNC paths (Windows) or SMB mounts (Mac) for shared inventory file |

---

## 11. Phased Roadmap

### Phase 1 — Local + shared drive (this build)
- Add-in scaffold and manifest
- Tool library reader
- Inventory sidecar store with file locking
- Inventory palette UI
- Edit count dialog
- CSV export
- Settings dialog
- Migration script

### Phase 2 — Cloud
- Replace sidecar JSON with APS Data Management or a lightweight REST backend (e.g. Supabase with a simple schema)
- Replace file-locking with server-side conflict resolution
- Sync from Fusion cloud tool libraries via APS Library API
- Optional: webhook/notification when stock drops below minimum

---

## 12. Open Questions

| # | Question | Impact |
|---|----------|--------|
| 1 | What is the exact field name used as the unique tool identifier in the existing library JSON? | Core data model |
| 2 | Is the shared drive a Windows UNC path, or will Mac clients also need access? | File path handling |
| 3 | Should the minimum stock threshold be global (one default) or per-tool? (Spec assumes per-tool, with a global default) | Data model, UI |
| 4 | Should the export include all tools in the library, or only tools with a known count? | CSV exporter logic |
| 5 | Any preference on the APS service for Phase 2 vs. a self-hosted option? | Phase 2 architecture |
