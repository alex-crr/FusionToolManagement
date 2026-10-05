"""Tool Inventory add-in entry point - registers the toolbar buttons and commands.

Buttons live in the Manufacture workspace (CAMEnvironment) Milling tab, in the
shared Manage panel (CAMManagePanel), right after the native Tool Library button.
Only "View Inventory" is promoted; Export and Settings sit in the panel's
expand/overflow flyout. (CAMManagePanel is shared, so they also show in the
Utilities tab's Manage panel - same as the native Tool Library button.)
"""
import os
import traceback

import adsk.core

from .commands import ExportCSV, InventoryPanel, Settings

WORKSPACE_ID = 'CAMEnvironment'
TAB_ID = 'MillingTab'
PANEL_ID = 'CAMManagePanel'
ANCHOR_CONTROL_ID = 'IronToolLibrary'  # native Tool Library button
LEGACY_PANEL_ID = 'toolInventoryPanel'  # old custom Utilities panel, removed on load
RESOURCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')

# (cmd_id, name, tooltip, module, promoted, icon_folder)
# A command MUST have an icon to be promotable to the ribbon - Fusion only shows
# promoted commands that carry an icon resource (Ekins, Autodesk forums).
_COMMANDS = [
    ('toolInventoryView', 'View Inventory',
     'Open the tool inventory table.', InventoryPanel, True, 'view'),
    ('toolInventoryExport', 'Export to CSV',
     'Export the joined tool inventory to a CSV file.', ExportCSV, False, 'export'),
    ('toolInventorySettings', 'Tool Inventory Settings',
     'Configure tool library path, inventory path and defaults.', Settings, False, 'settings'),
]

_handlers = []


def run(_context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        _cleanup(ui)  # idempotent: a re-run must not stack duplicate handlers/inputs
        panel = _manage_panel(ui)
        anchor = ANCHOR_CONTROL_ID
        for cmd_id, name, tooltip, module, promoted, icon in _COMMANDS:
            cmd_def = ui.commandDefinitions.addButtonDefinition(
                cmd_id, name, tooltip, os.path.join(RESOURCE_DIR, icon))
            handler = module.CreatedHandler()
            cmd_def.commandCreated.add(handler)
            _handlers.append(handler)
            if panel.controls.itemById(anchor):
                control = panel.controls.addCommand(cmd_def, anchor, False)
            else:
                control = panel.controls.addCommand(cmd_def)
            control.isPromotedByDefault = promoted
            control.isPromoted = promoted
            anchor = cmd_id  # chain so order stays View, Export, Settings
    except Exception:
        if ui:
            ui.messageBox('Tool Inventory failed to start:\n'
                          + traceback.format_exc())


def stop(_context):
    ui = None
    try:
        ui = adsk.core.Application.get().userInterface
        _cleanup(ui)
    except Exception:
        if ui:
            ui.messageBox('Tool Inventory failed to stop:\n'
                          + traceback.format_exc())


def _cleanup(ui):
    """Remove our controls, command defs and palette - safe to call repeatedly."""
    InventoryPanel.stop(ui)
    ws = ui.workspaces.itemById(WORKSPACE_ID)
    if ws:
        panel = _existing_panel(ws, TAB_ID, PANEL_ID)
        if panel:
            for cmd_id, _n, _t, _m, _p, _i in _COMMANDS:
                control = panel.controls.itemById(cmd_id)
                if control:
                    control.deleteMe()
        legacy = _find_panel(ws, LEGACY_PANEL_ID)
        if legacy:
            legacy.deleteMe()
    for cmd_id, _n, _t, _m, _p, _i in _COMMANDS:
        cmd_def = ui.commandDefinitions.itemById(cmd_id)
        if cmd_def:
            cmd_def.deleteMe()
    del _handlers[:]


def _manage_panel(ui):
    ws = ui.workspaces.itemById(WORKSPACE_ID)
    tab = ws.toolbarTabs.itemById(TAB_ID) or ws.toolbarTabs.item(0)
    return tab.toolbarPanels.itemById(PANEL_ID)


def _existing_panel(ws, tab_id, panel_id):
    tab = ws.toolbarTabs.itemById(tab_id)
    return tab.toolbarPanels.itemById(panel_id) if tab else None


def _find_panel(ws, panel_id):
    for t in range(ws.toolbarTabs.count):
        panel = ws.toolbarTabs.item(t).toolbarPanels.itemById(panel_id)
        if panel:
            return panel
    return None
