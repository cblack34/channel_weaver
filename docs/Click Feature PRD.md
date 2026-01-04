## Overview
This feature adds intelligent section splitting to the existing multi-channel WAV processing app. After splitting a 32-channel WAV (or multi-file session) into individual mono/stereo tracks based on the channel config, the app will optionally use a designated "click" track to detect sections automatically.

Sections are defined by changes in the click track: 
- Start or stop of click (distinguishing song vs. speaking parts)
- Any BPM change (even 1 BPM difference)

Each detected section will be placed in its own numbered directory (`section_01`, `section_02`, etc.) **directly inside the output directory**. This replaces the long continuous tracks in the output directory when the feature is enabled, making it easier to edit song sections vs. speaking parts in a DAW.

The feature runs post-splitting on the already-generated long tracks (leveraging the app's existing concatenation of multi-file sessions into continuous tracks).

Example structure:
- Input: `D:\Exchange Recordings\20260104\raw\*.wav`
- Output directory: `D:\Exchange Recordings\20260104\processed\`

When feature disabled (current behavior):
```
processed/
├── kick.wav
├── vocals.wav
├── click.wav
└── ... (other long tracks)
```

When feature enabled:
```
processed/
├── section_01/
│   ├── kick.wav
│   ├── vocals.wav
│   ├── click.wav
│   └── ... (section-specific segments)
├── section_02/
│   ├── kick.wav
│   ├── vocals.wav
│   ├── click.wav
│   └── ...
└── ... (more sections)
```

## Goals
- Automate separation of song rehearsals/performances from speaking/talking parts.
- Split at natural song boundaries where BPM changes (common in live band recordings with varying song tempos).
- Produce DAW-friendly output: short, focused track segments in numbered folders inside the standard output directory.
- Provide visibility into detected sections via console summary and optional JSON file.
- Maintain performance for large files (on-disk processing, no full load into memory).
- No changes to existing output directory logic (default sibling `processed` or CLI-specified path).

## Key Requirements

### Channel Configuration Changes
- Add a new channel type: `"click"` in the config YAML.
- Only **one** channel can be marked as `type: click`.
- Validation: Enforce single click channel; raise error if zero or multiple.
- Output: The click channel is exported as a mono WAV file in each section (same as other monos).
- Existing types (e.g., mono, stereo, group) remain unchanged.

### CLI Integration
- Add an optional flag to the existing `process` command: `--section-by-click` (or similar, e.g., `--split-sections`).
- When enabled: The output directory contains the `section_XX` directories instead of long tracks.
- When disabled: Behave exactly as current (long tracks directly in output directory).
- No dry-run needed.

### Configurable Parameters
Add a new top-level section in the config YAML (e.g., `section_splitting:`) with defaults:
```yaml
section_splitting:
  enabled: false  # Or tie to CLI flag
  gap_threshold_seconds: 3.0  # Time without clicks to detect speaking break (no-click period)
  min_section_length_seconds: 15.0  # Short sections below this are merged into previous
  bpm_change_threshold: 1  # Minimum BPM difference to trigger split (integer; default 1 as even small changes matter)
  # Click channel is determined by channel type, no separate config needed
```
- These are optional with defaults; overridable in config file.
- Gap threshold also overridable via CLI (e.g., `--gap-threshold 5.0`) for convenience.
- No CLI for min_section_length (config only).

### Detection Logic
- Process the full-length `click.wav` track (generated in memory or temp during processing).
- Use onset/peak detection tailored for clean metronome clicks:
  - Detect click positions (peaks/onsets above a noise threshold).
  - Compute inter-onset intervals (IOI) with decimal precision.
  - In sliding windows, estimate BPM (60 / median IOI * beats_per_bar if accent detected, but assume quarter-note clicks).
  - Detect "no-click" when gaps exceed `gap_threshold_seconds`.
  - Detect BPM changes: When stabilized new BPM differs by >= `bpm_change_threshold`.
- Section boundaries:
  - New section starts at click onset after a no-click gap.
  - New section starts at/just before the first beat of a new detected BPM.
  - Split on click stop (end of song into speaking).
- Section type:
  - "song": Click present with valid BPM.
  - "speaking": No click (BPM = none).
- Short sections (< min_section_length):
  - Merge into previous section (including if at recording end).
  - Never drop sections entirely.
- All tracks (including non-click) are split at identical sample-accurate boundaries.

### Output Structure
- Output directory logic unchanged (default sibling `processed` or CLI-specified).
- When feature enabled:
  - The output directory contains **only** the `section_01/`, `section_02/`, ... directories.
  - No long track files at the top level of the output directory.
- Directory naming: Zero-padded, chronological (`section_01`, `section_02`, ...).
- Inside each section dir: Same filenames as current split output (e.g., `kick.wav`, `vocals.wav`, `click.wav`).
- File format: Preserve input (usually 32-channel WAV specs), with existing override options.

### Metadata in Output WAVs
- Embed detected integer BPM in each section's WAV files using ID3v2-style tags (via library like mutagen or similar, which supports ID3 in RIFF WAV).
  - Use standard `TBPM` frame (text string of integer BPM, e.g., "120").
  - For speaking sections: Omit TBPM or set to "0".
- This provides DAW compatibility where possible (e.g., some tools read TBPM from WAV ID3 chunks).

### Summary Output
- Always print a console table when feature enabled:
  ```
  Section     | Start Time | Duration   | Type      | BPM
  ------------|------------|------------|-----------|----
  section_01  | 00:00:00   | 00:02:45   | song      | 120
  section_02  | 00:02:45   | 00:00:32   | speaking  | none
  section_03  | 00:03:17   | 00:03:10   | song      | 95
  ...
  ```
  - Times in HH:MM:SS.
  - Durations rounded appropriately.
- Optional session JSON:
  - Add CLI flag: `--session-json [path]` (default: `session.json` in parent directory of source WAV(s), e.g., `D:\Exchange Recordings\20260104\session.json`).
  - If path provided, write there; else default.
  - Format: Array of objects with keys: section, start_seconds, start_hms, duration_seconds, duration_hms, type, bpm.
  - If app evolves to have other JSON outputs, merge into it; for now, standalone.

### Edge Cases & Reliability
- No click channel defined: Warning + fallback to normal long tracks directly in output directory.
- Detection failure (e.g., very quiet/noisy click, no clear onsets): Warning + fallback to single section (`section_01` only in output directory).
- Single section detected: Still use directory structure (`section_01` only).
- Very short recordings: Apply min length merging.
- Multi-file sessions: Already handled by existing concatenation; sections can span original file boundaries seamlessly.
- Performance: Inline with current app (stream/on-disk splitting).

## Non-Requirements
- Gradual tempo ramps (out of scope).
- Configurable BPM detection sensitivity beyond thresholds.
- Excluding click from output.
- Folder names with BPM/type.
- Dry-run preview.
