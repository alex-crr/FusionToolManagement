"""User-local add-in configuration.

Stored in the user's Autodesk app-data folder, NOT inside the add-in bundle, so
settings survive add-in updates and re-installs (the App Store replaces the
bundle's Contents/ on every update). A legacy config.json next to the code is
still read as a fallback, which keeps dev installs working and migrates an
existing config to the new location on the next save.
"""
import json
import os

_ADDIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LEGACY_PATH = os.path.join(_ADDIN_DIR, 'config.json')

DEFAULTS = {
    'library_name': '',
    'inventory_path': '',
    'default_min_stock': 1,
}


def _config_dir():
    appdata = os.environ.get('APPDATA')  # Windows
    base = appdata or os.path.join(
        os.path.expanduser('~'), 'Library', 'Application Support')  # macOS
    return os.path.join(base, 'Autodesk', 'ToolInventory')


CONFIG_PATH = os.path.join(_config_dir(), 'config.json')


def load():
    cfg = dict(DEFAULTS)
    path = CONFIG_PATH if os.path.exists(CONFIG_PATH) else _LEGACY_PATH
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            cfg.update(json.load(f))
    return cfg


def save(cfg):
    os.makedirs(_config_dir(), exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)
