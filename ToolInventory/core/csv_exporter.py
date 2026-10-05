"""Joins tool definitions with inventory counts; builds table rows and CSV.

The join produces the records shown in the palette and exported to CSV.
A tool present in the library but absent from the sidecar gets on_hand=-1
(UNSTOCKED), so a newly created library tool appears in the inventory
immediately, flagged as not-yet-counted rather than empty.

On-hand semantics: -1 = unstocked (never counted), 0 = none in the boxes
(used up or in the machine), >0 = quantity currently in the boxes.
"""
import csv
from datetime import datetime

UNSTOCKED = -1

COLUMNS = ['tool_id', 'name', 'type', 'diameter_mm', 'on_hand', 'min_stock',
           'status', 'last_updated']

STATUS_OK = 'OK'
STATUS_LOW = 'LOW'
STATUS_UNSTOCKED = 'UNSTOCKED'


def status_of(on_hand, min_stock):
    """UNSTOCKED for the -1 sentinel; LOW means a real count below minimum."""
    if on_hand < 0:
        return STATUS_UNSTOCKED
    return STATUS_LOW if on_hand < min_stock else STATUS_OK


def build_rows(tools, inventory_doc, default_min_stock=1):
    counts = inventory_doc.get('tools', {})
    rows = []
    for tool in tools:
        entry = counts.get(tool['id']) or {}
        on_hand = entry.get('on_hand')
        if on_hand is None:
            on_hand = UNSTOCKED
        min_stock = entry.get('min_stock', default_min_stock)
        rows.append({
            'tool_id': tool['id'],
            'product_id': tool.get('product_id', ''),
            'name': tool['name'],
            'type': tool['type'],
            'diameter_mm': tool['diameter_mm'],
            'on_hand': on_hand,
            'min_stock': min_stock,
            'status': status_of(on_hand, min_stock),
        })
    return rows


def default_filename():
    return datetime.now().strftime('tool_inventory_%Y%m%d_%H%M%S.csv')


def export_csv(path, rows, last_updated):
    """Exports all library tools, including uncounted ones (on_hand 0)."""
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            out = dict(row)
            out['last_updated'] = last_updated or ''
            if out['diameter_mm'] is None:
                out['diameter_mm'] = ''
            writer.writerow(out)
