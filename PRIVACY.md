# Privacy policy: Tool Inventory

Last updated: 14 October 2026. Publisher: Alexandre Courrieu, alexandre@courri.eu.

This add-in runs entirely inside Autodesk Fusion on your computer. It does not connect to the internet, has no analytics or telemetry, and does not send, sell or share any data with the publisher or anyone else.

## What it stores on your computer
- Your settings (chosen tool library, inventory file path, default minimum stock): `%APPDATA%\Autodesk\ToolInventory\config.json`.
- The inventory file at the location you choose, holding on-hand and minimum stock per tool, plus the computer name and time of the last change. While a save is in progress, a short-lived `.lock` file next to it holds the computer name.
- CSV files, only when you export one, at the location you choose.

If you put the inventory file on a shared network drive, people with access to that drive can read it, including the computer names above.

Uninstalling the add-in removes its program files. Any files listed above that you created stay where they are, and you can delete them yourself.

## Contact
Questions about this policy: alexandre@courri.eu.
