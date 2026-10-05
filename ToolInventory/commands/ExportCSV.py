"""Exports the joined inventory to CSV via a save-file dialog."""
import traceback

import adsk.core

from ..core import csv_exporter
from . import InventoryPanel

_handlers = []


def _report_error():
    adsk.core.Application.get().userInterface.messageBox(
        'Tool Inventory error:\n' + traceback.format_exc())


class CreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            handler = _ExecuteHandler()
            args.command.execute.add(handler)
            _handlers.append(handler)
        except Exception:
            _report_error()


class _ExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            _export()
        except Exception:
            _report_error()


def _export():
    ui = adsk.core.Application.get().userInterface
    payload = InventoryPanel.build_payload()
    if 'error' in payload:
        ui.messageBox(payload['error'])
        return
    rows = payload['rows']

    dialog = ui.createFileDialog()
    dialog.title = 'Export Tool Inventory'
    dialog.filter = 'CSV files (*.csv)'
    dialog.initialFilename = csv_exporter.default_filename()
    if dialog.showSave() != adsk.core.DialogResults.DialogOK:
        return
    csv_exporter.export_csv(dialog.filename, rows, payload.get('last_updated'))
    ui.messageBox('Exported %d tools to:\n%s' % (len(rows), dialog.filename))
