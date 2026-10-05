#!/usr/bin/env python3
"""One-time migration: Excel inventory counts -> tool_inventory.json sidecar.

Runs OUTSIDE Fusion (plain Python 3, stdlib only - the .xlsx is read directly
as zip + XML, no openpyxl needed).

Usage:
    python excel_to_inventory.py --excel counts.xlsx --library shop_library.json
                                 --output tool_inventory.json [--default-min-stock 1]
                                 [--force]

The script prompts to map Excel columns to the tool id and on-hand count.
Excel ids are matched against both the library `guid` and `product-id`.
Unmatched rows are printed for manual review. The Excel file is not modified.
"""
import argparse
import json
import os
import re
import socket
import sys
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.library_reader import read_library  # noqa: E402

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}


def read_xlsx(path):
    """Return the first worksheet as a list of rows (lists of strings)."""
    with zipfile.ZipFile(path) as zf:
        shared = _shared_strings(zf)
        sheet_name = _first_sheet_path(zf)
        root = ET.fromstring(zf.read(sheet_name))
    rows = []
    for row_el in root.iterfind('.//m:sheetData/m:row', NS):
        cells = {}
        for c in row_el.iterfind('m:c', NS):
            ref = c.get('r', '')
            col = _col_index(ref)
            cells[col] = _cell_value(c, shared)
        if cells:
            width = max(cells) + 1
            rows.append([cells.get(i, '') for i in range(width)])
    width = max((len(r) for r in rows), default=0)
    return [r + [''] * (width - len(r)) for r in rows]


def _shared_strings(zf):
    if 'xl/sharedStrings.xml' not in zf.namelist():
        return []
    root = ET.fromstring(zf.read('xl/sharedStrings.xml'))
    strings = []
    for si in root.iterfind('m:si', NS):
        strings.append(''.join(t.text or '' for t in si.iter(
            '{%s}t' % NS['m'])))
    return strings


def _first_sheet_path(zf):
    wb = ET.fromstring(zf.read('xl/workbook.xml'))
    sheet = wb.find('.//m:sheets/m:sheet', NS)
    rid = sheet.get('{%s}id' % NS['r'])
    rels = ET.fromstring(zf.read('xl/_rels/workbook.xml.rels'))
    for rel in rels:
        if rel.get('Id') == rid:
            target = rel.get('Target').lstrip('/')
            return target if target.startswith('xl/') else 'xl/' + target
    return 'xl/worksheets/sheet1.xml'


def _col_index(cell_ref):
    index = 0
    for ch in cell_ref:
        if not ch.isalpha():
            break
        index = index * 26 + (ord(ch.upper()) - ord('A') + 1)
    return index - 1


def _cell_value(c, shared):
    ctype = c.get('t', 'n')
    if ctype == 'inlineStr':
        return ''.join(t.text or '' for t in c.iter('{%s}t' % NS['m']))
    v = c.find('m:v', NS)
    if v is None or v.text is None:
        return ''
    if ctype == 's':
        return shared[int(v.text)]
    return v.text


def prompt_column(header, label, optional=False):
    print('\nColumns in the Excel file:')
    for i, name in enumerate(header):
        print('  [%d] %s' % (i, name or '(empty)'))
    suffix = ' (Enter to skip)' if optional else ''
    while True:
        raw = input('Which column holds %s?%s ' % (label, suffix)).strip()
        if optional and raw == '':
            return None
        if raw.isdigit() and int(raw) < len(header):
            return int(raw)
        print('Please enter a number between 0 and %d.' % (len(header) - 1))


def parse_count(raw):
    raw = str(raw).strip()
    if not raw:
        return None
    try:
        value = int(float(raw))
    except ValueError:
        return None
    return value if value >= 0 else None


def main():
    parser = argparse.ArgumentParser(
        description='Migrate Excel inventory counts to tool_inventory.json')
    parser.add_argument('--excel', required=True, help='Existing Excel file (.xlsx)')
    parser.add_argument('--library', required=True,
                        help='Fusion tool library export (.json)')
    parser.add_argument('--output', required=True,
                        help='Destination tool_inventory.json')
    parser.add_argument('--default-min-stock', type=int, default=1)
    parser.add_argument('--force', action='store_true',
                        help='Overwrite the output file if it exists')
    args = parser.parse_args()

    if os.path.exists(args.output) and not args.force:
        sys.exit('Refusing to overwrite %s (use --force).' % args.output)

    rows = read_xlsx(args.excel)
    if len(rows) < 2:
        sys.exit('Excel file has no data rows.')
    header, data = rows[0], rows[1:]

    id_col = prompt_column(header, 'the tool id (guid or product id)')
    count_col = prompt_column(header, 'the on-hand count')
    min_col = prompt_column(header, 'the min stock', optional=True)

    tools, _ = read_library(args.library)
    by_key = {}
    for tool in tools:
        by_key[tool['id'].lower()] = tool['id']
        if tool['product_id']:
            by_key[tool['product_id'].lower()] = tool['id']

    matched = {}
    unmatched = []
    for row in data:
        excel_id = str(row[id_col]).strip()
        if not excel_id:
            continue
        guid = by_key.get(excel_id.lower())
        if guid is None:
            unmatched.append(excel_id)
            continue
        on_hand = parse_count(row[count_col])
        if on_hand is None:
            unmatched.append('%s (bad count: %r)' % (excel_id, row[count_col]))
            continue
        min_stock = (parse_count(row[min_col]) if min_col is not None else None)
        matched[guid] = {
            'on_hand': on_hand,
            'min_stock': args.default_min_stock if min_stock is None else min_stock,
        }

    doc = {
        'schema_version': 1,
        'last_updated': datetime.now(timezone.utc).isoformat(
            timespec='seconds').replace('+00:00', 'Z'),
        'last_updated_by': socket.gethostname(),
        'tools': matched,
    }
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(doc, f, indent=2)

    print('\nWrote %d tools to %s' % (len(matched), args.output))
    if unmatched:
        print('\n%d Excel rows did NOT match any library tool - review manually:'
              % len(unmatched))
        for entry in unmatched:
            print('  -', entry)


if __name__ == '__main__':
    main()
