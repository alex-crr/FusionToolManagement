"""Assemble the App Store .bundle for the Tool Inventory add-in.

Run:  python build_bundle.py
Output:  dist/ADSK.FusionToolManagement.ToolInventory.bundle/

The bundle is what the Autodesk App Store distributes (a folder ending in
.bundle, with PackageContents.xml at its root and the add-in under Contents/).
For a dev install you do NOT need this - just point the API/AddIns junction at
ToolInventory/ (see README).

UpgradeCode stays constant across releases; ProductCode is fresh per build and
AppVersion comes from ToolInventory.manifest - bump "version" there per release.
"""
import json
import os
import shutil
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'ToolInventory')
DIST = os.path.join(HERE, 'dist')
BUNDLE = os.path.join(DIST, 'ADSK.FusionToolManagement.ToolInventory.bundle')

VENDOR = 'Alexandre Courrieu'
VENDOR_URL = 'https://github.com/alex-crr/FusionToolManagement'
VENDOR_EMAIL = 'alexandre@courri.eu'
UPGRADE_CODE = '{8F3A1C92-6E0D-4B7A-9C24-1D5E7F2A8B36}'  # STABLE - never change

# User data / dev artefacts that must not ship in the distributed bundle.
EXCLUDE_DIRS = {'__pycache__', '.git'}
EXCLUDE_FILES = {'config.json'}
EXCLUDE_SUFFIX = ('.pyc', '.lock', '.tmp')


def _version():
    with open(os.path.join(SRC, 'ToolInventory.manifest'), encoding='utf-8') as f:
        return json.load(f)['version']


def _package_contents(version):
    return '''<?xml version="1.0" encoding="utf-8"?>
<ApplicationPackage SchemaVersion="1.0"
    AutodeskProduct="Fusion360"
    ProductType="Application"
    Name="Tool Inventory"
    Description="Joins Fusion tool library definitions with shop on-hand counts in one table."
    Author="{vendor}"
    AppVersion="{version}"
    ProductCode="{{{product_code}}}"
    UpgradeCode="{upgrade_code}"
    Icon="./Contents/resources/view/32x32.png">
  <CompanyDetails Name="{vendor}" Url="{url}" Email="{email}"/>
  <Components Description="Fusion 360 Add-in">
    <RuntimeRequirements OS="Win64" Platform="Fusion360" SeriesMin="" SeriesMax=""/>
    <ComponentEntry AppName="ToolInventory" Version="{version}" AppType="addin"
        ModuleName="./Contents/ToolInventory.py" LoadOnFusionStartup="True"/>
  </Components>
</ApplicationPackage>
'''.format(vendor=VENDOR, version=version, product_code=uuid.uuid4(),
           upgrade_code=UPGRADE_CODE, url=VENDOR_URL, email=VENDOR_EMAIL)


def _ignore(_dir, names):
    skip = set()
    for n in names:
        if n in EXCLUDE_DIRS or n in EXCLUDE_FILES or n.endswith(EXCLUDE_SUFFIX):
            skip.add(n)
    return skip


def main():
    version = _version()
    if os.path.exists(BUNDLE):
        shutil.rmtree(BUNDLE)
    contents = os.path.join(BUNDLE, 'Contents')
    shutil.copytree(SRC, contents, ignore=_ignore)
    with open(os.path.join(BUNDLE, 'PackageContents.xml'), 'w', encoding='utf-8') as f:
        f.write(_package_contents(version))
    print('Built %s (v%s)' % (BUNDLE, version))
    print('Install to test: copy the .bundle folder into')
    print(r'  %APPDATA%\Autodesk\ApplicationPlugins\   (Win)')
    print('  ~/Library/Application Support/Autodesk/ApplicationPlugins/   (Mac)')


if __name__ == '__main__':
    main()
