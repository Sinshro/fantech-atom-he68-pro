# Fantech Atom HE68 PRO SignalRGB plugin (unofficial)

`Fantech_Atom_HE68_PRO.js` is a local SignalRGB HID plugin. It uses the
capture-verified Custom Lighting frame format: 10 reports for each visible
frame, with the vendor HID endpoint selected through usage page `0xFF68`.

## Install for local testing

1. Fully close the official Fantech web/software configurator and the Python
   GIF player. Only one program may control the keyboard's vendor HID endpoint.
2. Install SignalRGB, then create this folder if it does not exist:
   `%USERPROFILE%\Documents\WhirlwindFX\Plugins`
3. Copy `Fantech_Atom_HE68_PRO.js` into that folder.
4. Restart SignalRGB. The device should appear as **Fantech Atom HE68 PRO
   (Unofficial)**. Enable streaming and choose any SignalRGB effect.

## Current status

The wired plugin has been tested on hardware. The complete 68-key address map was
recovered from the official configurator and visually checked, including Esc,
Backspace, Insert/Delete, Page Up/Page Down, and the arrow cluster. The plugin
preserves the last frame when SignalRGB exits because a safe command to restore
the user's previous hardware effect has not been captured.

## 2.4 GHz dongle

Use `Fantech_Atom_HE68_PRO_Dongle.js` when connected through the receiver. It
is a separate plugin because the receiver has PID `0xFEFE` and sends Custom
lighting as 22 reports of 32 bytes, while wired mode uses 10 reports of 64
bytes. The receiver's Custom table and `0x80` Custom-mode selector are
capture-backed. Its reports require the observed 26 ms spacing, which limits a
full update to roughly 1.7 frames per second. Direct dongle streaming remains
experimental: the packet contents are verified, but HID transport through
SignalRGB/HIDAPI has not yet been reliable on every test run.
