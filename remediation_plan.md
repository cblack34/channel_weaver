# Remediation Plan: Channel Weaver

## Overview

This plan addresses all issues identified in `evaluation.md` plus additional issues discovered through library API validation to achieve 100% PRD compliance. The approach is structured in five phases, ordered by dependency to minimize rework:

1. **Critical API Fixes** – Fix deprecated library APIs and structural issues
2. **Preparation & Bug Fixes** – Resolve dependencies, clean up duplicates, fix logic bugs
3. **Integration** – Wire CLI to core processing logic, ensuring memory-efficient pipeline
4. **SOLID & Code Smells** – Apply architectural improvements for maintainability
5. **Enhancements & Documentation** – Polish with logging, type hints, docstrings

Each phase builds on the previous, ensuring foundational issues are resolved before integration, and integration is stable before refactoring.

---

## Phase 1: Critical API Fixes (Library Validation Findings)

> **Context**: Validated APIs using Context7 for Pydantic v2, Typer, PySoundFile, and NumPy.

### 1.1 Pydantic v2 Migration ⚠️ BREAKING CHANGE
The code uses **deprecated `@validator` decorator** which should be `@field_validator` in Pydantic v2.

- [x] **Migrate `@validator` to `@field_validator` in ChannelConfig**:
  ```python
  # OLD (deprecated):
  @validator("action")
  def validate_action(cls, value: ChannelAction) -> ChannelAction:
      return value
  
  # NEW (Pydantic v2):
  from pydantic import field_validator
  
  @field_validator("action")
  @classmethod
  def validate_action(cls, value: ChannelAction) -> ChannelAction:
      return value
  ```

- [x] **Migrate `@validator` to `@field_validator` in BusConfig**:
  ```python
  # OLD (deprecated):
  @validator("slots")
  def validate_slots(cls, value: dict[BusSlot, int], values: dict[str, object]) -> dict[BusSlot, int]:
      bus_type = values.get("type", BusType.STEREO)
      ...
  
  # NEW (Pydantic v2) - use model_validator for cross-field access:
  from pydantic import model_validator
  from typing import Self
  
  @model_validator(mode='after')
  def validate_slots(self) -> Self:
      required = self.type.required_slots()
      if set(self.slots.keys()) != required:
          required_slots = ", ".join(slot.name for slot in sorted(required, key=lambda s: s.name))
          raise ValueError(f"{self.type.name} buses require slots: {required_slots}")
      return self
  ```

- [x] **Update imports**: Replace `from pydantic import validator` with `from pydantic import field_validator, model_validator`

- [x] **Remove unused pydantic-settings**: Delete from `pyproject.toml` as it's not used in the codebase

### 1.2 Package Structure
- [x] **Create `src/__init__.py`**: Make `src/` a proper Python package for clean imports
  ```python
  """Channel Weaver - Midas M32 multitrack processor."""
  __version__ = "0.1.0"
  ```

- [x] **Create `src/exceptions.py`**: Extract all custom exceptions to dedicated module for reusability
  ```python
  """Custom exceptions for Channel Weaver."""
  
  class ConfigError(Exception):
      """Base class for user-facing configuration errors."""
  
  class ConfigValidationError(ConfigError): ...
  class DuplicateChannelError(ConfigError): ...
  # ... etc
  ```

- [x] **Create `src/models.py`**: Extract all Pydantic models and enums
  ```python
  """Data models for Channel Weaver configuration."""
  from enum import Enum, auto
  from pydantic import BaseModel, Field, field_validator, model_validator
  
  class ChannelAction(Enum): ...
  class BusSlot(Enum): ...
  class BusType(Enum): ...
  class BitDepth(str, Enum): ...
  class ChannelConfig(BaseModel): ...
  class BusConfig(BaseModel): ...
  ```

- [x] **Create `src/constants.py`**: Centralize magic numbers
  ```python
  """Constants for Channel Weaver."""
  AUDIO_CHUNK_SIZE: int = 131_072  # frames per read operation
  VERSION: str = "0.1.0"
  ```

### 1.3 Typer API Corrections
- [x] **Fix version callback signature**: Add `is_eager=True` for proper ordering
  ```python
  def version_callback(value: bool) -> None:
      if value:
          typer.echo(f"Channel Weaver v{VERSION}")
          raise typer.Exit()
  
  # In main() signature:
  version: bool = typer.Option(
      None, "--version", "-v",
      callback=version_callback,
      is_eager=True,  # Critical: process before other options
      is_flag=True,
      help="Show version and exit."
  )
  ```

### 1.4 Verify Library API Usage
- [x] **PySoundFile API**: Confirmed correct usage of:
  - `sf.SoundFile` context manager with `'w'`, `'r'`, `'r+'` modes ✓
  - `sf.info()` for metadata extraction ✓
  - `subtype` parameter: `'PCM_24'`, `'PCM_16'`, `'FLOAT'` ✓
  
- [x] **NumPy API**: Confirmed correct usage of:
  - `astype(dtype, copy=False)` for efficient type conversion ✓
  - `np.clip()` for value clamping ✓
  - `np.column_stack()` for stereo interleaving ✓

---

## Phase 2: Preparation & Bug Fixes

### 2.1 Dependency Issues
- [x] **Verify Rich dependency**: Confirm `rich>=14.2.0` is in `pyproject.toml` ✓ (added via `uv add rich`)
- [x] **Remove unused dependency**: Delete `pydantic-settings` from `pyproject.toml`
- [x] **Verify**: Run `uv sync` and confirm no import errors in all modules

### 2.2 Remove Code Duplication (Prerequisite for Integration)
- [x] **Delete duplicate definitions from main.py**: Remove `ChannelAction`, `BusSlot`, `BusType`, `BitDepth`, `ChannelConfig`, `BusConfig`, and simplified `ConfigLoader` classes
- [x] **Add imports from src.models**: Import all shared types and classes from the new `models.py`
- [x] **Sync BitDepth enum**: Ensure `main.py` uses `BitDepth` from `models.py` which includes `SOURCE` value
- [x] **Verify**: All files compile without import errors

### 2.3 Logic and Validation Bugs
- [x] **Fix _sort_key edge case**: Modify `AudioExtractor._sort_key()` to return `(float('inf'), path.name)` for non-numeric filenames:
  ```python
  def _sort_key(self, path: Path) -> tuple[int | float, str]:
      match = re.search(r"(\d+)", path.stem)
      if match:
          return int(match.group(1)), path.name
      return float('inf'), path.name  # Non-numeric files sort last
  ```

- [x] **Fix double cleanup risk**: Remove temp cleanup from `TrackBuilder.build_tracks()`:
  ```python
  def build_tracks(self, channels, buses, segments) -> None:
      self._write_mono_tracks(channels, segments)
      self._write_buses(buses, segments)
      # REMOVED: if not self.keep_temp and self.temp_dir.exists(): shutil.rmtree(...)
      # Cleanup is handled by AudioExtractor.cleanup()
  ```

- [x] **Improve channel auto-creation warnings**: Use `logging.warning()` instead of `warnings.warn()`:
  ```python
  import logging
  logger = logging.getLogger(__name__)
  
  # Replace:
  warnings.warn(f"Auto-creating channel {ch:02d}...", stacklevel=2)
  # With:
  logger.warning("Auto-creating channel %02d for bus assignment with action=BUS.", ch)
  ```

### 2.4 Configuration and Validation Issues
- [x] **Add slot value validation in BusConfig**: Validate all slot values are `>= 1`:
  ```python
  @model_validator(mode='after')
  def validate_slots(self) -> Self:
      # Validate slot channel numbers are positive
      for slot, ch in self.slots.items():
          if ch < 1:
              raise ValueError(f"Slot {slot.name} channel must be >= 1, got {ch}")
      # Validate required slots
      required = self.type.required_slots()
      if set(self.slots.keys()) != required:
          raise ValueError(f"{self.type.name} buses require slots: {', '.join(s.name for s in required)}")
      return self
  ```

### 2.5 File and Documentation Issues
- [ ] **Fix README.md**: Update entry point references:
  - Change `channel_weaver.py` → `python -m src.main` or `uv run python -m src.main`
  - Add pip alternative: `pip install -e .` then `channel-weaver <input>`
  
- [ ] **Clean spec.md**: Delete irrelevant audio plugin comparison content or remove file entirely

- [ ] **Verify**: README accurately reflects how to run the tool

---

## Phase 3: Integration

### 3.1 Wire CLI to Core Processing Logic
- [ ] **Update imports in main.py**: Import from new module structure:
  ```python
  from src.models import (
      ChannelAction, BusSlot, BusType, BitDepth,
      ChannelConfig, BusConfig
  )
  from src.exceptions import ConfigError, AudioProcessingError
  from src.m32_processor import AudioExtractor, TrackBuilder, ConfigLoader
  from src.constants import VERSION
  from rich.console import Console
  ```

- [ ] **Create shared Console instance**: Instantiate `Console()` once in `main()` for injection

### 3.2 Implement Processing Pipeline
- [ ] **Replace placeholder with AudioExtractor initialization**:
  ```python
  console = Console()
  extractor = AudioExtractor(
      input_dir=normalized_input,
      temp_dir=temp_root,
      keep_temp=keep_temp,
      console=console,
  )
  ```

- [ ] **Discover and validate input files**: Call `extractor.discover_and_validate()`

- [ ] **Get detected channel count**: Store `extractor.channels` for ConfigLoader

- [ ] **Replace main.py ConfigLoader usage**: Use m32_processor's ConfigLoader with `detected_channel_count`:
  ```python
  config_loader = ConfigLoader(CHANNELS, BUSES, detected_channel_count=extractor.channels)
  channels, buses = config_loader.load()
  ```

- [ ] **Extract segments**: Call `segments = extractor.extract_segments(target_bit_depth=bit_depth)`

- [ ] **Build tracks with TrackBuilder**:
  ```python
  builder = TrackBuilder(
      sample_rate=extractor.sample_rate,
      bit_depth=bit_depth,
      source_bit_depth=extractor.bit_depth,
      temp_dir=temp_root,
      output_dir=output_dir,
      keep_temp=keep_temp,
      console=console,
  )
  builder.build_tracks(channels, buses, segments)
  ```

- [ ] **Handle cleanup**: Call `extractor.cleanup()` after successful processing

### 3.3 Error Handling Integration
- [ ] **Wrap processing in try/except**: Catch `ConfigError`, `AudioProcessingError`:
  ```python
  try:
      # Processing pipeline here
      ...
  except (ConfigError, AudioProcessingError) as e:
      console.print(f"[red]Error:[/red] {e}")
      raise typer.Exit(code=1)
  finally:
      if not keep_temp:
          extractor.cleanup()
  ```

- [ ] **Ensure cleanup on error**: Use `finally` block to clean temp files if error occurs (unless keep_temp)

### 3.4 CLI Alignment with PRD
- [ ] **Update bit_depth default**: Change default from `BitDepth.FLOAT32` to `BitDepth.SOURCE`:
  ```python
  bit_depth: BitDepth = typer.Option(
      BitDepth.SOURCE,  # Changed from FLOAT32 per PRD
      "--bit-depth", "-b",
      help="Target bit depth for output files (source=preserve original)"
  )
  ```

- [ ] **Add --version option**: Implement with eager callback (see Phase 1.3)

- [ ] **Verify**: CLI `--help` shows all options matching PRD specification

---

## Phase 4: SOLID Principles & Code Smells

### 4.1 Single Responsibility Principle (SRP)

- [ ] **Create `src/validators.py`**: Extract validation logic to dedicated module:
  ```python
  """Validation utilities for Channel Weaver configuration."""
  from .models import ChannelConfig, BusConfig, ChannelAction
  from .exceptions import (
      DuplicateChannelError, ChannelOutOfRangeError,
      BusSlotOutOfRangeError, BusSlotDuplicateError, BusChannelConflictError
  )
  
  class ChannelValidator:
      """Validates channel configuration against detected channel count."""
      
      def __init__(self, detected_channel_count: int) -> None:
          self._detected_channels = detected_channel_count
      
      def validate(self, channels: list[ChannelConfig]) -> None:
          """Validate channel numbers are unique and within range."""
          ...
  
  class BusValidator:
      """Validates bus configuration against detected channel count."""
      ...
  ```

- [ ] **Refactor ConfigLoader**: Keep as orchestrator calling validators:
  ```python
  class ConfigLoader:
      def __init__(self, ..., channel_validator: ChannelValidator | None = None):
          self._channel_validator = channel_validator or ChannelValidator(detected_channel_count)
  ```

### 4.2 Open-Closed Principle (OCP)

- [ ] **Create `src/converters.py`**: Define abstract interface for bit depth operations:
  ```python
  """Bit depth conversion strategies."""
  from abc import ABC, abstractmethod
  from typing import Protocol
  import numpy as np
  from .models import BitDepth
  
  class BitDepthConverter(Protocol):
      """Protocol for bit depth conversion strategies."""
      
      @property
      def soundfile_subtype(self) -> str: ...
      
      @property
      def numpy_dtype(self) -> np.dtype: ...
      
      def convert(self, data: np.ndarray) -> np.ndarray: ...
  
  class Float32Converter:
      """Converter for 32-bit float output."""
      soundfile_subtype = "FLOAT"
      numpy_dtype = np.float32
      
      def convert(self, data: np.ndarray) -> np.ndarray:
          return data.astype(np.float32, copy=False)
  
  class Int24Converter:
      """Converter for 24-bit integer output."""
      soundfile_subtype = "PCM_24"
      numpy_dtype = np.int32
      
      def convert(self, data: np.ndarray) -> np.ndarray:
          float_data = data.astype(np.float32, copy=False)
          scaled = np.clip(np.rint(float_data * 8388608.0), -8388608, 8388607)
          return scaled.astype(np.int32)
  
  class Int16Converter:
      """Converter for 16-bit integer output."""
      ...
  
  def get_converter(bit_depth: BitDepth) -> BitDepthConverter:
      """Factory function to get appropriate converter."""
      converters = {
          BitDepth.FLOAT32: Float32Converter(),
          BitDepth.INT24: Int24Converter(),
          BitDepth.INT16: Int16Converter(),
      }
      if bit_depth is BitDepth.SOURCE:
          raise ValueError("Resolve SOURCE bit depth before getting converter")
      return converters[bit_depth]
  ```

- [ ] **Refactor `_soundfile_subtype()`, `_numpy_dtype()`, `_convert_dtype()`**: Replace with converter factory pattern

### 4.3 Liskov Substitution Principle (LSP)

- [ ] **Verify exception hierarchy**: All custom exceptions properly inherit from `ConfigError`:
  ```
  ConfigError (base)
  ├── ConfigValidationError
  ├── DuplicateChannelError
  ├── ChannelOutOfRangeError
  ├── BusSlotOutOfRangeError
  ├── BusSlotDuplicateError
  ├── BusChannelConflictError
  └── AudioProcessingError
  ```

- [ ] **Add docstrings to exceptions**: Document when each exception is raised

### 4.4 Interface Segregation Principle (ISP)

- [ ] **Keep TrackBuilder unified**: After analysis, `build_tracks` always writes both mono and stereo, so splitting adds complexity without benefit. Mark as intentional design decision.

### 4.5 Dependency Inversion Principle (DIP)

- [ ] **Define OutputHandler protocol** (optional, for testability):
  ```python
  from typing import Protocol
  
  class OutputHandler(Protocol):
      """Protocol for output handling (console, logging, etc.)."""
      def info(self, message: str) -> None: ...
      def warning(self, message: str) -> None: ...
      def error(self, message: str) -> None: ...
  ```

- [ ] **Inject validators into ConfigLoader**: Pass validator instances instead of creating internally

### 4.6 Code Smells

- [ ] **Extract type aliases** in `src/types.py`:
  ```python
  """Type aliases for Channel Weaver."""
  from pathlib import Path
  from typing import TypeAlias
  
  SegmentMap: TypeAlias = dict[int, list[Path]]
  ChannelData: TypeAlias = dict[str, object]
  BusData: TypeAlias = dict[str, object]
  ```

- [ ] **Break down long methods**:
  - Split `AudioExtractor.extract_segments()`:
    - `_create_segment_writers()`
    - `_process_file_chunks()`
    - `_finalize_segments()`
  - Split `TrackBuilder._write_buses()`:
    - `_validate_bus_segments()`
    - `_interleave_stereo()`
    - `_write_stereo_file()`

- [ ] **Standardize naming**: Document convention: `ch` for short variable names within methods, `channel` for function parameters and class attributes

- [ ] **Remove dead imports**: Audit and remove unused imports:
  - `warnings` (if migrated to logging)
  - Check `ExitStack` usage in m32_processor.py (currently used ✓)

- [ ] **Fix inconsistent method naming**: Standardize to `_load_*` for private, `load_*` for public

---

## Phase 5: Enhancements & Documentation

### 5.1 Logging

- [ ] **Add logging configuration**: Create logger at module level with configurable level:
  ```python
  import logging
  
  logger = logging.getLogger(__name__)
  ```
  
- [ ] **Replace print/echo statements**: Convert `console.print()` to `logger.info()` for operational messages
- [ ] **Keep Rich for user-facing output**: Use Rich Console for progress bars and formatted output, logging for debug/info
- [ ] **Add --verbose flag**: Wire to logging level adjustment:
  ```python
  verbose: bool = typer.Option(
      False, "--verbose", "-v",
      help="Enable verbose debug output"
  )
  ```

### 5.2 Type Hints

- [ ] **Complete return type hints**: Add return types to all functions (especially those returning `None`)
- [ ] **Create `src/types.py`**: Add type aliases for complex types:
  ```python
  """Type aliases for Channel Weaver."""
  from pathlib import Path
  from typing import TypeAlias
  
  SegmentMap: TypeAlias = dict[int, list[Path]]
  ChannelData: TypeAlias = dict[str, object]
  BusData: TypeAlias = dict[str, object]
  AudioInfo: TypeAlias = tuple[int, int, str]  # (sample_rate, channels, subtype)
  ```
  
- [ ] **Use TypedDict for config dicts**: Consider `TypedDict` for CHANNELS and BUSES raw data structures:
  ```python
  from typing import TypedDict
  
  class ChannelDict(TypedDict):
      channel: int
      name: str
      action: str
  ```

### 5.3 Docstrings

- [ ] **Add module docstrings**: Ensure both main.py and m32_processor.py have comprehensive module docstrings
- [ ] **Add class docstrings**: Document purpose, usage, and attributes for all classes
- [ ] **Add method docstrings**: Use Google/NumPy style for all public methods with Args, Returns, Raises sections
- [ ] **Document configuration format**: Add docstring explaining CHANNELS and BUSES structure

### 5.4 Error Messages

- [ ] **Enhance ConfigError messages**: Include context about what was being validated
- [ ] **Add suggestions in errors**: E.g., "Did you mean to set action=BUS for channel X?"
- [ ] **Validate error message clarity**: Review all custom exceptions for user-friendliness

---

## Final Verification

### End-to-End Checklist

#### Critical API Compliance
- [ ] **Pydantic v2 compliant**: All `@validator` replaced with `@field_validator` + `@classmethod`
- [ ] **No deprecated imports**: No imports from `pydantic.validator`, use `pydantic.field_validator`
- [ ] **Typer callbacks correct**: Version callback uses `is_eager=True`

#### Package Structure
- [ ] **Package importable**: `python -c "import src"` works without error
- [ ] **No circular imports**: All module imports resolve cleanly
- [ ] **Single source of truth**: Types/models imported, not duplicated

#### CLI Behavior
- [ ] **CLI invocation**: `python -m src.main <input_path>` runs without errors
- [ ] **Help text**: `--help` matches PRD specification
- [ ] **Version**: `--version` displays version and exits
- [ ] **Bit depth default**: Without `--bit-depth`, output matches source bit depth
- [ ] **Output directory**: Default creates sibling `<input>_processed` folder
- [ ] **Output directory conflict**: If `_processed` exists, creates `_processed_v2`

#### Processing Pipeline
- [ ] **Memory efficiency**: Large files process without excessive RAM (chunked processing)
- [ ] **Temp cleanup**: Temp files deleted on success, preserved with `--keep-temp`
- [ ] **Error handling**: Invalid inputs produce clear, actionable error messages
- [ ] **Mono tracks**: Output as `01_Kick In.wav` with sanitized filenames
- [ ] **Stereo buses**: Output as `07_Overheads.wav` per bus configuration

#### Validation
- [ ] **Channel auto-creation**: Missing channels auto-created with warnings logged
- [ ] **Validation**: Invalid channel/bus configs rejected with specific errors
- [ ] **Edge cases**: Non-numeric filenames handled gracefully (logged warning)

#### Code Quality
- [ ] **No duplicate code**: Single source of truth for all types and models
- [ ] **Import structure**: Clean imports with no circular dependencies
- [ ] **No magic numbers**: All constants extracted to `src/constants.py`
- [ ] **Type hints complete**: All functions have parameter and return type hints

### PRD Compliance Matrix

| PRD Requirement | Status | Notes |
|-----------------|--------|-------|
| Discover & sort WAV files | Verify | Check `_sort_key()` edge case |
| Validate consistent audio params | Verify | |
| Fail fast with clear errors | Verify | |
| Sibling output directory | Verify | |
| Handle directory conflicts | Verify | |
| Bit-perfect concatenation | Verify | |
| Memory-safe (chunked) | Verify | AUDIO_CHUNK_SIZE constant |
| Temp file cleanup | Verify | Check double cleanup issue |
| Channel routing (PROCESS/BUS/SKIP) | Verify | |
| Stereo bus creation | Verify | |
| Filename sanitization | Verify | |
| Pydantic validation | Verify | Must use v2 API |
| Runtime channel count validation | Verify | |
| Custom exceptions | Verify | |
| Typer CLI | Verify | |
| Rich progress bars | Verify | |
| ConfigLoader/AudioExtractor/TrackBuilder | Verify | |
| Dependency injection | Verify | |

### Testing Recommendations (Post-Implementation)

- [ ] **Unit tests**: Add pytest tests for validators, converters, config loading
- [ ] **Integration tests**: Test full pipeline with sample audio files
- [ ] **Edge case tests**: Non-numeric filenames, empty directories, corrupted files
- [ ] **Performance tests**: Measure memory usage with large files
