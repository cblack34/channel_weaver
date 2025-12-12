# Channel Weaver - Code Restructuring Plan

**Version:** 1.0  
**Date:** December 12, 2025  
**Purpose:** Comprehensive restructuring plan to improve code organization, maintainability, and adherence to SOLID principles.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State Analysis](#2-current-state-analysis)
3. [Proposed Architecture](#3-proposed-architecture)
4. [Detailed Package Structure](#4-detailed-package-structure)
5. [Module Specifications](#5-module-specifications)
6. [Migration Guide](#6-migration-guide)
7. [Implementation Order](#7-implementation-order)
8. [Testing Strategy](#8-testing-strategy)

---

## 1. Executive Summary

### 1.1 Goals

- **Eliminate code smells**: Remove God classes, reduce coupling, improve cohesion
- **Apply SOLID principles**: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
- **Domain-Driven Design**: Organize code around business domains (audio, configuration, output)
- **Improve testability**: Enable unit testing of individual components in isolation
- **Future extensibility**: Support new bus types, audio formats, and output handlers without modifying existing code

### 1.2 Key Changes

| Current Structure | Problem | New Structure |
|-------------------|---------|---------------|
| `m32_processor.py` (706 lines) | God module with 3+ responsibilities | Split into `audio/`, `config/`, `output/` packages |
| Module named "m32" | Too hardware-specific for generic functionality | Hardware-agnostic naming with clear domains |
| Mixed concerns in modules | Validation, conversion, processing intermingled | Separated by domain and responsibility |
| Protocols in single file | Limited extensibility | Domain-specific protocol definitions |

---

## 2. Current State Analysis

### 2.1 Existing Module Inventory

| Module | Lines | Responsibilities | SOLID Violations |
|--------|-------|------------------|------------------|
| `m32_processor.py` | 706 | ConfigLoader, AudioExtractor, TrackBuilder, helper functions, bit depth utilities | SRP (3+ classes), OCP (hardcoded behaviors) |
| `main.py` | 232 | CLI definition, configuration data, path utilities | SRP (CLI + config data + utilities) |
| `models.py` | 127 | Pydantic models, enums | Generally good, minor ISP concerns |
| `validators.py` | 49 | Channel/Bus validation | Good, follows SRP |
| `exceptions.py` | 109 | Custom exceptions | Good, well-organized |
| `converters.py` | 121 | Bit depth converters + factory | Good, follows OCP with Strategy pattern |
| `protocols.py` | 51 | OutputHandler protocol | Good, but should be domain-specific |
| `types.py` | 25 | Type aliases and TypedDicts | Good |
| `constants.py` | 4 | Constants | Good, but should grow |

### 2.2 Identified Code Smells

#### 2.2.1 God Class/Module - `m32_processor.py`

**Problem**: Contains three major classes (`ConfigLoader`, `AudioExtractor`, `TrackBuilder`) plus 8+ utility functions with distinct responsibilities:

- Configuration loading and completion
- Audio file discovery and validation
- Audio segment extraction (ffmpeg-based)
- Mono track building
- Stereo bus building
- Bit depth resolution
- Filename sanitization
- Audio info extraction (ffmpeg fallback)

**Impact**: 
- 706 lines is difficult to navigate and maintain
- Changes to one area risk breaking another
- Testing requires mocking many unrelated dependencies

#### 2.2.2 Hardcoded Hardware Reference

**Problem**: "m32" in module name suggests Midas M32 hardware specificity, but the code is generic audio processing.

**Impact**:
- Confuses users about applicability to other consoles
- Limits perceived reusability

#### 2.2.3 Mixed Configuration and CLI Logic

**Problem**: `main.py` contains both CLI definition AND hardcoded channel/bus configuration data.

**Impact**:
- Configuration changes require modifying Python code
- No separation between "how to run" and "what to process"
- Difficult to support external configuration files in future

#### 2.2.4 Duplicate Exception Definition

**Problem**: `AudioProcessingError` is defined in BOTH `exceptions.py` AND `m32_processor.py` (line 227).

**Impact**:
- Confusion about which to import
- Potential import conflicts

#### 2.2.5 Unreachable/Dead Code

**Problem**: In `m32_processor.py`, the `_get_audio_info_ffmpeg` function (lines 253-269) has unreachable code after `return MockInfo()`.

**Impact**:
- Confusing to readers
- Potential bugs if the return is removed

#### 2.2.6 Tight Coupling to External Tools

**Problem**: `AudioExtractor._process_file_segments` directly calls `ffmpeg` with hardcoded command construction.

**Impact**:
- Difficult to unit test
- No abstraction for alternative extraction methods

---

## 3. Proposed Architecture

### 3.1 Package Structure Overview

```
src/
├── __init__.py                 # Package metadata and version
├── cli/                        # Command-line interface layer
│   ├── __init__.py
│   ├── app.py                  # Typer application definition
│   ├── commands.py             # CLI command implementations
│   └── utils.py                # Path sanitization, output directory resolution
│
├── config/                     # Configuration domain
│   ├── __init__.py
│   ├── loader.py               # ConfigLoader class
│   ├── defaults.py             # Default channel/bus configurations
│   ├── models.py               # ChannelConfig, BusConfig Pydantic models
│   ├── enums.py                # ChannelAction, BusSlot, BusType, BitDepth
│   └── validators.py           # ChannelValidator, BusValidator
│
├── audio/                      # Audio processing domain
│   ├── __init__.py
│   ├── discovery.py            # File discovery and sorting
│   ├── validation.py           # Audio parameter validation (sample rate, channels, etc.)
│   ├── extractor.py            # AudioExtractor - segment extraction orchestration
│   ├── info.py                 # Audio info retrieval (soundfile + ffmpeg fallback)
│   └── ffmpeg/                 # FFmpeg-specific implementations
│       ├── __init__.py
│       ├── commands.py         # FFmpeg command builders
│       └── executor.py         # FFmpeg execution wrapper
│
├── processing/                 # Track building and conversion domain
│   ├── __init__.py
│   ├── builder.py              # TrackBuilder orchestration
│   ├── mono.py                 # MonoTrackWriter
│   ├── stereo.py               # StereoTrackWriter (bus tracks)
│   └── converters/             # Bit depth conversion strategies
│       ├── __init__.py
│       ├── protocols.py        # BitDepthConverter protocol
│       ├── float32.py          # Float32Converter
│       ├── int24.py            # Int24Converter
│       ├── int16.py            # Int16Converter
│       ├── source.py           # SourceConverter
│       └── factory.py          # get_converter() factory function
│
├── output/                     # Output handling domain
│   ├── __init__.py
│   ├── protocols.py            # OutputHandler protocol
│   ├── console.py              # ConsoleOutputHandler (Rich-based)
│   ├── logging.py              # LoggingOutputHandler (for headless/CI)
│   └── naming.py               # Filename sanitization, output path generation
│
├── exceptions/                 # Centralized exception hierarchy
│   ├── __init__.py             # Re-exports all exceptions
│   ├── base.py                 # ConfigError base class
│   ├── config.py               # Configuration-related exceptions
│   └── audio.py                # Audio processing exceptions
│
├── types.py                    # Type aliases (SegmentMap, AudioInfo, etc.)
└── constants.py                # Application constants (chunk size, version, etc.)
```

### 3.2 Dependency Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                              CLI Layer                               │
│                    (cli/app.py, cli/commands.py)                    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Application Layer                            │
│              (Orchestrates config, audio, processing)                │
└─────────────────────────────────────────────────────────────────────┘
          │                         │                        │
          ▼                         ▼                        ▼
┌─────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
│  Config Domain  │   │    Audio Domain     │   │ Processing Domain   │
│  (config/*)     │   │    (audio/*)        │   │ (processing/*)      │
└─────────────────┘   └─────────────────────┘   └─────────────────────┘
          │                         │                        │
          └─────────────────────────┴────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Shared Layer                                 │
│         (types.py, constants.py, exceptions/, output/)               │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 SOLID Principles Application

| Principle | Application |
|-----------|-------------|
| **Single Responsibility** | Each module has one reason to change. `discovery.py` only discovers files. `validation.py` only validates audio params. |
| **Open/Closed** | Converter strategies, output handlers, and validators are extensible via new implementations without modifying existing code. |
| **Liskov Substitution** | All converter implementations are interchangeable. All output handlers implement the same protocol. |
| **Interface Segregation** | Protocols are focused and minimal. `BitDepthConverter` doesn't include file I/O. `OutputHandler` doesn't include progress tracking. |
| **Dependency Inversion** | High-level modules (`builder.py`, `extractor.py`) depend on abstractions (`BitDepthConverter`, `OutputHandler`), not concrete implementations. |

---

## 4. Detailed Package Structure

### 4.1 `src/cli/` - Command Line Interface Package

**Responsibility**: Handle all user interaction, argument parsing, and CLI presentation.

#### 4.1.1 `src/cli/__init__.py`

```python
"""CLI package for Channel Weaver."""
from src.cli.app import app

__all__ = ["app"]
```

#### 4.1.2 `src/cli/app.py`

**Responsibility**: Define the Typer application instance and global options.

**Contents**:
- `app = typer.Typer()` definition
- Version callback function
- App-level configuration (help text, completion settings)

**Dependencies**: `typer`, `src.constants.VERSION`

**Lines**: ~30

#### 4.1.3 `src/cli/commands.py`

**Responsibility**: Implement CLI command handlers.

**Contents**:
- `main()` command function (the primary processing command)
- Orchestrates `AudioExtractor`, `ConfigLoader`, `TrackBuilder`
- Error handling and user feedback

**Dependencies**: 
- `src.cli.utils`
- `src.config.loader.ConfigLoader`
- `src.config.defaults.CHANNELS, BUSES`
- `src.audio.extractor.AudioExtractor`
- `src.processing.builder.TrackBuilder`
- `src.output.console.ConsoleOutputHandler`
- `src.exceptions`

**Lines**: ~100

#### 4.1.4 `src/cli/utils.py`

**Responsibility**: CLI utility functions for path handling.

**Contents**:
- `sanitize_path(path: Path) -> Path`
- `default_output_dir(input_path: Path) -> Path`
- `ensure_output_path(input_path: Path, override: Path | None) -> Path`
- `determine_temp_dir(output_dir: Path, override: Path | None) -> Path`

**Dependencies**: `pathlib`

**Lines**: ~50

---

### 4.2 `src/config/` - Configuration Domain Package

**Responsibility**: Configuration loading, validation, and default values.

#### 4.2.1 `src/config/__init__.py`

```python
"""Configuration package for Channel Weaver."""
from src.config.loader import ConfigLoader
from src.config.models import ChannelConfig, BusConfig
from src.config.enums import ChannelAction, BusSlot, BusType, BitDepth
from src.config.validators import ChannelValidator, BusValidator

__all__ = [
    "ConfigLoader",
    "ChannelConfig",
    "BusConfig",
    "ChannelAction",
    "BusSlot",
    "BusType",
    "BitDepth",
    "ChannelValidator",
    "BusValidator",
]
```

#### 4.2.2 `src/config/enums.py`

**Responsibility**: Define all configuration-related enumerations.

**Contents**:
- `ChannelAction(Enum)` - PROCESS, BUS, SKIP
- `BusSlot(Enum)` - LEFT, RIGHT
- `BusType(Enum)` - STEREO (with `required_slots()` method)
- `BitDepth(str, Enum)` - SOURCE, FLOAT32, INT24, INT16

**Dependencies**: `enum`

**Lines**: ~50

**Note**: Moved from `models.py` for better separation. Enums are pure domain concepts.

#### 4.2.3 `src/config/models.py`

**Responsibility**: Pydantic models for configuration entries.

**Contents**:
- `ChannelConfig(BaseModel)` - Channel configuration with validators
- `BusConfig(BaseModel)` - Bus configuration with validators

**Dependencies**: 
- `pydantic`
- `src.config.enums`

**Lines**: ~80

#### 4.2.4 `src/config/validators.py`

**Responsibility**: Validate configuration against runtime constraints.

**Contents**:
- `ChannelValidator` - Validates channel uniqueness and range
- `BusValidator` - Validates bus channel references and conflicts

**Dependencies**: 
- `src.config.models`
- `src.config.enums`
- `src.exceptions.config`

**Lines**: ~60

**Note**: Already well-structured, minimal changes needed.

#### 4.2.5 `src/config/loader.py`

**Responsibility**: Load and complete configuration from raw data.

**Contents**:
- `ConfigLoader` class:
  - `__init__(channels_data, buses_data, detected_channel_count, validators)`
  - `load() -> tuple[list[ChannelConfig], list[BusConfig]]`
  - `_load_channels() -> list[ChannelConfig]`
  - `_load_buses() -> list[BusConfig]`
  - `_collect_bus_channels(buses) -> list[int]`
  - `_complete_channel_list(channels, bus_channels) -> list[ChannelConfig]`

**Dependencies**:
- `src.config.models`
- `src.config.validators`
- `src.exceptions.config`
- `src.types`

**Lines**: ~120

#### 4.2.6 `src/config/defaults.py`

**Responsibility**: Store default/example channel and bus configurations.

**Contents**:
- `CHANNELS: list[ChannelDict]` - Default channel definitions
- `BUSES: list[BusDict]` - Default bus definitions

**Dependencies**: `src.types.ChannelDict, BusDict`

**Lines**: ~80

**Note**: This extracts the hardcoded configuration from `main.py`, making it easier to:
1. Find and modify defaults
2. Eventually support external config files (JSON, YAML, TOML)
3. Create preset configurations for different console types

---

### 4.3 `src/audio/` - Audio Processing Domain Package

**Responsibility**: Audio file discovery, validation, and segment extraction.

#### 4.3.1 `src/audio/__init__.py`

```python
"""Audio processing package for Channel Weaver."""
from src.audio.extractor import AudioExtractor
from src.audio.discovery import AudioFileDiscovery
from src.audio.validation import AudioParameterValidator

__all__ = [
    "AudioExtractor",
    "AudioFileDiscovery",
    "AudioParameterValidator",
]
```

#### 4.3.2 `src/audio/discovery.py`

**Responsibility**: Discover and sort audio files in a directory.

**Contents**:
- `AudioFileDiscovery` class:
  - `__init__(input_dir: Path)`
  - `discover() -> list[Path]` - Find all WAV files
  - `_sort_key(path: Path) -> tuple[int | float, str]` - Numeric sorting

**Dependencies**: `pathlib`, `re`

**Lines**: ~40

**SOLID**: Single responsibility - only discovers files, doesn't validate them.

#### 4.3.3 `src/audio/validation.py`

**Responsibility**: Validate audio file parameters for consistency.

**Contents**:
- `AudioParameterValidator` class:
  - `__init__(files: list[Path])`
  - `validate() -> AudioParameters` - Returns validated parameters
  - `_validate_file(path: Path, expected: AudioParameters | None) -> AudioParameters`

- `AudioParameters` dataclass:
  - `sample_rate: int`
  - `channels: int`
  - `bit_depth: BitDepth`
  - `subtype: str`

**Dependencies**: 
- `soundfile`
- `src.audio.info`
- `src.config.enums.BitDepth`
- `src.exceptions.audio`

**Lines**: ~80

**SOLID**: Single responsibility - only validates consistency.

#### 4.3.4 `src/audio/info.py`

**Responsibility**: Retrieve audio file information with fallback strategies.

**Contents**:
- `get_audio_info(path: Path) -> AudioInfo` - Primary interface
- `_get_info_soundfile(path: Path) -> AudioInfo` - SoundFile-based
- `_get_info_ffmpeg(path: Path) -> AudioInfo` - FFmpeg fallback
- `bit_depth_from_subtype(subtype: str) -> BitDepth` - Convert subtype to BitDepth

**Dependencies**:
- `soundfile`
- `subprocess`
- `json`
- `src.config.enums.BitDepth`

**Lines**: ~70

**SOLID**: Encapsulates fallback logic, isolates external dependencies.

#### 4.3.5 `src/audio/extractor.py`

**Responsibility**: Orchestrate audio segment extraction.

**Contents**:
- `AudioExtractor` class:
  - `__init__(input_dir, temp_dir, keep_temp, output_handler)`
  - `discover_and_validate() -> list[Path]`
  - `extract_segments(target_bit_depth) -> SegmentMap`
  - `cleanup() -> None`
  - Properties: `sample_rate`, `channels`, `bit_depth`

**Dependencies**:
- `src.audio.discovery.AudioFileDiscovery`
- `src.audio.validation.AudioParameterValidator`
- `src.audio.ffmpeg.executor.FFmpegExecutor`
- `src.output.protocols.OutputHandler`
- `src.types`

**Lines**: ~100

**SOLID**: 
- Composes discovery, validation, and extraction (orchestration)
- Depends on abstractions (OutputHandler, validators)

#### 4.3.6 `src/audio/ffmpeg/__init__.py`

```python
"""FFmpeg integration for audio extraction."""
from src.audio.ffmpeg.executor import FFmpegExecutor
from src.audio.ffmpeg.commands import FFmpegCommandBuilder

__all__ = ["FFmpegExecutor", "FFmpegCommandBuilder"]
```

#### 4.3.7 `src/audio/ffmpeg/commands.py`

**Responsibility**: Build FFmpeg command strings.

**Contents**:
- `FFmpegCommandBuilder` class:
  - `build_extraction_command(input_path, output_dir, channels, codec) -> list[str]`
  - `_build_pan_filters(channels) -> str`
  - `_get_codec_for_bit_depth(bit_depth) -> str`

**Dependencies**: `pathlib`, `src.config.enums.BitDepth`

**Lines**: ~50

**SOLID**: Single responsibility - command building only, no execution.

#### 4.3.8 `src/audio/ffmpeg/executor.py`

**Responsibility**: Execute FFmpeg commands and handle errors.

**Contents**:
- `FFmpegExecutor` class:
  - `__init__(output_handler: OutputHandler | None = None)`
  - `execute(command: list[str]) -> None`
  - `extract_channels(input_path, output_dir, channels, bit_depth) -> list[Path]`

**Dependencies**: 
- `subprocess`
- `src.audio.ffmpeg.commands.FFmpegCommandBuilder`
- `src.output.protocols.OutputHandler`
- `src.exceptions.audio`

**Lines**: ~60

**SOLID**: Separated from command building, handles execution concerns.

---

### 4.4 `src/processing/` - Track Building Domain Package

**Responsibility**: Build final output tracks from extracted segments.

#### 4.4.1 `src/processing/__init__.py`

```python
"""Track processing package for Channel Weaver."""
from src.processing.builder import TrackBuilder

__all__ = ["TrackBuilder"]
```

#### 4.4.2 `src/processing/builder.py`

**Responsibility**: Orchestrate track building from segments.

**Contents**:
- `TrackBuilder` class:
  - `__init__(sample_rate, bit_depth, source_bit_depth, temp_dir, output_dir, keep_temp, output_handler)`
  - `build_tracks(channels, buses, segments) -> None`
  - Uses `MonoTrackWriter` and `StereoTrackWriter` internally

**Dependencies**:
- `src.processing.mono.MonoTrackWriter`
- `src.processing.stereo.StereoTrackWriter`
- `src.processing.converters.get_converter`
- `src.config.models`
- `src.output.protocols.OutputHandler`

**Lines**: ~80

**SOLID**: Orchestration class, delegates to specialized writers.

#### 4.4.3 `src/processing/mono.py`

**Responsibility**: Write mono track files from segments.

**Contents**:
- `MonoTrackWriter` class:
  - `__init__(sample_rate, converter, output_dir, output_handler)`
  - `write(channel_config, segments) -> Path`
  - `_concatenate_segments(segments, output_path) -> None`

**Dependencies**:
- `soundfile`
- `numpy`
- `src.processing.converters.protocols.BitDepthConverter`
- `src.config.models.ChannelConfig`
- `src.constants.AUDIO_CHUNK_SIZE`

**Lines**: ~60

**SOLID**: Single responsibility - mono track writing only.

#### 4.4.4 `src/processing/stereo.py`

**Responsibility**: Write stereo bus tracks from segment pairs.

**Contents**:
- `StereoTrackWriter` class:
  - `__init__(sample_rate, converter, output_dir, output_handler)`
  - `write(bus_config, segments) -> Path`
  - `_validate_bus_segments(bus, segments) -> tuple[...]`
  - `_interleave_segments(left_segments, right_segments, output_path) -> None`

**Dependencies**:
- `soundfile`
- `numpy`
- `src.processing.converters.protocols.BitDepthConverter`
- `src.config.models.BusConfig`
- `src.constants.AUDIO_CHUNK_SIZE`
- `src.exceptions.audio`

**Lines**: ~100

**SOLID**: Single responsibility - stereo track writing only.

#### 4.4.5 `src/processing/converters/__init__.py`

```python
"""Bit depth conversion strategies."""
from src.processing.converters.protocols import BitDepthConverter
from src.processing.converters.factory import get_converter

__all__ = ["BitDepthConverter", "get_converter"]
```

#### 4.4.6 `src/processing/converters/protocols.py`

**Responsibility**: Define the converter interface.

**Contents**:
- `BitDepthConverter(Protocol)`:
  - `soundfile_subtype: str` (property)
  - `numpy_dtype: np.dtype` (property)
  - `convert(data: np.ndarray) -> np.ndarray`

**Dependencies**: `typing.Protocol`, `numpy`

**Lines**: ~25

#### 4.4.7 `src/processing/converters/float32.py`

**Responsibility**: 32-bit float conversion.

**Contents**:
- `Float32Converter` class implementing `BitDepthConverter`

**Dependencies**: `numpy`

**Lines**: ~20

#### 4.4.8 `src/processing/converters/int24.py`

**Responsibility**: 24-bit integer conversion.

**Contents**:
- `Int24Converter` class implementing `BitDepthConverter`

**Dependencies**: `numpy`

**Lines**: ~25

#### 4.4.9 `src/processing/converters/int16.py`

**Responsibility**: 16-bit integer conversion.

**Contents**:
- `Int16Converter` class implementing `BitDepthConverter`

**Dependencies**: `numpy`

**Lines**: ~25

#### 4.4.10 `src/processing/converters/source.py`

**Responsibility**: Source bit depth preservation (32-bit PCM).

**Contents**:
- `SourceConverter` class implementing `BitDepthConverter`

**Dependencies**: `numpy`

**Lines**: ~25

#### 4.4.11 `src/processing/converters/factory.py`

**Responsibility**: Factory function for converter selection.

**Contents**:
- `get_converter(bit_depth: BitDepth) -> BitDepthConverter`
- `resolve_bit_depth(requested: BitDepth, source: BitDepth | None) -> BitDepth`

**Dependencies**:
- `src.config.enums.BitDepth`
- All converter implementations

**Lines**: ~30

---

### 4.5 `src/output/` - Output Handling Domain Package

**Responsibility**: Handle user-facing output (console, logging).

#### 4.5.1 `src/output/__init__.py`

```python
"""Output handling package for Channel Weaver."""
from src.output.protocols import OutputHandler
from src.output.console import ConsoleOutputHandler
from src.output.naming import sanitize_filename, build_output_path

__all__ = [
    "OutputHandler",
    "ConsoleOutputHandler",
    "sanitize_filename",
    "build_output_path",
]
```

#### 4.5.2 `src/output/protocols.py`

**Responsibility**: Define output handler interface.

**Contents**:
- `OutputHandler(Protocol)`:
  - `print(message: str, **kwargs) -> None`
  - `info(message: str) -> None`
  - `warning(message: str) -> None`
  - `error(message: str) -> None`

**Dependencies**: `typing.Protocol`

**Lines**: ~25

#### 4.5.3 `src/output/console.py`

**Responsibility**: Rich console-based output.

**Contents**:
- `ConsoleOutputHandler` class implementing `OutputHandler`

**Dependencies**: `rich.console.Console`

**Lines**: ~35

#### 4.5.4 `src/output/logging.py`

**Responsibility**: Logging-based output handler.

**Contents**:
- `LoggingOutputHandler` class implementing `OutputHandler`
- Useful for headless/CI environments

**Dependencies**: `logging`

**Lines**: ~30

**Note**: New addition for improved testability and non-interactive use.

#### 4.5.5 `src/output/naming.py`

**Responsibility**: Filename sanitization and path generation.

**Contents**:
- `sanitize_filename(name: str) -> str` - Make filesystem-safe filenames
- `build_output_path(output_dir: Path, prefix: int, name: str, extension: str) -> Path`
- `build_bus_output_path(output_dir: Path, file_name: str) -> Path`

**Dependencies**: `pathlib`, `re`

**Lines**: ~40

---

### 4.6 `src/exceptions/` - Exception Hierarchy Package

**Responsibility**: Centralized exception definitions.

#### 4.6.1 `src/exceptions/__init__.py`

```python
"""Exception hierarchy for Channel Weaver."""
from src.exceptions.base import ConfigError
from src.exceptions.config import (
    ConfigValidationError,
    DuplicateChannelError,
    ChannelOutOfRangeError,
    BusSlotOutOfRangeError,
    BusSlotDuplicateError,
    BusChannelConflictError,
)
from src.exceptions.audio import AudioProcessingError

__all__ = [
    "ConfigError",
    "ConfigValidationError",
    "DuplicateChannelError",
    "ChannelOutOfRangeError",
    "BusSlotOutOfRangeError",
    "BusSlotDuplicateError",
    "BusChannelConflictError",
    "AudioProcessingError",
]
```

#### 4.6.2 `src/exceptions/base.py`

**Responsibility**: Base exception class.

**Contents**:
- `ConfigError(Exception)` - Base for all custom exceptions

**Lines**: ~15

#### 4.6.3 `src/exceptions/config.py`

**Responsibility**: Configuration-related exceptions.

**Contents**:
- `ConfigValidationError(ConfigError)`
- `DuplicateChannelError(ConfigError)`
- `ChannelOutOfRangeError(ConfigError)`
- `BusSlotOutOfRangeError(ConfigError)`
- `BusSlotDuplicateError(ConfigError)`
- `BusChannelConflictError(ConfigError)`

**Lines**: ~70

#### 4.6.4 `src/exceptions/audio.py`

**Responsibility**: Audio processing exceptions.

**Contents**:
- `AudioProcessingError(ConfigError)` - Audio file operation failures

**Note**: Removes the duplicate definition from `m32_processor.py`.

**Lines**: ~20

---

### 4.7 `src/types.py` - Type Aliases (Unchanged Structure)

**Responsibility**: Central type definitions.

**Contents**:
- `SegmentMap: TypeAlias = dict[int, list[Path]]`
- `ChannelData: TypeAlias = dict[str, object]`
- `BusData: TypeAlias = dict[str, object]`
- `AudioInfo: TypeAlias = tuple[int, int, str]`
- `ChannelDict(TypedDict)` - For raw channel config
- `BusDict(TypedDict)` - For raw bus config

**Lines**: ~30

---

### 4.8 `src/constants.py` - Application Constants

**Responsibility**: Central constant definitions.

**Contents**:
- `AUDIO_CHUNK_SIZE: int = 131_072`
- `VERSION: str = "0.1.0"`
- `SUPPORTED_AUDIO_EXTENSIONS: tuple[str, ...] = (".wav", ".WAV")`
- `DEFAULT_OUTPUT_SUFFIX: str = "_processed"`

**Lines**: ~15

---

## 5. Module Specifications

### 5.1 Complete Module Dependency Matrix

| Module | Imports From | Imported By |
|--------|--------------|-------------|
| `cli/app.py` | `typer`, `constants` | `__main__` |
| `cli/commands.py` | `cli/utils`, `config/*`, `audio/extractor`, `processing/builder`, `output/*`, `exceptions` | `cli/app` |
| `cli/utils.py` | `pathlib` | `cli/commands` |
| `config/loader.py` | `config/models`, `config/validators`, `exceptions/config`, `types` | `cli/commands` |
| `config/models.py` | `pydantic`, `config/enums` | `config/loader`, `config/validators`, `processing/*` |
| `config/enums.py` | `enum` | `config/models`, `audio/*`, `processing/*` |
| `config/validators.py` | `config/models`, `config/enums`, `exceptions/config` | `config/loader` |
| `config/defaults.py` | `types` | `cli/commands` |
| `audio/discovery.py` | `pathlib`, `re` | `audio/extractor` |
| `audio/validation.py` | `soundfile`, `audio/info`, `config/enums`, `exceptions/audio` | `audio/extractor` |
| `audio/info.py` | `soundfile`, `subprocess`, `json`, `config/enums` | `audio/validation` |
| `audio/extractor.py` | `audio/discovery`, `audio/validation`, `audio/ffmpeg/*`, `output/protocols`, `types` | `cli/commands` |
| `audio/ffmpeg/commands.py` | `pathlib`, `config/enums` | `audio/ffmpeg/executor` |
| `audio/ffmpeg/executor.py` | `subprocess`, `audio/ffmpeg/commands`, `output/protocols`, `exceptions/audio` | `audio/extractor` |
| `processing/builder.py` | `processing/mono`, `processing/stereo`, `processing/converters`, `config/models`, `output/protocols` | `cli/commands` |
| `processing/mono.py` | `soundfile`, `numpy`, `processing/converters/protocols`, `config/models`, `constants` | `processing/builder` |
| `processing/stereo.py` | `soundfile`, `numpy`, `processing/converters/protocols`, `config/models`, `constants`, `exceptions/audio` | `processing/builder` |
| `processing/converters/*.py` | `numpy`, `config/enums` | `processing/builder` |
| `output/protocols.py` | `typing` | `audio/extractor`, `processing/builder` |
| `output/console.py` | `rich`, `output/protocols` | `cli/commands` |
| `output/naming.py` | `pathlib`, `re` | `processing/mono`, `processing/stereo` |
| `exceptions/*.py` | - | All modules that can raise errors |

### 5.2 Line Count Summary

| Package | Estimated Lines |
|---------|-----------------|
| `src/cli/` | ~180 |
| `src/config/` | ~390 |
| `src/audio/` | ~400 |
| `src/processing/` | ~390 |
| `src/output/` | ~130 |
| `src/exceptions/` | ~105 |
| `src/types.py` | ~30 |
| `src/constants.py` | ~15 |
| **Total** | **~1,640** |

**Comparison**: Current codebase is ~1,424 lines. The restructured version is slightly larger due to:
- More explicit module boundaries
- Additional docstrings per module
- New `LoggingOutputHandler` for testability
- Cleaner `__init__.py` re-exports

---

## 6. Migration Guide

### 6.1 File Mapping

| Current File | New Location(s) |
|--------------|-----------------|
| `m32_processor.py` | Split into: |
| - `ConfigLoader` class | `config/loader.py` |
| - `AudioExtractor` class | `audio/extractor.py` |
| - `TrackBuilder` class | `processing/builder.py` |
| - `_sanitize_filename()` | `output/naming.py` |
| - `_resolve_bit_depth()` | `processing/converters/factory.py` |
| - `_bit_depth_from_subtype()` | `audio/info.py` |
| - `_get_audio_info_ffmpeg()` | `audio/info.py` |
| `main.py` | Split into: |
| - CLI app/commands | `cli/app.py`, `cli/commands.py` |
| - Path utilities | `cli/utils.py` |
| - CHANNELS/BUSES data | `config/defaults.py` |
| `models.py` | Split into: |
| - Enums | `config/enums.py` |
| - Pydantic models | `config/models.py` |
| `validators.py` | `config/validators.py` (minor path updates) |
| `exceptions.py` | Split into: |
| - Base exception | `exceptions/base.py` |
| - Config exceptions | `exceptions/config.py` |
| - Audio exceptions | `exceptions/audio.py` |
| `converters.py` | Split into: |
| - Protocol | `processing/converters/protocols.py` |
| - Each converter | `processing/converters/{name}.py` |
| - Factory | `processing/converters/factory.py` |
| `protocols.py` | `output/protocols.py` + `output/console.py` |
| `types.py` | `types.py` (unchanged location) |
| `constants.py` | `constants.py` (unchanged, expanded) |

### 6.2 Import Path Changes

| Old Import | New Import |
|------------|------------|
| `from src.m32_processor import AudioExtractor` | `from src.audio import AudioExtractor` |
| `from src.m32_processor import ConfigLoader` | `from src.config import ConfigLoader` |
| `from src.m32_processor import TrackBuilder` | `from src.processing import TrackBuilder` |
| `from src.models import ChannelConfig, BusConfig` | `from src.config import ChannelConfig, BusConfig` |
| `from src.models import ChannelAction, BusSlot, BitDepth` | `from src.config import ChannelAction, BusSlot, BitDepth` |
| `from src.converters import get_converter` | `from src.processing.converters import get_converter` |
| `from src.protocols import OutputHandler, ConsoleOutputHandler` | `from src.output import OutputHandler, ConsoleOutputHandler` |
| `from src.validators import ChannelValidator` | `from src.config import ChannelValidator` |

---

## 7. Implementation Order

### Phase 1: Foundation (No Breaking Changes)

1. **Create new package directories** (empty `__init__.py` files)
2. **Create `exceptions/` package** - Split existing exceptions
3. **Create `output/` package** - Move protocols and handlers
4. **Create `processing/converters/`** - Split converters module

### Phase 2: Configuration Domain

5. **Create `config/enums.py`** - Extract enums from models
6. **Create `config/models.py`** - Move Pydantic models
7. **Create `config/validators.py`** - Move validators (update imports)
8. **Create `config/loader.py`** - Extract ConfigLoader from m32_processor
9. **Create `config/defaults.py`** - Extract CHANNELS/BUSES from main.py

### Phase 3: Audio Domain

10. **Create `audio/discovery.py`** - Extract file discovery logic
11. **Create `audio/info.py`** - Extract audio info retrieval
12. **Create `audio/validation.py`** - Extract parameter validation
13. **Create `audio/ffmpeg/`** - Extract FFmpeg command building/execution
14. **Create `audio/extractor.py`** - Refactor AudioExtractor to use new modules

### Phase 4: Processing Domain

15. **Create `output/naming.py`** - Extract filename sanitization
16. **Create `processing/mono.py`** - Extract mono track writing
17. **Create `processing/stereo.py`** - Extract stereo track writing
18. **Create `processing/builder.py`** - Refactor TrackBuilder

### Phase 5: CLI Layer

19. **Create `cli/utils.py`** - Extract path utilities from main.py
20. **Create `cli/app.py`** - Extract Typer app definition
21. **Create `cli/commands.py`** - Refactor main command

### Phase 6: Cleanup

22. **Delete `m32_processor.py`**
23. **Update `main.py`** to import from `cli/app.py`
24. **Update `pyproject.toml`** if entry point changes
25. **Update all tests** with new import paths

---

## 8. Testing Strategy

### 8.1 Test Structure

```
tests/
├── __init__.py
├── conftest.py                 # Shared fixtures
├── unit/
│   ├── __init__.py
│   ├── config/
│   │   ├── test_loader.py
│   │   ├── test_models.py
│   │   ├── test_validators.py
│   │   └── test_enums.py
│   ├── audio/
│   │   ├── test_discovery.py
│   │   ├── test_validation.py
│   │   ├── test_info.py
│   │   └── test_ffmpeg.py
│   ├── processing/
│   │   ├── test_builder.py
│   │   ├── test_mono.py
│   │   ├── test_stereo.py
│   │   └── test_converters.py
│   └── output/
│       ├── test_console.py
│       ├── test_logging.py
│       └── test_naming.py
└── integration/
    ├── __init__.py
    └── test_full_pipeline.py
```

### 8.2 Test Guidelines

1. **Unit tests**: Each module should have corresponding unit tests
2. **Mocking**: Use dependency injection to mock:
   - `OutputHandler` for silent tests
   - FFmpeg executor for fast tests
   - File system operations where needed
3. **Integration tests**: Test full pipeline with real audio files
4. **Fixture files**: Small WAV files for audio tests

### 8.3 Coverage Targets

| Package | Target Coverage |
|---------|-----------------|
| `config/` | 95%+ |
| `audio/` | 85%+ (FFmpeg execution may be mocked) |
| `processing/` | 90%+ |
| `output/` | 80%+ |
| `cli/` | 70%+ (integration-heavy) |

---

## Appendix A: SOLID Principle Verification

### A.1 Single Responsibility Principle (SRP)

| New Module | Single Responsibility |
|------------|----------------------|
| `audio/discovery.py` | Discover audio files in directory |
| `audio/validation.py` | Validate audio parameter consistency |
| `audio/info.py` | Retrieve audio file metadata |
| `audio/ffmpeg/commands.py` | Build FFmpeg commands |
| `audio/ffmpeg/executor.py` | Execute FFmpeg commands |
| `processing/mono.py` | Write mono tracks |
| `processing/stereo.py` | Write stereo bus tracks |
| `output/naming.py` | Sanitize filenames |
| `config/loader.py` | Load and complete configuration |

### A.2 Open/Closed Principle (OCP)

**Extensible without modification**:
- Add new `BitDepthConverter` implementations without changing factory
- Add new `OutputHandler` implementations (e.g., JSON output)
- Add new `BusType` values with `required_slots()` method

### A.3 Liskov Substitution Principle (LSP)

All protocol implementations are fully substitutable:
- Any `BitDepthConverter` can be used by `TrackBuilder`
- Any `OutputHandler` can be injected into processing classes

### A.4 Interface Segregation Principle (ISP)

Protocols are focused:
- `BitDepthConverter`: Only conversion properties and method
- `OutputHandler`: Only message output methods
- No "god interfaces" that force unused implementations

### A.5 Dependency Inversion Principle (DIP)

High-level modules depend on abstractions:
- `TrackBuilder` depends on `BitDepthConverter` protocol, not concrete classes
- `AudioExtractor` depends on `OutputHandler` protocol
- Factory functions provide concrete implementations

---

## Appendix B: Files to Delete After Migration

1. `src/m32_processor.py` - Fully replaced by new structure
2. Old `src/models.py` - Replaced by `config/enums.py` and `config/models.py`
3. Old `src/validators.py` - Moved to `config/validators.py`
4. Old `src/exceptions.py` - Replaced by `exceptions/` package
5. Old `src/converters.py` - Replaced by `processing/converters/` package
6. Old `src/protocols.py` - Replaced by `output/` package

---

## Appendix C: Future Extensibility

This structure enables future enhancements:

1. **External configuration files**: Add `config/file_loader.py` for JSON/YAML/TOML support
2. **New bus types**: Add mono buses, surround (5.1/7.1) by extending `BusType` and creating new writers
3. **Alternative extraction backends**: Add `audio/native/` for pure-Python extraction (no FFmpeg)
4. **Progress tracking**: Add `output/progress.py` with `ProgressHandler` protocol
5. **Plugin system**: Add `plugins/` package for user-defined transformations
6. **Configuration presets**: Add `config/presets/` with per-console defaults (M32, X32, etc.)
