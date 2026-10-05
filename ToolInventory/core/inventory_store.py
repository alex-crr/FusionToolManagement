"""Reads/writes the shared inventory sidecar JSON with optimistic file locking.

Locking protocol (spec section 6): a `<file>.lock` sidecar holds hostname +
timestamp. A lock younger than LOCK_STALE_SECONDS blocks the write; an older
one is assumed to belong to a dead client and is overwritten. Reads never lock.
"""
import json
import os
import socket
import time
from datetime import datetime, timezone

LOCK_STALE_SECONDS = 30
SCHEMA_VERSION = 1


class LockHeldError(Exception):
    """The inventory file is locked by another workstation."""

    def __init__(self, holder):
        self.holder = holder
        super().__init__(
            'Inventory is being edited by another user (%s) - try again.' % holder)


def empty_doc():
    return {
        'schema_version': SCHEMA_VERSION,
        'last_updated': None,
        'last_updated_by': None,
        'tools': {},
    }


def read_inventory(path):
    """Lockless read. Missing or unconfigured path -> empty document."""
    if not path or not os.path.exists(path):
        return empty_doc()
    with open(path, 'r', encoding='utf-8') as f:
        doc = json.load(f)
    doc.setdefault('tools', {})
    return doc


def update_tool(path, tool_id, on_hand, min_stock):
    """Read-modify-write a single tool's counts under the lock.

    Returns the updated document. Raises LockHeldError if another
    workstation holds a fresh lock.
    """
    _acquire_lock(path)
    try:
        doc = read_inventory(path)
        doc['tools'][str(tool_id)] = {'on_hand': on_hand, 'min_stock': min_stock}
        doc['schema_version'] = SCHEMA_VERSION
        doc['last_updated'] = _utc_now_iso()
        doc['last_updated_by'] = socket.gethostname()
        _write_atomic(path, doc)
        return doc
    finally:
        _release_lock(path)


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def _lock_path(path):
    return path + '.lock'


def _acquire_lock(path):
    lock = _lock_path(path)
    for _ in range(2):
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write('%s %s' % (socket.gethostname(), _utc_now_iso()))
            return
        except FileExistsError:
            try:
                age = time.time() - os.path.getmtime(lock)
                with open(lock, 'r', encoding='utf-8') as f:
                    holder = f.read().strip() or 'unknown'
            except OSError:
                continue  # lock vanished between checks - retry creation
            if age < LOCK_STALE_SECONDS:
                raise LockHeldError(holder)
            # Stale lock: dead-client recovery, take it over.
            try:
                os.remove(lock)
            except OSError:
                pass
    raise LockHeldError('unknown')


def _release_lock(path):
    try:
        os.remove(_lock_path(path))
    except OSError:
        pass


def _write_atomic(path, doc):
    tmp = '%s.%s.tmp' % (path, os.getpid())
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(doc, f, indent=2)
    os.replace(tmp, path)
