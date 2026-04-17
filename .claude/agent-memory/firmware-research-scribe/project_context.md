---
name: Project Context — Roccat Elo Headset RE
description: Active reverse engineering of Roccat Elo wireless headset; goal is HeadsetControl / eruption open-source driver support
type: project
---

Investigation targets a Roccat Elo wireless gaming headset (exact model TBD — not the original 7.1 Air).

**Why:** User wants open-source driver support (HeadsetControl project). Original Elo 7.1 Air support exists in eruption/HeadsetControl with VID 0x1E7D, but this hardware uses different VIDs (26CE, 0E8D), suggesting a newer hardware revision or OEM variant.

**How to apply:** When documenting, note that upstream HeadsetControl PRs must follow CLAUDE.md upstream rules — no firmware addresses, no attack tooling, no AI attribution.

Key directory: `C:\msys64\home\gelum\headphones\` — this is where all RE documentation lives.
Analysis subdirectory: `headset_firmware_analysis/` (created during this session).
