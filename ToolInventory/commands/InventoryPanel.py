"""Main inventory palette: dockable HTML table joining library + sidecar."""
import json
import os
import traceback

import adsk.core

from ..core import config as config_store
from ..core import csv_exporter, inventory_store, live_library
from . import EditCount

PALETTE_ID = 'toolInventoryPalette'

_handlers = []


def _report_error():
    adsk.core.Application.get().userInterface.messageBox(
        'Tool Inventory error:\n' + traceback.format_exc())


def _palette_url():
    addin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(addin_dir, 'palette', 'inventory.html').replace('\\', '/')


def build_payload():
    """Joined view of library tools and inventory counts, as sent to the UI.

    The library is re-read live from Fusion on every call, so tools created
    in the Fusion tool library dialog appear on the next Refresh.
    """
    cfg = config_store.load()
    if not cfg['library_name']:
        return {'error': 'No tool library selected - open Tool Inventory '
                         'Settings and choose a local library.'}
    try:
        tools, skipped = live_library.read_local_library(cfg['library_name'])
    except Exception as e:
        return {'error': 'Could not read tool library "%s": %s'
                         % (cfg['library_name'], e)}
    try:
        inv = inventory_store.read_inventory(cfg['inventory_path'])
    except (OSError, ValueError) as e:
        return {'error': 'Could not read inventory file: %s' % e}
    return {
        'rows': csv_exporter.build_rows(tools, inv, cfg['default_min_stock']),
        'skipped': skipped,
        'library_name': cfg['library_name'],
        'last_updated': inv.get('last_updated'),
        'last_updated_by': inv.get('last_updated_by'),
    }


class _HTMLEventHandler(adsk.core.HTMLEventHandler):
    """Push-based protocol: the page fires events, Python answers with
    sendInfoToHTML pushes. (HTMLEventArgs.returnData no longer reaches the
    page in current Fusion builds - JS handler returns arrive back here as
    'response' events, which we ignore.)"""

    def notify(self, args):
        try:
            html_args = adsk.core.HTMLEventArgs.cast(args)
            action = html_args.action
            palette = adsk.core.Application.get().userInterface.palettes.itemById(PALETTE_ID)
            if not palette:
                return
            if action in ('ready', 'refresh'):
                palette.sendInfoToHTML('render', json.dumps(build_payload()))
            elif action == 'save':
                data = json.loads(html_args.data)
                ok, message = EditCount.apply_edit(
                    config_store.load(), data.get('tool_id'),
                    data.get('on_hand'), data.get('min_stock'))
                palette.sendInfoToHTML(
                    'saveResult', json.dumps({'ok': ok, 'error': message}))
                if ok:
                    palette.sendInfoToHTML('render', json.dumps(build_payload()))
        except Exception:
            _report_error()


class CreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            handler = _ShowExecuteHandler()
            args.command.execute.add(handler)
            _handlers.append(handler)
        except Exception:
            _report_error()


class _ShowExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            show(adsk.core.Application.get().userInterface)
        except Exception:
            _report_error()


def show(ui):
    # Recreate on every open so the page is always freshly loaded (the
    # webview caches the previous page across isVisible toggles).
    palette = ui.palettes.itemById(PALETTE_ID)
    if palette:
        palette.deleteMe()
    palette = ui.palettes.add(
        PALETTE_ID, 'Tool Inventory', _palette_url(),
        True, True, True, 900, 480)
    palette.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateRight
    handler = _HTMLEventHandler()
    palette.incomingFromHTML.add(handler)
    _handlers.append(handler)
    palette.isVisible = True


def refresh_if_open(ui):
    """Push fresh data to the palette (used after Settings changes)."""
    palette = ui.palettes.itemById(PALETTE_ID)
    if palette:
        palette.sendInfoToHTML('render', json.dumps(build_payload()))


def stop(ui):
    palette = ui.palettes.itemById(PALETTE_ID)
    if palette:
        palette.deleteMe()
    del _handlers[:]
