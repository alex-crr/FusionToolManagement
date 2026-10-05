"""Parses a Fusion 360 (HSMWorks-format) tool library .json file."""
import json

MM_PER_INCH = 25.4
_INCH_UNITS = ('inches', 'inch')


def read_library(path):
    """Return (tools, skipped_count) from a Fusion tool library export file."""
    with open(path, 'r', encoding='utf-8') as f:
        doc = json.load(f)
    raw = doc.get('data', []) if isinstance(doc, dict) else doc
    return parse_tools(raw)


def parse_tools(raw):
    """Parse a list of HSM-format tool dicts -> (tools, skipped_count).

    Each tool record: {id, product_id, name, type, diameter_mm, flutes}.
    `guid` is the primary key (verified against real libraries); `product-id`
    is kept separately for display. Tools with neither key are skipped.
    Diameters are normalized to millimeters using the tool's `unit` field.
    """
    tools = []
    skipped = 0
    for entry in raw:
        if not isinstance(entry, dict):
            skipped += 1
            continue
        product_id = entry.get('product-id') or entry.get('product_id') or ''
        tool_id = entry.get('guid') or product_id
        if not tool_id:
            skipped += 1
            continue
        geometry = entry.get('geometry') or {}
        diameter = geometry.get('DC')
        if isinstance(diameter, (int, float)) and entry.get('unit') in _INCH_UNITS:
            diameter *= MM_PER_INCH
        tools.append({
            'id': str(tool_id),
            'product_id': str(product_id),
            'name': entry.get('description') or str(product_id),
            'type': entry.get('type') or '',
            'diameter_mm': round(diameter, 3) if isinstance(diameter, (int, float)) else None,
            'flutes': geometry.get('NOF'),
        })
    return tools, skipped
