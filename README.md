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
uv run channel_weaver.py <input_path> [options]
```

### Options
- `--output PATH`: Override the default output directory (sibling folder named `<input_folder>_processed`).
- `--bit-depth BitDepth`: Target bit depth (e.g., `32float`, `24`, `16`; default: same as source).
- `--temp-dir PATH`: Custom temporary directory for segment files.
- `--keep-temp`: Keep temporary files after processing (for debugging).
- `--version`: Show version.
- `--help`: Show help.

### Configuration
Edit the user configuration section at the top of `channel_weaver.py`:

```python
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
```

- Missing channels are auto-created with default names (e.g., `Ch 04`).
- Validation ensures configs are correct before processing.

### Example
Input folder: `/path/to/recording` with files like `00000001.WAV` (32 channels).

Output: `/path/to/recording_processed` with files like:
- `01_Kick In.wav` (mono)
- `07_Overheads.wav` (stereo)

## Requirements
- Python 3.14
 
## Contributing
Contributions welcome! Please open an issue or PR for bugs, features, or improvements.

