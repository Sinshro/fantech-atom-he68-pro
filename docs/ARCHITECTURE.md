# Architecture

```mermaid
flowchart LR
  CLI["demo.py / future Qt GUI"] --> Device["HE68Device\nHID transport"]
  Device --> Protocol["Verified protocol serializer"]
  Device --> Capture["JSON + binary captures"]
  Protocol --> Keyboard["Wired HID collection\n0x0C45:0x80CB / 0xFF68"]
  Framework["Lighting / Performance / Macro / Profile / Firmware"] -. "raises until captured" .-> Protocol
  Adapters["Future OpenRGB / SignalRGB adapters"] -. "no protocol assumptions" .-> Framework
```

Only `HE68Device.set_color()` has a verified serialized command. The remaining
protocol classes are explicit capability boundaries and raise `NotImplementedError`.

## Future modules

- `features/`: capture-backed lighting, performance, macro, profile, and firmware work.
- `backends/`: adapter interfaces for OpenRGB and SignalRGB.
- `ambient/`: modular desktop-capture backends; no keyboard transmission is allowed
  until a PC-sync command is captured.
- `gui.py`: optional Qt UI once each user-visible control has a verified capability.
