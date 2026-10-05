"""Validates and applies an inventory count edit coming from the palette."""
from ..core import inventory_store


def apply_edit(config, tool_id, on_hand, min_stock):
    """Returns (ok, error_message). Writes under the shared-file lock."""
    inventory_path = config.get('inventory_path')
    if not inventory_path:
        return False, 'Inventory path is not configured - open Settings first.'
    if not tool_id:
        return False, 'Missing tool id.'
    try:
        on_hand = int(on_hand)
        min_stock = int(min_stock)
    except (TypeError, ValueError):
        return False, 'On Hand and Min Stock must be whole numbers.'
    if on_hand < -1:
        return False, 'On Hand must be -1 (unstocked) or greater.'
    if min_stock < 0:
        return False, 'Min Stock must be 0 or greater.'
    try:
        inventory_store.update_tool(inventory_path, tool_id, on_hand, min_stock)
    except inventory_store.LockHeldError as e:
        return False, str(e)
    except OSError as e:
        return False, 'Could not write inventory file: %s' % e
    return True, ''
