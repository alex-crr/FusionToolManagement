"""Settings dialog: tool library selection, inventory path, default min stock."""
import traceback

import adsk.core

from ..core import config as config_store
from ..core import live_library
from . import InventoryPanel

_handlers = []


def _report_error():
    adsk.core.Application.get().userInterface.messageBox(
        'Tool Inventory error:\n' + traceback.format_exc())


class CreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            cmd = args.command
            cfg = config_store.load()
            inputs = cmd.commandInputs
            dropdown = inputs.addDropDownCommandInput(
                'libraryName', 'Tool library',
                adsk.core.DropDownStyles.TextListDropDownStyle)
            for name in live_library.list_local_libraries():
                dropdown.listItems.add(name, name == cfg['library_name'])
            inputs.addStringValueInput(
                'inventoryPath', 'Inventory file (.json)', cfg['inventory_path'])
            inputs.addIntegerSpinnerCommandInput(
                'defaultMinStock', 'Default min stock', 0, 9999, 1,
                int(cfg['default_min_stock']))
            handler = _ExecuteHandler()
            cmd.execute.add(handler)
            _handlers.append(handler)
        except Exception:
            _report_error()


class _ExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            inputs = args.command.commandInputs
            cfg = config_store.load()
            selected = inputs.itemById('libraryName').selectedItem
            cfg['library_name'] = selected.name if selected else ''
            cfg['inventory_path'] = inputs.itemById('inventoryPath').value.strip()
            cfg['default_min_stock'] = inputs.itemById('defaultMinStock').value
            config_store.save(cfg)
            InventoryPanel.refresh_if_open(
                adsk.core.Application.get().userInterface)
        except Exception:
            _report_error()
