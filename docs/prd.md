# Product Requirements Document (PRD)  
**Midas M32 Multitrack Processor**  
**Version:** 1.3  
**Date:** November 23, 2025  

## 1. Purpose  
Create a high-quality, memory-efficient command-line tool that converts a set of multi-channel WAV files recorded by a Midas M32 (or similar console) into continuous, DAW-ready mono and stereo tracks with user-defined naming, stereo buses, and optional channel skipping.

## 2. Scope  
- Input: one folder containing any number of sequentially-named multi-channel WAV files (`00000001.WAV`, `00000002.WAV`, …)  
- Output: a sibling folder named `<input_folder_name>_processed` containing one continuous WAV file per final track (mono or stereo)  
- Target DAWs: Studio One (primary), Reaper, Pro Tools, Logic, Ableton, etc.  
- Platform: Windows, macOS, Linux  

## 3. Functional Requirements  

### 3.1 Input Handling  
- Automatically discover and numerically sort all `.wav`/`.WAV` files in the provided directory  
- Detect sample rate, bit depth, and channel count from the first file  
- Validate that every subsequent file matches the first in sample rate, bit depth, and channel count  
- Fail fast with clear error messages on mismatch  

### 3.2 Output Directory  
- Default location: a new folder named `processed` created as a **sibling** to the input folder  
  - Example:  
    Input → `C:/Recordings/My Gig 2025-11-22/raw`  
    Output → `C:/Recordings/My Gig 2025-11-22/processed`  
- Handle conflicts: if the default folder exists, append a suffix (e.g., `_v2`, `_v3`) or timestamp to avoid overwriting  
- User may override via CLI argument  
- Use `pathlib` for all path operations to ensure cross-platform compatibility  

### 3.3 Audio Processing  
- Sample-accurate, bit-perfect concatenation across file boundaries  
- No pops, clicks, or level changes at junctions  
- Preserve original bit depth by default  
- Optional conversion to 24-bit or 16-bit integer  

### 3.4 Memory Strategy  
- Process one input file at a time  
- Extract each channel to temporary mono segment files on disk  
- After all input files are processed, concatenate segments per channel/bus  
- Delete temporary files immediately after use (unless `--keep-temp`)  

### 3.5 Channel Routing & Naming  

```python
from enum import Enum, auto
from pydantic import BaseModel, validator, Field

class ChannelAction(Enum):
    PROCESS = auto()   # output as individual mono track
    BUS     = auto()   # route to a stereo/multi-channel bus
    SKIP    = auto()   # discard entirely

class BusSlot(Enum):
    LEFT  = auto()
    RIGHT = auto()

class BusType(Enum):
    STEREO = auto()    # only supported type in v1.3

class ChannelConfig(BaseModel):
    ch: int = Field(..., ge=1, description="Channel number (1-based)")
    name: str
    action: ChannelAction = ChannelAction.PROCESS

    @validator('action')
    def validate_action(cls, v):
        return v

class BusConfig(BaseModel):
    file_name: str = Field(..., description="Custom file name for output, e.g., '07_overheads'")
    type: BusType = BusType.STEREO
    slots: dict[BusSlot, int] = Field(..., description="Slot to channel mapping")

    @validator('slots')
    def validate_slots(cls, v, values):
        if values.get('type') == BusType.STEREO:
            if set(v.keys()) != {BusSlot.LEFT, BusSlot.RIGHT}:
                raise ValueError("STEREO buses require exactly LEFT and RIGHT slots")
        return v
```

#### User Configuration (Top of Script – Easy to Edit)

```python
# Channel definitions – list of dicts for easy editing and future config file support
# Any missing channels 1–N (where N is detected channel count) are auto-created as "Ch XX" with action=PROCESS
# Log warnings for auto-created channels to alert users
CHANNELS = [
    {"ch": 1, "name": "Kick In"},
    {"ch": 2, "name": "Kick Out"},
    {"ch": 3, "name": "Snare Top"},
    {"ch": 31, "name": "Click", "action": ChannelAction.SKIP},
    {"ch": 32, "name": "Talkback", "action": ChannelAction.SKIP},
]

# Bus definitions – list of dicts, each owns its slot-to-channel mappings and custom file name
BUSES = [
    {
        "file_name": "07_Overheads",
        "type": BusType.STEREO,
        "slots": {BusSlot.LEFT: 7, BusSlot.RIGHT: 8},
    },
    {
        "file_name": "15_Room Mics",
        "type": BusType.STEREO,
        "slots": {BusSlot.LEFT: 15, BusSlot.RIGHT: 16},
    },
]
```

### 3.6 Output Files  
- Mono tracks: `<zero-padded ch number>_<name>.wav` (e.g., `01_Kick In.wav`)  
- Stereo bus tracks: `<bus file_name>.wav` (e.g., `07_Overheads.wav`)  
- All filenames sanitized for filesystem safety (invalid characters replaced with `_`)  

### 3.7 Configuration Validation  
- Validate during config loading (early in script execution) using Pydantic for type and value checks  
- Additional runtime checks after detecting channel count (N):  
  - Ensure all configured channels and bus slots are <= N  
  - No duplicate channel numbers in CHANNELS or bus slots  
  - Channels assigned to buses must not be marked as PROCESS or SKIP in CHANNELS  
- Make validation extensible: Define required slots per BusType (e.g., via a method on BusType) for future types  
- Raise custom exceptions with helpful, user-friendly messages  

## 4. Non-Functional Requirements  

| Requirement             | Specification                                      |
|-------------------------|----------------------------------------------------|
| CLI Framework           | Typer (type hints, auto-help, clean design)        |
| Audio Library           | PySoundFile + NumPy (primary)                      |
| Progress Feedback       | Rich progress bars (use tqdm)                      |
| Temporary Directory     | Created inside output folder; deleted on success   |
| Dependencies            | typer, pysoundfile, numpy, tqdm, pydantic          |
| Performance             | Must handle 200+ GB projects without high RAM use |
| Error Handling          | User-friendly, never silent failures; custom exceptions where appropriate |
| Code Structure          | Modular design for maintainability:  
  - ConfigLoader class (parses, validates, auto-creates channels)  
  - AudioExtractor class (handles per-file channel splitting)  
  - TrackBuilder class (concatenation and bus interleaving)  
  - Use dependency injection (e.g., pass config to builders) |

## 5. Command-Line Interface

```bash
python m32_processor.py <input_path> [options]

Options:
  --output PATH              Override output directory
  --bit-depth BitDepth       Target bit depth (default: same as source); use custom Enum for choices (32float, 24, 16)
  --temp-dir PATH            Custom temp directory
  --keep-temp                Keep temporary segment files
  --version                  Show version
  --help                     Show help
```

## 6. Deliverable  
A single, fully commented, production-ready script named `m32_processor.py` that implements all requirements above and can be run immediately after installing dependencies:

```bash
pip install typer pysoundfile numpy tqdm pydantic
python m32_processor.py "path/to/M32 recording folder"
```
