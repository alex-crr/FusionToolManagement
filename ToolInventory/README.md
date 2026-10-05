# Tool Inventory — Fusion 360 Add-in (Phase 1)

Joins Fusion tool library definitions (.json) with shop on-hand counts stored
in a shared sidecar file. See `../tool-inventory-requirements.md` for the spec.

## Install

A junction in `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\ToolInventory`
points at this folder, so Fusion lists the add-in in
**Utilities → Add-Ins → Scripts and Add-Ins** and runs it on startup.
(On another machine: add this folder there via the dialog's **+** button.)

The **Tool Inventory** panel appears in **Manufacture workspace → Utilities tab**
with three commands: View Inventory, Export to CSV, Tool Inventory Settings.

## Configure

Open **Tool Inventory Settings** and set:

- **Tool library** — pick one of the local Fusion tool libraries (e.g. "Haas Tooling").
  It is read live through the Fusion API: a tool created in the library
  appears in the inventory (quantity 0) on the next Refresh.
- **Inventory file (.json)** — the shared sidecar, e.g.
  `//server/shop/tool_inventory.json`. Created on first edit if missing.
- **Default min stock** — used for tools that have no per-tool minimum yet.

Settings are stored per-machine in `config.json` in this folder.

## Concurrency

Writes use a `tool_inventory.json.lock` file (hostname + UTC timestamp).
A lock younger than 30 s blocks the write with a "being edited by another
user" message; older locks are treated as dead clients and taken over.
Reads never lock.

## Migration from Excel

One-time, run outside Fusion (plain Python 3, stdlib only):

```
python migrate/excel_to_inventory.py --excel counts.xlsx ^
    --library shop_library.json --output tool_inventory.json
```

The script prompts for which Excel columns hold the tool id and the on-hand
count (a min-stock column is optional). Excel ids are matched against both
the library `guid` and `product-id`; unmatched rows are printed for review.
(The migration needs a library *export* file: in Fusion's Tool Library
dialog, right-click the library → Export.)

## Behavior notes (decisions on the spec's open questions)

- **Unique id (Q1):** `guid` — verified against the real local libraries;
  every tool has one. `product-id` is shown in the table as a friendlier
  "Tool ID" and accepted by the migration matcher.
- **Min stock (Q3):** per-tool, falling back to the configured default.
- **CSV scope (Q4):** exports *all* library tools; tools without a recorded
  count export as `on_hand = 0`.
- **LOW status:** strictly below minimum (`on_hand < min_stock`).

## Try it with the example data

`examples/` holds a small Haas tool library (8 tools) and a matching inventory file:

1. In Fusion, open **Manufacture > Manage > Tool Library**, right-click **Local**, choose **Import Libraries**, and pick `examples/Haas_Example_Library.json`. Name it `Haas Example`.
2. Open **Tool Inventory Settings**, choose **Haas Example** as the tool library, and set the inventory path to `examples/tool_inventory.example.json`.
3. Click **View Inventory**. The example shows OK, Low (at or below minimum stock) and Unstocked (never counted) rows.

Tool data comes from the Haas Tooling library for Fusion. Counts are made up.
