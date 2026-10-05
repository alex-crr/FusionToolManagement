"""Reads tool definitions live from Fusion's local tool libraries.

Unlike a static .json export, every call re-fetches the library through the
Fusion API, so tools created or edited in the Fusion tool library dialog
appear in the inventory on the next Refresh. (Only module in core/ that
imports adsk - the migration script must not import it.)
"""
import json

import adsk.cam

from . import library_reader


def _tool_libraries():
    return adsk.cam.CAMManager.get().libraryManager.toolLibraries


def _local_library_urls():
    tool_libs = _tool_libraries()
    root = tool_libs.urlByLocation(adsk.cam.LibraryLocations.LocalLibraryLocation)
    return tool_libs.childAssetURLs(root)


def list_local_libraries():
    """Names of all libraries under Local, for the Settings dropdown."""
    return [url.toString().rsplit('/', 1)[-1] for url in _local_library_urls()]


def read_local_library(name):
    """Return (tools, skipped_count) for the named local library."""
    for url in _local_library_urls():
        if url.toString().rsplit('/', 1)[-1] == name:
            lib = _tool_libraries().toolLibraryAtURL(url)
            raw = [json.loads(lib.item(i).toJson()) for i in range(lib.count)]
            return library_reader.parse_tools(raw)
    raise ValueError('Local tool library not found: %s' % name)
