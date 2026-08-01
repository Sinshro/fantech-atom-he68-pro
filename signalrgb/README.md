# Fantech Atom HE68 PRO SignalRGB plugin (unofficial)

`Fantech_Atom_HE68_PRO.js` is a local SignalRGB HID plugin. It uses the
capture-verified Custom Lighting frame format: 10 reports for each visible
frame, with the vendor HID endpoint selected through usage page `0xFF68`.

## Step-by-step installation

### 1. Download the plugin files

Open the repository on GitHub, select **Code**, then **Download ZIP**. Extract the
ZIP and open its `signalrgb` folder.

### 2. Choose the correct connection

- Wired USB: `Fantech_Atom_HE68_PRO.js`
- 2.4 GHz receiver: `Fantech_Atom_HE68_PRO_Dongle.js`

You can install both files. Their USB product IDs are different, so SignalRGB
will select the one matching the keyboard's current connection.

### 3. Close competing software

Fully close the official Fantech web configurator, any Fantech desktop software,
and Python lighting/GIF scripts. Only one application should control the
keyboard's vendor HID endpoint at a time.

### 4. Open SignalRGB's plugin folder

Press **Win + R**, paste the following path, and press **Enter**:

```text
%USERPROFILE%\Documents\WhirlwindFX\Plugins
```

Create the `Plugins` folder if it does not exist.

### 5. Copy and load the plugins

Copy the selected `.js` file—or both files—into the `Plugins` folder. Fully exit
SignalRGB from its system-tray icon, wait a few seconds, and open SignalRGB again.

### 6. Verify the keyboard

Open **Devices** in SignalRGB. Under **Other Devices**, look for **Fantech Atom
HE68 PRO**. Its card should use the official keyboard product image:

![Fantech Atom HE68 PRO detected by SignalRGB](../docs/images/signalrgb-device-card.png)

Select an effect in SignalRGB and use the device's light/pulse button to confirm
that the LED map follows the physical keyboard.

## Troubleshooting

- Device missing: unplug and reconnect the keyboard or receiver, then restart
  SignalRGB.
- Device visible but not changing: close the official configurator and every
  Python lighting process, then restart SignalRGB.
- Using the dongle: wireless streaming is experimental and limited to roughly
  1.7 complete frames per second by the captured 22-report update sequence.
- Using USB: make sure the keyboard is actually in wired mode, not merely charging
  while its wireless mode is still selected.

## Current status

The wired plugin has been tested on hardware. The complete 68-key address map was
recovered from the official configurator and visually checked, including Esc,
Backspace, Insert/Delete, Page Up/Page Down, and the arrow cluster. The plugin
preserves the last frame when SignalRGB exits because a safe command to restore
the user's previous hardware effect has not been captured.

## 2.4 GHz dongle details

Use `Fantech_Atom_HE68_PRO_Dongle.js` when connected through the receiver. It
is a separate plugin because the receiver has PID `0xFEFE` and sends Custom
lighting as 22 reports of 32 bytes, while wired mode uses 10 reports of 64
bytes. The receiver's Custom table and `0x80` Custom-mode selector are
capture-backed. Its reports require the observed 26 ms spacing, which limits a
full update to roughly 1.7 frames per second. Direct dongle streaming remains
experimental: the packet contents are verified, but HID transport through
SignalRGB/HIDAPI has not yet been reliable on every test run.
