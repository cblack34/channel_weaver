# Channel Weaver

A high-quality, memory-efficient Python CLI tool for processing multitrack audio recordings. It handles split multichannel WAV files (e.g., from digital mixing consoles), extracts individual channels, concatenates segments across files, supports stereo bus creation, and outputs numbered DAW-ready tracks.

## Features
- **Automatic Input Detection**: Scans a folder for sequentially-named WAV files (e.g., `00000001.WAV`, `00000002.WAV`).
- **Flexible Validation**: Detects and ensures consistent sample rate, bit depth, and channel count across files.
- **Channel Extraction & Concatenation**: Splits multichannel files into mono segments, then stitches them into continuous tracks.
- **Stereo Buses**: Define custom stereo pairs (e.g., overheads or room mics) with user-specified file names for ordered output.
- **Custom Naming & Numbering**: Outputs files like `01_Kick In.wav` or `07_Overheads.wav` for seamless DAW import (e.g., Studio One).
- **Memory-Safe Processing**: Uses on-disk temporary files to handle large projects (200+ GB) without high RAM usage.
- **Configurable**: Easy-to-edit Python config for channels and buses; future support for JSON/YAML.
- **CLI Interface**: Built with Typer for clean, intuitive commands.
- **Extensible**: Modular code structure following SOLID principles for easy maintenance and additions.
- **Intelligent Section Splitting**: Automatically detects song sections using click track analysis and splits recordings accordingly.
- **BPM Metadata Embedding**: Embeds detected BPM values into WAV files using ID3 tags for DAW compatibility.
- **Session JSON Output**: Optional detailed session metadata export for post-processing analysis.

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/cblack34/channel_weaver.git
   cd channel-weaver
   ```

2. Install dependencies:
   ```
   uv sync
   ```

## Usage

Run the script with:
```
uv run python -m src.main <input_path> [options]
```

### Options
- `--output PATH`: Override the default output directory (sibling folder named `<input_folder>_processed`).
- `--bit-depth BitDepth`: Target bit depth (e.g., `32float`, `24`, `16`; default: same as source).
- `--temp-dir PATH`: Custom temporary directory for segment files.
- `--keep-temp`: Keep temporary files after processing (for debugging).
- `--section-by-click`: Enable automatic section splitting based on click track analysis.
- `--gap-threshold FLOAT`: Minimum gap between sections in seconds when using click-based splitting (default: 3.0).
- `--session-json PATH`: Output detailed session metadata as a JSON file.
- `--version`: Show version.
- `--help`: Show help.

### Configuration
Edit the user configuration section in your project directory. Create a `config.py` file with:

```python
from src.config import ChannelAction, BusSlot, BusType

CHANNELS = [
    {"ch": 1, "name": "Kick In"},
    {"ch": 2, "name": "Kick Out"},
    # ... add more
]

BUSES = [
    {
        "file_name": "07_Overheads",
        "type": BusType.STEREO,
        "slots": {BusSlot.LEFT: 7, BusSlot.RIGHT: 8},
    },
    # ... add more
]

# Optional: Section splitting configuration
SECTION_SPLITTING = {
    "enabled": False,  # Set to True to enable click-based section splitting
    "gap_threshold_seconds": 3.0,  # Minimum gap between sections
    "min_section_length_seconds": 15.0,  # Minimum section length
    "bpm_change_threshold": 1,  # BPM change threshold for section boundaries
}
```

- Missing channels are auto-created with default names (e.g., `Ch 04`).
- Validation ensures configs are correct before processing.
- For click-based section splitting, ensure one channel is named "Click" with `action: CLICK`.
- BPM metadata is embedded using ID3 TBPM tags, compatible with most DAWs (Pro Tools, Logic Pro, Ableton Live).

### Example
Input folder: `/path/to/recording` with files like `00000001.WAV` (32 channels).

Output: `/path/to/recording_processed` with files like:
- `01_Kick In.wav` (mono)
- `07_Overheads.wav` (stereo)

#### Section Splitting Example
When `--section-by-click` is enabled and a "Click" channel exists:

Output structure:
```
/path/to/recording_processed/
├── section_01/
│   ├── 01_Kick In.wav
│   ├── 07_Overheads.wav
│   └── session.json (if --session-json specified)
├── section_02/
│   ├── 01_Kick In.wav
│   ├── 07_Overheads.wav
│   └── session.json
└── session_summary.json (if --session-json specified)
```

Each section directory contains the audio files for that detected section, with BPM metadata embedded in the WAV files.

## BPM Metadata & DAW Compatibility

When section splitting is enabled, Channel Weaver automatically detects the tempo (BPM) of each section and embeds this information into the output WAV files using ID3 TBPM tags. This metadata is compatible with most professional DAWs:

- **Pro Tools**: Reads BPM metadata for tempo mapping
- **Logic Pro**: Displays BPM in file information
- **Ableton Live**: Can use BPM for tempo-matching
- **Studio One**: Shows BPM in file browser and inspector

**Note**: Some DAWs may require manual refresh of the file browser to display newly embedded metadata. The BPM detection is optimized for click tracks in the 45-300 BPM range with high accuracy (±2 BPM typical).

## Requirements
- Python 3.14
 
## Contributing
Contributions welcome! Please open an issue or PR for bugs, features, or improvements.

