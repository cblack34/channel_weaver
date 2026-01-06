# Click Feature Implementation Plan

This document outlines the detailed step-by-step implementation plan for adding intelligent section splitting based on a click track to the Channel Weaver application. The plan is structured as a series of agile user stories, each building upon the previous ones to ensure a logical progression of development. Each story includes a detailed description of the work required, acceptance criteria, and definition of done.

For full feature requirements, refer to the [Click Feature PRD](./Click%20Feature%20PRD.md).

---

## Technical Decisions

The following technical decisions guide the implementation:

### Audio Analysis Library: Custom Implementation with NumPy/SciPy/soundfile
- **Decision**: Build a custom onset detection and BPM estimation solution using NumPy, SciPy, and soundfile.
- **Rationale**: This approach uses well-maintained, widely-compatible scientific Python libraries that have robust Python 3.14+ support. NumPy provides efficient array operations, SciPy provides signal processing algorithms (`scipy.signal.find_peaks`, filtering, spectral analysis), and soundfile provides memory-efficient streaming audio I/O via libsndfile.
- **Key Components**:
  - `soundfile.blocks()`: Stream audio in configurable block sizes without loading entire files into memory.
  - `scipy.signal.find_peaks()`: Peak detection with configurable prominence, distance, and height thresholds.
  - `numpy.fft.rfft()` / `scipy.fft.rfft()`: Spectral analysis for onset detection functions.
  - `scipy.signal.butter()` / `scipy.signal.sosfilt()`: Bandpass filtering to isolate click frequencies.
- **Installation**: All libraries are available via `uv add numpy scipy soundfile`.
- **Architecture Note**: Implement behind a protocol/abstract interface (`ClickAnalyzerProtocol`) to allow future replacement with alternative implementations if needed, following the Dependency Inversion Principle.

### WAV Metadata Embedding: ID3 Tags with Mutagen
- **Decision**: Use ID3 tags embedded in WAV files for BPM metadata storage using the TBPM frame.
- **Rationale**: Research confirmed that RIFF INFO chunks do not have a standardized BPM field. ID3 tags can be embedded in WAV files and provide the TBPM frame specifically for BPM values, which is widely supported by audio applications and DAWs.
- **Library**: [mutagen](https://github.com/quodlibet/mutagen) - comprehensive Python library for audio metadata manipulation with excellent ID3 tag support.
- **Implementation**: Use `mutagen.File` to load WAV files and `mutagen.id3.TBPM` to set/read BPM values.
- **Compatibility**: ID3 tags in WAV files are supported by most professional audio software and can be read by tools like ffprobe and media players.

### Memory Efficiency: Streaming/Chunked Processing
- **Decision**: Implement streaming/chunked analysis for click track processing to support multi-hour recordings.
- **Implementation**: Use `soundfile.blocks()` with configurable `blocksize` and optional `overlap` to read audio in chunks without loading the full file into memory. Process each block through the onset detection pipeline and accumulate results.
- **Rationale**: Ensures the feature scales to long recording sessions without memory constraints. The `soundfile` library wraps libsndfile, which is highly optimized for streaming audio I/O.

---

## Architecture Principles

The following principles apply to all stories in this implementation:

### Interfaces as Protocols
All interfaces must be defined as Python `Protocol` classes (from `typing`), following the existing project pattern in `src/config/protocols.py`. Protocols provide structural subtyping and enable the Dependency Inversion Principle. All protocols must be decorated with `@runtime_checkable`.

### Data Models as Pydantic Models
All data models must use **Pydantic** (not dataclasses) for consistency with the existing codebase. Pydantic provides built-in validation, serialization to/from JSON, and follows the patterns established in `src/config/models.py`. Use Pydantic v2 API patterns (`@field_validator`, `@model_validator`).

### Enums for Type Safety
Use Python `Enum` classes for any value that has a fixed set of options (e.g., section types, channel actions). This provides type safety and prevents invalid string values. Follow patterns in `src/config/enums.py`.

### Sample-Based Precision
Audio timing calculations should use **sample positions** (integers) rather than seconds (floats) for maximum precision. Convert to seconds only for display/output purposes.

---

## Status Key

Each story includes a **Status** section with one of the following values:

- **Done**: Story is fully implemented and tested
- **Ready to start**: Story prerequisites are complete and can be started immediately
- **Waiting on dependencies**: Story cannot be started due to incomplete prerequisites

---

## Story 1: Define Click Analyzer Protocol and Data Models

**Description:**  
Create the foundational abstractions and data models for click track analysis before implementing the concrete analyzer. This follows the Dependency Inversion Principle by defining the interface first.

**Detailed Requirements:**  
- Create a new file `src/audio/click/protocols.py` with a `ClickAnalyzerProtocol` defining the interface for click analysis.
- The protocol must be decorated with `@runtime_checkable` for runtime type checking.
- The protocol should define methods for:
  - `analyze(audio_path: Path, sample_rate: int) -> SectionBoundaries` - Main analysis method.
  - `detect_onsets(audio_path: Path, sample_rate: int) -> list[int]` - Return onset positions in **samples** (not seconds) for maximum precision.
  - `estimate_bpm(onset_samples: list[int], sample_rate: int, window_start_sample: int, window_end_sample: int) -> float | None` - Estimate BPM for a sample range.
- Create a `SectionType` enum in `src/audio/click/enums.py` with values:
  - `SONG = "song"`
  - `SPEAKING = "speaking"`
- Create a `SectionInfo` **Pydantic model** in `src/audio/click/models.py` with fields:
  - `section_number: int`
  - `start_sample: int`
  - `end_sample: int`
  - `start_seconds: float` (computed from samples and sample rate)
  - `duration_seconds: float` (computed from samples and sample rate)
  - `section_type: SectionType` (use the enum, not a string literal)
  - `bpm: int | None`
- Create a `SectionBoundaries` **Pydantic model** as a container for a list of `SectionInfo` with helper methods.
- All data models must use Pydantic (not dataclasses) for consistency with the existing codebase and built-in validation/serialization.
- Create package `src/audio/click/__init__.py` exporting public interfaces.

**Acceptance Criteria:**  
- Protocol is `@runtime_checkable` and properly documented.
- All data models are Pydantic models with proper type hints and validation.
- `SectionType` enum is used instead of string literals for type safety.
- Models can serialize to/from JSON for the session output feature using Pydantic's built-in methods.

**Definition of Done:**  
- All protocols and models created with complete docstrings.
- Unit tests for model validation and serialization.
- No circular import issues with existing modules.
- Type hints pass mypy checks.
- All models follow Pydantic v2 API patterns.

**Status:** Done

---

## Story 2: Extend Configuration Models for Click Channel and Section Splitting

**Description:**  
Update the Pydantic configuration models in `src/config/` to support the new "click" channel type and add a new `section_splitting` configuration section. This includes defining the data structures for channel types, validation rules, and default values for section splitting parameters.

**Detailed Requirements:**  
- Add `CLICK` to the `ChannelAction` enum in `src/config/enums.py` (alongside PROCESS, BUS, SKIP).
- Update `ChannelConfig` model to allow `action: ChannelAction.CLICK`.
- Create a new `SectionSplittingConfig` Pydantic model in `src/config/models.py` with fields:
  - `enabled: bool` (default: False)
  - `gap_threshold_seconds: float` (default: 3.0, must be positive)
  - `min_section_length_seconds: float` (default: 15.0, must be positive)
  - `bpm_change_threshold: int` (default: 1, must be >= 1)
- Add `section_splitting: SectionSplittingConfig | None` field to the main config structure (or create one if none exists).
- Add a model validator to ensure only one channel has `action: CLICK` when section splitting is enabled.
- Update `ConfigLoader` and `ConfigSource` protocol to handle the new section.
- Ensure backward compatibility: configs without `section_splitting` load with defaults.

**Acceptance Criteria:**  
- Config files without the new fields load successfully with defaults applied.
- Config files with invalid values (e.g., negative thresholds) raise appropriate `ConfigValidationError`.
- Multiple "click" channels in config raise a validation error.
- Zero click channels when `section_splitting.enabled=true` raises a validation error.

**Definition of Done:**  
- All Pydantic models updated with Pydantic v2 API (`@field_validator`, `@model_validator`).
- Unit tests added for new validation logic including edge cases.
- Existing config loading tests pass.
- Updated YAML schema examples in documentation.  

**Status:** Done

---

## Story 3: Update CLI Interface for Section Splitting Options

**Description:**  
Extend the Typer-based CLI in `src/cli/commands.py` to add the new `--section-by-click` flag, `--gap-threshold` option, and `--session-json` option to the `process` command. Integrate these options with the configuration system to override defaults when provided.

**Detailed Requirements:**  
- Add `--section-by-click` as a boolean flag to the process command (default: False).
- Add `--gap-threshold` as an optional float option (when provided, overrides config value).
- Add `--session-json` as an optional Path option (enables JSON output; if path not specified, uses default location).
- Create a `ProcessingOptions` dataclass or Pydantic model to encapsulate all CLI options for cleaner parameter passing.
- Update the command handler to merge CLI options with config values (CLI takes precedence).
- Add comprehensive help text for each new option following existing patterns.
- Validate `--gap-threshold` is positive at CLI level using Typer callbacks.
- Maintain existing CLI behavior when new flags are not used.

**Acceptance Criteria:**  
- Running `uv run python -m src.main process --help` shows the new options with descriptions.
- CLI options correctly override config defaults.
- Invalid values for `--gap-threshold` (e.g., negative) are rejected with helpful error messages.
- `--session-json` without a path argument uses the default location.

**Definition of Done:**  
- CLI tests updated and passing.
- Integration tests verify option precedence (CLI > config > defaults).
- Rich console output remains consistent.
- Code follows CLI design patterns established in `src/cli/commands.py`.

**Status:** Done

---

## Story 4: Implement Custom Click Track Analyzer with NumPy/SciPy

**Description:**  
Create a concrete implementation of the `ClickAnalyzerProtocol` using NumPy, SciPy, and soundfile for streaming audio analysis. This module handles onset detection, BPM estimation, and section boundary identification using signal processing techniques.

**Detailed Requirements:**  
- Create `src/audio/click/scipy_analyzer.py` with a `ScipyClickAnalyzer` class implementing `ClickAnalyzerProtocol`.

**Audio I/O Component:**
- Use `soundfile.blocks()` for streaming audio input with configurable `blocksize` (default: 32768 samples, approximately 0.74 seconds at 44.1kHz) and optional `overlap` for continuous processing.
- Extract click track channel from multi-channel files using array slicing on the returned NumPy arrays.
- Track absolute sample position across blocks to maintain sample-accurate onset positions.

**Onset Detection Component:**
Implement an energy-based onset detection function using the following signal processing pipeline:
1. **Bandpass Filtering**: Design a Butterworth bandpass filter using `scipy.signal.butter()` with `output='sos'` for numerical stability. Configure cutoff frequencies appropriate for metronome clicks (typically 1kHz-8kHz). Apply filter using `scipy.signal.sosfilt()`.
2. **Envelope Extraction**: Compute the amplitude envelope by taking the absolute value of the filtered signal, then apply a smoothing filter (low-pass or moving average using `scipy.ndimage.uniform_filter1d()` or `numpy.convolve()`).
3. **Novelty Function**: Compute the first derivative (difference) of the envelope using `numpy.diff()`. Half-wave rectify (set negative values to zero) to capture only energy increases.
4. **Peak Detection**: Apply `scipy.signal.find_peaks()` to the novelty function with the following configurable parameters:
   - `height`: Minimum peak height threshold (adaptive based on signal statistics, e.g., `mean + 2*std`).
   - `distance`: Minimum samples between peaks (prevents double-detection; set based on expected minimum BPM, e.g., 300 BPM = 200ms = ~8820 samples at 44.1kHz).
   - `prominence`: Minimum peak prominence to distinguish true onsets from noise.
5. **Sample Position Calculation**: Convert peak indices to absolute sample positions relative to the start of the audio file, accounting for block offsets and any filter group delay.

**BPM Estimation Component:**
- Calculate inter-onset intervals (IOI) in samples between consecutive detected onsets.
- Convert IOI to BPM using the formula: `BPM = (sample_rate * 60) / IOI_samples`.
- Use median IOI within a sliding window (e.g., 8-16 consecutive intervals) for robust tempo estimation that handles occasional missed or spurious detections.
- Return `None` for regions with insufficient onsets (fewer than 4 within the analysis window).

**Section Boundary Detection:**
1. Identify gaps exceeding `gap_threshold_seconds` (converted to samples) as section boundaries by analyzing IOI values.
2. Identify significant BPM changes exceeding `bpm_change_threshold` between consecutive analysis windows as section boundaries.
3. Build section boundary list with start/end samples and computed BPM values for each section.

**Edge Case Handling:**
- No onsets detected: Return single section spanning entire audio with `bpm=None`.
- Single onset: Return single section spanning entire audio with `bpm=None`.
- Very short audio (< 1 second): Process without streaming, handle as single block.
- Silent or near-silent audio: Use adaptive thresholding that detects when no valid peaks exist.

**Configuration Parameters (stored as class attributes or passed to constructor):**
- `blocksize: int` - Audio block size in samples (default: 32768).
- `bandpass_low: float` - Low cutoff frequency in Hz (default: 1000.0).
- `bandpass_high: float` - High cutoff frequency in Hz (default: 8000.0).
- `filter_order: int` - Butterworth filter order (default: 4).
- `min_onset_distance_ms: float` - Minimum milliseconds between onsets (default: 150.0, corresponding to ~400 BPM max).
- `peak_prominence_factor: float` - Factor multiplied by signal std for prominence threshold (default: 1.5).

**Acceptance Criteria:**  
- Implementation passes `isinstance(analyzer, ClickAnalyzerProtocol)` check.
- Detection accurately identifies onsets in clean click tracks (>95% accuracy on test files with known onset positions).
- BPM estimation is within ±2 BPM for steady tempos on test files with known BPM values.
- Memory usage remains constant regardless of audio file length (streaming verification via memory profiling).
- Section boundaries align with expected song/speaking transitions in test files with annotated boundaries.
- All onset positions are returned as integer sample counts, not floating-point seconds.

**Definition of Done:**  
- Unit tests with synthesized click track audio data (sine wave bursts at known intervals and BPMs).
- Unit tests for each sub-component: filtering, envelope extraction, peak detection, BPM calculation.
- Integration tests with real WAV sample files (add to `tests/fixtures/`).
- Performance test verifying constant memory for 1-hour+ simulated streams using `tracemalloc` or similar.
- Code includes comprehensive docstrings and type hints.
- All NumPy/SciPy-specific code is isolated behind the protocol interface, enabling future alternative implementations.

---

## Story 5: Implement Section Boundary Processing and Merging

**Description:**  
Create a section processor that takes raw section boundaries from the analyzer, merges short sections, and produces the final section list. This separates the merging logic from detection for testability and single responsibility.

**Detailed Requirements:**  
- Create `src/audio/click/section_processor.py` with a `SectionProcessor` class.
- Implement `merge_short_sections(sections: list[SectionInfo], min_length_seconds: float) -> list[SectionInfo]`:
  - Iterate through sections and merge any section shorter than `min_length_seconds` into the previous section.
  - If the first section is short, merge into the next section instead.
  - Preserve BPM of the longer/primary section when merging.
  - Never drop sections entirely - always merge.
- Implement `calculate_section_metadata(sections: list[SectionInfo], sample_rate: int) -> list[SectionInfo]`:
  - Compute HMS-formatted start times and durations.
  - Assign section numbers (1-indexed, zero-padded for display).
- Implement `classify_sections(sections: list[SectionInfo]) -> list[SectionInfo]`:
  - Mark sections as "song" if they have a valid BPM.
  - Mark sections as "speaking" if BPM is None (no clicks detected in that region).
- Ensure sample-accurate boundaries: all calculations use integer sample positions.

**Acceptance Criteria:**  
- Short sections are correctly merged without dropping content.
- Section numbering is sequential and correct after merging.
- Edge case: single section results in one-element list.
- Edge case: all short sections merge into one section.

**Definition of Done:**  
- Comprehensive unit tests for all merging scenarios.
- Property-based tests using Hypothesis for edge cases.
- Code follows single responsibility - only handles section processing, not audio I/O.

**Status:** Done

---

## Story 6: Integrate Section Splitting into Processing Pipeline

**Description:**  
Modify the main processing pipeline in `src/processing/` to optionally split audio tracks into sections based on click track analysis. Coordinate splitting across all channels at identical sample-accurate boundaries.

**Detailed Requirements:**  
- Update `TrackBuilder` (or create a new `SectionSplitter` class) to accept section boundaries.
- Implement a new processing mode that:
  1. First processes the click track to generate section boundaries.
  2. Then splits all tracks (including non-click) at those boundaries.
- Ensure the click track is processed/extracted before other tracks when section splitting is enabled.
- Use temporary storage for the click track if needed for analysis before final output.
- Generate section metadata to pass to output handlers.
- Preserve existing processing behavior when section splitting is disabled.
- Handle multi-file sessions: section boundaries apply to the concatenated output.

**Acceptance Criteria:**  
- All tracks in a section have identical durations and start/end times.
- Processing handles edge cases like single sections or no detections gracefully.
- Existing processing tests pass when feature is disabled.
- Section boundaries are sample-accurate across all tracks.

**Definition of Done:**  
- Integration tests with multi-track audio files.
- Tests verify section content matches expected audio segments.
- Memory-efficient implementation using streaming or temporary files.
- Code review confirms no breaking changes to existing functionality.

**Status:** Done

---

## Story 7: Update Output Directory Structure for Sections

**Status:** Done

**Description:**  
Modify the output logic in `src/output/` to create numbered section directories instead of placing tracks directly in the output directory when section splitting is enabled.

**Detailed Requirements:**  
- Create a new `SectionOutputWriter` class in `src/output/section_writer.py`.
- Implement directory creation: `section_01/`, `section_02/`, etc. (zero-padded to 2 digits; extend to 3 digits if >99 sections).
- Place individual track files inside each section directory with the same filenames as current output.
- Integrate with existing output path logic (sibling `processed/` or CLI-specified).
- When section splitting is enabled, output directory contains ONLY section subdirectories (no top-level track files).
- Handle single section case: still create `section_01/` directory.
- Implement cleanup: remove empty section directories if write fails.

**Acceptance Criteria:**  
- Output structure matches the PRD examples exactly.
- File formats and naming remain unchanged within sections.
- Directory creation handles filesystem errors gracefully (permissions, disk space).
- Existing output behavior unchanged when feature is disabled.

**Definition of Done:**  
- Unit tests for directory structure creation and naming.
- Integration tests verify correct file placement.
- Error handling tests for filesystem edge cases.
- Code follows existing patterns in `src/output/`.

---

## Story 8: Embed BPM Metadata in WAV Files

**Status:** Completed

**Description:**  
Add functionality to embed detected BPM values into the WAV files of each section using industry-standard ID3 metadata tags for DAW compatibility.

**Architecture Note:**  
Follow the interface-first pattern: define a `MetadataWriterProtocol` before implementing concrete writers. This allows swapping implementations without changing consuming code.

**Implementation Notes:**
- Used mutagen library for ID3 TBPM tag support in WAV files
- ID3 tags can be embedded in WAV files for metadata storage
- Maintains clean architecture with protocol-based design and dependency injection

**Detailed Requirements:**  
- Create `src/output/protocols.py` with a `MetadataWriterProtocol` defining:
  - `write_bpm(file_path: Path, bpm: int | None) -> bool` - Embed BPM metadata, return success status.
  - `read_bpm(file_path: Path) -> int | None` - Read BPM metadata for verification.
  - Protocol must be `@runtime_checkable`.
- Create `src/output/metadata.py` with a `MutagenMetadataWriter` class implementing `MetadataWriterProtocol`.
- Use the [mutagen](https://github.com/quodlibet/mutagen) library for ID3 tag manipulation.
- Embed BPM using the standard ID3 `TBPM` frame for BPM values.
- Set integer BPM values for song sections.
- For speaking sections: omit BPM metadata or set to empty/zero.
- Apply to all track files in each section (not just click track).
- Implement as a post-processing step after WAV file creation.
- Handle cases where metadata embedding fails gracefully (log warning, continue processing).
- Ensure embedding doesn't alter audio data or file integrity.
- Use dependency injection to allow selecting the writer implementation.

**Acceptance Criteria:**  
- `MetadataWriterProtocol` is defined and implementation conforms to it.
- BPM values are embedded and readable by common audio tools (test with ffprobe, mediainfo).
- Speaking sections have no BPM metadata or BPM=0.
- File sizes increase only minimally after embedding.
- Audio playback is unaffected by metadata embedding.

**Definition of Done:**  
- Protocol defined with complete docstrings.
- Concrete implementation passing all tests.
- Unit tests verify metadata embedding and reading.
- Integration tests check file integrity and audio data preservation.
- Fallback handling for files where embedding fails (warning logged, processing continues).
- Documentation in README on the metadata format used and DAW compatibility.

---

## Story 9: Implement Console Summary Output

**Status:** Ready to start

**Description:**  
Add console output functionality to display a Rich-formatted table summarizing detected sections with start times, durations, types, and BPMs.

**Detailed Requirements:**  
- Extend `ConsoleOutputHandler` in `src/output/console.py` with a `print_section_summary(sections: list[SectionInfo])` method.
- Use Rich `Table` for formatted output with columns: Section, Start Time, Duration, Type, BPM.
- Format times as HH:MM:SS (use `datetime.timedelta` or custom formatter).
- Display BPM as integer string or "none" for speaking sections.
- Apply consistent styling matching existing Rich usage in the project.
- Output the table automatically after processing completes when section splitting is enabled.
- Handle edge case: no sections (should not occur, but display appropriate message).

**Acceptance Criteria:**  
- Table output matches the PRD example format exactly.
- Times and durations are accurately calculated and displayed.
- Table renders correctly in various terminal widths (handles wrapping gracefully).
- Output appears only when section splitting is enabled and sections exist.

**Definition of Done:**  
- Unit tests for time formatting and table generation.
- Manual testing of console output in different terminal sizes.
- Integration with existing Rich console patterns in the project.
- Snapshot tests or golden file tests for table output format.

---

## Story 10: Implement Optional JSON Session Output

**Status:** Ready to start

**Description:**  
Add functionality to write a JSON file containing detailed session metadata when the `--session-json` flag is provided.

**Detailed Requirements:**  
- Create `src/output/session_json.py` with a `SessionJsonWriter` class.
- Integrate with the `--session-json` CLI option (defined in Story 3).
- Default path: `session.json` in the parent directory of input files if flag is used without explicit path.
- Generate JSON array of objects with the following schema:
  ```json
  [
    {
      "section": "section_01",
      "start_seconds": 0.0,
      "start_hms": "00:00:00",
      "duration_seconds": 165.5,
      "duration_hms": "00:02:45",
      "type": "song",
      "bpm": 120
    }
  ]
  ```
- Use `json.dumps()` with `indent=2` for human-readable output.
- Use precise floating-point seconds (at least 3 decimal places).
- Handle write errors gracefully with informative error messages.
- Ensure atomic writes (write to temp file, then rename) to prevent corruption.

**Acceptance Criteria:**  
- JSON structure matches PRD specification exactly.
- File is created in correct location with proper permissions.
- Invalid paths are handled gracefully with clear error messages.
- Partial writes don't leave corrupted files.

**Definition of Done:**  
- Unit tests for JSON generation logic.
- Integration tests verify file creation, content, and location.
- Error handling tests for write failures (disk full, permissions, invalid paths).
- JSON schema validation in tests.

---

## Story 11: Add Comprehensive Error Handling and Fallbacks

**Status:** Ready to start

**Description:**  
Implement robust error handling for detection failures, invalid configurations, and edge cases, with appropriate fallbacks to maintain app stability.

**Detailed Requirements:**  
- Create custom exceptions in `src/exceptions/` for click-specific errors:
  - `ClickChannelNotFoundError`
  - `ClickDetectionError`
  - `SectionProcessingError`
- Implement fallback behaviors per PRD:
  - No click channel defined when `--section-by-click` is used: Log warning, fall back to normal long-track output.
  - Detection failure (no onsets, noisy/quiet click): Log warning, fall back to single `section_01` containing all content.
  - Very short recordings: Apply min length merging; if entire recording is one section, output as `section_01`.
- Add validation at processing start to catch configuration issues early.
- Provide clear, actionable error messages including suggestions for resolution.
- Ensure partial failures during processing don't corrupt output:
  - Use atomic file operations where possible.
  - Clean up incomplete section directories on failure.
- Use Python `logging` module at appropriate levels (DEBUG for details, WARNING for fallbacks, ERROR for failures).
- User-facing messages via Rich console maintain consistent styling.

**Acceptance Criteria:**  
- App gracefully handles all edge cases mentioned in PRD.
- Fallback behaviors match PRD requirements exactly.
- Error messages are helpful and guide users to solutions.
- Processing failures don't leave partial/corrupted output.

**Definition of Done:**  
- Unit tests for each error condition and fallback scenario.
- Integration tests with edge-case inputs (empty files, noise-only click tracks).
- Logging output reviewed for appropriate verbosity levels.
- User-facing error messages tested for clarity.

---

## Story 12: Add Signal Processing Dependencies and Update Project Configuration

**Status:** Completed

**Description:**  
Add the required signal processing libraries (NumPy, SciPy, soundfile) as project dependencies and update pyproject.toml. Also add mutagen for ID3 metadata writing.

**Detailed Requirements:**  
- Verify `numpy` is already a project dependency; if not, use `uv add numpy` to add it.
- Use `uv add scipy` to add the SciPy library for signal processing algorithms (`find_peaks`, filtering, FFT).
- Verify `soundfile` is already a project dependency (likely present for audio I/O); if not, use `uv add soundfile` to add it.
- Use `uv add mutagen` to add the mutagen library for ID3 metadata writing.
- Add dependencies using the `uv add <package>` command to ensure proper formatting and version resolution.
- Run `uv sync` to verify the lock file is updated correctly.
- Verify all dependencies install correctly on Windows, macOS, and Linux via CI.
- Note: SciPy and NumPy are pure Python wheels with binary extensions and should install without system dependencies on all major platforms.
- Test that existing functionality is not affected by new dependencies.

**Acceptance Criteria:**  
- `uv sync` installs all dependencies without errors.
- CI pipeline passes on all supported platforms (Windows, macOS, Linux).
- No version conflicts with existing dependencies.
- pyproject.toml shows properly formatted dependency entries added by uv.
- SciPy signal processing functions are importable: `from scipy.signal import find_peaks, butter, sosfilt`.
- soundfile streaming functions are importable: `from soundfile import blocks`.

**Definition of Done:**  
- Dependencies added via `uv add` commands.
- pyproject.toml and uv.lock updated correctly.
- CI workflow tested and passing on all platforms.
- Quick verification script confirms imports work correctly.

---

## Story 13: Update Documentation and Final Testing

**Status:** Waiting on dependencies

**Description:**  
Update README, add comprehensive tests, and ensure all quality checks pass for the new feature.

**Detailed Requirements:**  
- Update README.md with:
  - New CLI options (`--section-by-click`, `--gap-threshold`, `--session-json`).
  - Configuration file examples for `section_splitting` section.
  - Example output structure when section splitting is enabled.
  - BPM metadata format and DAW compatibility notes.
- Add/update YAML configuration example file.
- Add unit tests for all new classes and functions (target: >90% coverage for new code).
- Add integration tests covering:
  - Full processing workflow with section splitting enabled.
  - Fallback scenarios.
  - Multi-file session handling.
- Ensure mypy type checking passes with no errors.
- Run ruff linting and fix any issues.
- Update TESTING_PLAN.md with new test scenarios.

**Acceptance Criteria:**  
- All tests pass (`uv run pytest`, `uv run mypy src/ tests/`, `uv run ruff check src/ tests/`).
- README accurately and completely describes the new feature.
- Coverage meets project standards (check existing coverage baseline).
- No regressions in existing functionality.

**Definition of Done:**  
- CI pipeline passes with all new code.
- Documentation reviewed for accuracy and completeness.
- Feature can be used end-to-end following README instructions.
- Code review feedback addressed.
- Feature ready for production use.

---

## TODO

### Architecture Review and SOLID Principles Evaluation
- **Description**: Conduct a comprehensive review of the current architecture to ensure adherence to SOLID principles and best practices. Focus on identifying any violations of the Open-Closed Principle, Single Responsibility Principle, and other design patterns that may have emerged during implementation.
- **Key Areas to Review**:
  - **Open-Closed Principle**: Ensure classes are open for extension but closed for modification. Evaluate recent refactoring of track writers to use inheritance instead of modifying existing classes.
  - **Single Responsibility Principle**: Verify each class has a single, well-defined responsibility. Check for classes that may be doing too much (e.g., combining data processing with output formatting).
  - **Dependency Inversion**: Ensure high-level modules don't depend on low-level modules but both depend on abstractions (protocols).
  - **Interface Segregation**: Review protocols to ensure they are focused and not forcing implementations to depend on methods they don't use.
  - **Liskov Substitution**: Verify that derived classes can be substituted for their base classes without breaking functionality.
- **Actions Required**:
  - Document current architecture patterns and identify any anti-patterns
  - Create a refactoring plan for any identified issues
  - Implement fixes following SOLID principles
  - Add architectural decision records for future reference
  - Update code comments to reflect design intentions
- **Success Criteria**:
  - Architecture follows SOLID principles consistently
  - Code is maintainable and extensible
  - Classes have clear, single responsibilities
  - Dependencies are properly abstracted
  - Future feature additions won't require modifying existing stable classes

---

## Appendix A: Dependency Summary

| Dependency | Purpose | Installation Command |
|------------|---------|---------------------|
| numpy | Array operations, FFT, numerical computations for signal processing | `uv add numpy` (likely already present) |
| scipy | Signal processing: `find_peaks`, `butter`, `sosfilt`, filtering, spectral analysis | `uv add scipy` |
| soundfile | Streaming audio I/O via `blocks()`, WAV reading/writing with libsndfile | `uv add soundfile` (likely already present) |
| audiometa | WAV metadata (RIFF INFO chunk) reading/writing | `uv add audiometa` |

## Appendix B: File Structure for New Code

```
src/
├── audio/
│   └── click/
│       ├── __init__.py
│       ├── protocols.py          # ClickAnalyzerProtocol
│       ├── enums.py              # SectionType enum
│       ├── models.py             # SectionInfo, SectionBoundaries (Pydantic models)
│       ├── scipy_analyzer.py     # NumPy/SciPy implementation of ClickAnalyzerProtocol
│       └── section_processor.py  # Merging and processing logic
├── config/
│   ├── models.py                 # Add SectionSplittingConfig
│   └── enums.py                  # Add CLICK to ChannelAction
├── output/
│   ├── protocols.py              # MetadataWriterProtocol
│   ├── section_writer.py         # Section directory output
│   ├── metadata.py               # AudiometaWriter, FfmpegMetadataWriter implementations
│   └── session_json.py           # JSON session output
└── exceptions/
    └── (add click-specific exceptions)
```

## Appendix C: Testing Strategy

1. **Unit Tests**: All new classes with mocked dependencies.
2. **Integration Tests**: End-to-end processing with fixture audio files.
3. **Property-Based Tests**: Hypothesis for section merging edge cases.
4. **Performance Tests**: Memory profiling for streaming verification.
5. **Golden File Tests**: Console output and JSON schema validation.