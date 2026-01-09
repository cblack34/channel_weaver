# Architecture Remediation User Stories

## Executive Summary

The Channel Weaver codebase demonstrates **solid foundational architecture** with good separation of concerns, comprehensive use of protocols/interfaces for dependency inversion, and a well-structured module hierarchy. The codebase passes all 362 tests, mypy type-checking, and ruff linting. Key strengths include proper use of Pydantic v2 for configuration validation, protocol-based abstractions for extensibility (e.g., `ConfigSource`, `ClickAnalyzerProtocol`, `BitDepthConverter`), and consistent exception handling through a custom exception hierarchy.

**Top Risks/Opportunities:**
- **High-complexity command module**: The `commands.py` file (441 lines) violates Single Responsibility Principle by mixing CLI parsing, orchestration logic, and validation
- **Duplicated time formatting logic**: `_format_time()` method duplicated across 3+ modules
- **Missing abstraction for audio pipeline**: No unified pipeline orchestrator; orchestration logic embedded in CLI command
- **Incomplete error recovery**: Some exception handlers log and continue without proper graceful degradation patterns
- **Missing logging configuration abstraction**: Logging setup hardcoded in commands module
- **Section splitter god class**: `SectionSplitter` class (570 lines) handles multiple responsibilities

**Estimated Scope:** 7-11 medium-complexity stories, approximately 2-3 sprints for a single developer.

---

## Story 01 - Extract Processing Pipeline Orchestrator from CLI Commands

**Status:** Ready to start

**Depends on:** None

**Short Description:** Create a dedicated `ProcessingPipeline` orchestrator class to coordinate the complete audio processing workflow, removing orchestration logic from the CLI `process` command.

**Detailed Requirements:**
- Create `src/pipeline/orchestrator.py` with a `ProcessingPipeline` class
- Extract workflow steps from `commands.py`:process() into discrete, testable methods:
  - `discover_and_validate_audio()`
  - `load_configuration()`
  - `extract_segments()`
  - `build_tracks()`
  - `split_sections_if_enabled()`
  - `write_metadata()`
  - `cleanup()`
- Accept all dependencies via constructor injection (extractor, config_loader, builder, etc.)
- Implement proper resource management with context manager pattern (`__enter__`/`__exit__`)
- Reduce `process()` function in commands.py to CLI parsing + delegation to orchestrator
- Return a structured `ProcessingResult` dataclass with summary information

**Acceptance Criteria:**
- [ ] `ProcessingPipeline` class exists with clear, single-purpose methods
- [ ] `commands.py:process()` reduced to <50 lines of CLI-focused code
- [ ] All 362 existing tests continue to pass
- [ ] New unit tests for orchestrator achieve 90%+ coverage
- [ ] Type hints complete for all public methods

**Definition of Done:**
- [ ] All tests pass (pytest)
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Code review completed
- [ ] Documentation updated (docstrings)

---

## Story 02 - Extract Utility Functions to Shared Module

**Status:** Ready to start

**Depends on:** None

**Short Description:** Consolidate duplicated utility functions (time formatting, path sanitization) into a shared `src/utils/` package.

**Detailed Requirements:**
- Create `src/utils/__init__.py` package
- Create `src/utils/formatting.py` with:
  - `format_time_hms(seconds: float) -> str` - consolidate from `console.py`, `session_json.py`
  - `format_duration(seconds: float, include_ms: bool = False) -> str`
- Create `src/utils/paths.py` with path utilities (consolidate from `cli/utils.py` if applicable)
- Update all existing usages to import from shared module:
  - `src/output/console.py::_format_time()`
  - `src/output/session_json.py::_format_time()`
- Add comprehensive unit tests for formatting edge cases (negative values, very large values, zero)

**Acceptance Criteria:**
- [ ] Single source of truth for time formatting
- [ ] No duplicate `_format_time()` implementations remain
- [ ] Existing tests continue to pass
- [ ] New tests cover formatting edge cases

**Definition of Done:**
- [ ] All tests pass (pytest)
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Code review completed

---

## Story 03 - Refactor SectionSplitter to Reduce Complexity

**Status:** Ready to start

**Depends on:** None

**Short Description:** Split the 570-line `SectionSplitter` class into focused, single-responsibility components following the SRP principle.

**Detailed Requirements:**
- Extract analysis responsibilities to `ClickTrackAnalysisService`:
  - `analyze_final_click_track()`
  - `_find_click_track_file()`
  - `_analyze_final_track()`
  - `_check_click_track_signal()`
- Extract splitting responsibilities to `TrackSplittingService`:
  - `split_output_tracks_if_enabled()`
  - `_split_single_track()`
  - `_cleanup_partial_sections()`
- Extract metadata responsibilities to `SectionMetadataService`:
  - `apply_metadata()`
  - `_get_bpm_for_file()`
- Keep `SectionSplitter` as a facade that coordinates these services
- Use dependency injection to compose services in `SectionSplitter`
- Each service should be independently testable

**Acceptance Criteria:**
- [ ] `SectionSplitter` class reduced to <150 lines (facade pattern)
- [ ] Each extracted service has single responsibility
- [ ] All services accept dependencies via constructor
- [ ] Existing integration tests continue to pass
- [ ] New unit tests for each extracted service

**Definition of Done:**
- [ ] All tests pass (pytest)
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Code review completed

---

## Story 04 - Implement Logging Configuration Abstraction

**Status:** Ready to start

**Depends on:** None

**Short Description:** Create a centralized logging configuration module to replace hardcoded `logging.basicConfig()` calls in command modules.

**Detailed Requirements:**
- Create `src/logging_config.py` with:
  - `configure_logging(verbose: bool = False, log_file: Path | None = None) -> None`
  - Support for different log levels based on environment
  - Optional file logging with rotation
- Remove `logging.basicConfig()` call from `commands.py`
- Add logging configuration to CLI app initialization in `app.py`
- Use `logging.getLogger(__name__)` pattern consistently across all modules
- Consider structured logging format for production use

**Acceptance Criteria:**
- [ ] Single entry point for logging configuration
- [ ] No `logging.basicConfig()` calls in command modules
- [ ] Verbose flag properly controls log level application-wide
- [ ] All existing logging statements continue to work
- [ ] Optional file logging support implemented

**Definition of Done:**
- [ ] All tests pass (pytest)
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Code review completed

---

## Story 06 - Add ConfigLoader Integration Tests for YAML Sources

**Status:** Ready to start

**Depends on:** None

**Short Description:** Expand integration test coverage for the complete configuration loading flow from YAML files through to validated models.

**Detailed Requirements:**
- Create `tests/integration/test_config_loading.py`
- Test cases for:
  - Complete YAML to validated config flow
  - Schema version validation and upgrade paths
  - Channel auto-completion with detected channel count
  - Bus channel conflict detection
  - Section splitting configuration merging with CLI options
- Use real YAML files from `tests/fixtures/`
- Test edge cases: empty config, minimal config, full config
- Verify error messages are user-friendly for validation failures

**Acceptance Criteria:**
- [ ] 10+ integration test cases covering YAML config loading
- [ ] Tests cover happy path and error cases
- [ ] Tests use realistic configuration files
- [ ] Error message quality verified in tests

**Definition of Done:**
- [ ] All tests pass (pytest)
- [ ] Test coverage report shows increased config module coverage
- [ ] Code review completed

---

## Story 07 - Standardize Protocol Implementation Verification

**Status:** Ready to start

**Depends on:** None

**Short Description:** Add runtime protocol verification and improve protocol documentation to ensure implementations match contracts.

**Detailed Requirements:**
- Add `@runtime_checkable` decorator to all protocols where not already present:
  - `BitDepthConverter` in `processing/converters/protocols.py` ✓
  - `ClickAnalyzerProtocol` in `audio/click/protocols.py` - needs verification
- Create `src/protocols/__init__.py` to centralize all protocol exports
- Add unit tests verifying each concrete implementation satisfies its protocol:
  - `Float32Converter`, `Int24Converter`, `Int16Converter` implement `BitDepthConverter`
  - `ScipyClickAnalyzer` implements `ClickAnalyzerProtocol`
  - `YAMLConfigSource`, `DefaultConfigSource` implement `ConfigSource`
- Document protocol contracts in docstrings with expected behavior

**Acceptance Criteria:**
- [ ] All protocols are `@runtime_checkable` where appropriate
- [ ] Unit tests verify protocol compliance for all implementations
- [ ] Protocol documentation complete with usage examples
- [ ] Import paths consolidated in protocols package

**Definition of Done:**
- [ ] All tests pass (pytest)
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Code review completed

---

## Story 08 - Improve Error Recovery and Graceful Degradation

**Status:** Ready to start

**Depends on:** None

**Short Description:** Enhance error handling to provide better recovery paths and ensure partial results are preserved when possible.

**Detailed Requirements:**
- Review all exception handlers in `commands.py` and `section_splitter.py`
- Implement graceful degradation pattern:
  - If section splitting fails, continue with unsplit output (currently partially implemented)
  - If metadata writing fails, continue with audio-only output
  - If a single track fails, continue with remaining tracks
- Add `--strict` CLI flag to fail-fast on any error (for CI/automated pipelines)
- Ensure cleanup always runs even after partial failures (use try/finally properly)
- Add summary of warnings/errors at end of processing
- Log partial success information for debugging

**Acceptance Criteria:**
- [ ] Partial failures don't lose successful work
- [ ] `--strict` flag available for fail-fast behavior
- [ ] Cleanup always executes on any exit path
- [ ] End-of-run summary shows any issues encountered
- [ ] User-friendly error messages for all failure modes

**Definition of Done:**
- [ ] All tests pass (pytest)
- [ ] Integration tests verify graceful degradation
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Code review completed

---

## Story 09 - Add Performance Monitoring and Profiling Hooks

**Status:** Waiting on dependencies

**Depends on:** Story 01

**Short Description:** Add optional performance monitoring to track processing time for each pipeline stage, enabling optimization and progress estimation.

**Detailed Requirements:**
- Create `src/monitoring/performance.py` with:
  - `ProcessingMetrics` dataclass to capture timing data
  - `@timed_operation` decorator for measuring method execution time
  - `MetricsCollector` class to aggregate metrics
- Add timing instrumentation to `ProcessingPipeline` orchestrator (from Story 01)
- Track time for: discovery, extraction, building, splitting, metadata
- Add `--metrics` CLI flag to output performance summary
- Consider adding progress estimation based on prior run metrics
- Store metrics in JSON format for analysis

**Acceptance Criteria:**
- [ ] Processing time tracked for each major stage
- [ ] `--metrics` flag outputs timing summary
- [ ] Metrics stored in machine-readable format
- [ ] No significant performance overhead when metrics disabled
- [ ] Progress estimation available for extraction phase

**Definition of Done:**
- [ ] All tests pass (pytest)
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Code review completed
- [ ] Performance overhead measured and documented

---

## Story 10 - Consolidate Audio Processing Abstractions

**Status:** Ready to start

**Depends on:** None

**Short Description:** Refactor audio module to use consistent abstractions for audio I/O operations across the codebase.

**Detailed Requirements:**
- Create `src/audio/io.py` with unified audio read/write abstractions:
  - `AudioReader` class wrapping soundfile with chunked reading
  - `AudioWriter` class with atomic write support
  - `AudioFile` context manager for consistent resource management
- Standardize chunk size usage (currently `AUDIO_CHUNK_SIZE` in constants)
- Extract common patterns from `mono.py`, `stereo.py`, `section_splitter.py`
- Add retry logic for transient I/O errors (currently in `section_splitter._concatenate_segments`)
- Ensure all audio operations use string paths for soundfile (currently mixed)

**Acceptance Criteria:**
- [ ] Unified `AudioReader` and `AudioWriter` abstractions
- [ ] All audio I/O goes through new abstractions
- [ ] Retry logic centralized and consistent
- [ ] Path handling consistent (always convert to string for soundfile)
- [ ] Existing tests pass unchanged

**Definition of Done:**
- [ ] All tests pass (pytest)
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Code review completed

---

## Story 11 - Update Copilot Instructions Based on Architecture Findings

**Status:** Ready to start

**Depends on:** None

**Short Description:** Update the `.github/copilot-instructions.md` file to reflect architectural patterns and best practices discovered during this review.

**Detailed Requirements:**
- Add section on "Pipeline Architecture" describing orchestrator pattern
- Add guidance on "Protocol Usage" for new abstractions
- Update "Code Quality Standards" to include:
  - Maximum class size recommendation (300 lines)
  - Maximum function size recommendation (50 lines)
  - Protocol-first design for new abstractions
- Add section on "Error Handling Patterns":
  - Graceful degradation approach
  - Custom exception usage
  - Cleanup/resource management
- Document "Audio Processing Patterns":
  - Chunk-based reading
  - Path handling for soundfile
  - Atomic file writes
- Add section on "Testing Requirements":
  - Integration test requirements for new features
  - Protocol compliance testing

**Acceptance Criteria:**
- [ ] Copilot instructions updated with all identified patterns
- [ ] New developers can understand architecture from instructions
- [ ] Instructions align with actual codebase practices
- [ ] No contradictions with existing guidance

**Definition of Done:**
- [ ] Instructions reviewed by team
- [ ] No conflicts with existing guidance
- [ ] Documentation clear and actionable

---

## Story 12 - Implement Configuration Schema Migration Support

**Status:** Waiting on dependencies

**Depends on:** Story 06

**Short Description:** Add support for configuration schema versioning and migration to handle future configuration format changes.

**Detailed Requirements:**
- Create `src/config/migration.py` with:
  - `SchemaMigrator` class to handle version upgrades
  - `MigrationStep` protocol for individual migrations
  - Registry of migration functions by version pair
- Current schema version is 1 (in `protocols.py`)
- Implement migration framework that:
  - Detects schema version from YAML
  - Applies sequential migrations if needed
  - Preserves unknown/custom fields during migration
- Add `--migrate-config` CLI command to upgrade config files in place
- Log migration steps for user visibility
- Back up original config before migration

**Acceptance Criteria:**
- [ ] Schema migration framework implemented
- [ ] Migrations are composable and sequential
- [ ] Unknown fields preserved during migration
- [ ] `--migrate-config` command available
- [ ] Original config backed up before changes

**Definition of Done:**
- [ ] All tests pass (pytest)
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Code review completed
- [ ] Migration documentation written

---

## Story 13 - Add Comprehensive CLI Help and Examples

**Status:** Ready to start

**Depends on:** None

**Short Description:** Enhance CLI help text with comprehensive examples and improve discoverability of features.

**Detailed Requirements:**
- Add rich help panels to Typer commands using `rich_help_panel`
- Group related options (output, section splitting, debugging)
- Add usage examples to each command's docstring:
  - Basic processing: `channel-weaver process ./raw`
  - With config: `channel-weaver process ./raw --config channel_weaver.yaml`
  - Section splitting: `channel-weaver process ./raw --section-by-click`
- Create `channel-weaver examples` command to show common workflows
- Update `--help` output to be more scannable
- Consider adding shell completion support

**Acceptance Criteria:**
- [ ] All commands have rich help panels
- [ ] Options grouped logically
- [ ] Examples provided for common use cases
- [ ] `channel-weaver examples` command available
- [ ] Help text reviewed for clarity

**Definition of Done:**
- [ ] All tests pass (pytest)
- [ ] CLI help manually reviewed
- [ ] Code review completed
- [ ] README examples match CLI capabilities

---

## Summary Table

| Story | Title | Status | Priority | Dependencies |
|-------|-------|--------|----------|--------------|
| 01 | Extract Processing Pipeline Orchestrator | Ready | High | None |
| 02 | Extract Utility Functions to Shared Module | Ready | Medium | None |
| 03 | Refactor SectionSplitter to Reduce Complexity | Ready | High | None |
| 04 | Implement Logging Configuration Abstraction | Ready | Medium | None |
| 06 | Add ConfigLoader Integration Tests | Ready | Medium | None |
| 07 | Standardize Protocol Implementation Verification | Ready | Low | None |
| 08 | Improve Error Recovery and Graceful Degradation | Ready | High | None |
| 09 | Add Performance Monitoring Hooks | Waiting | Low | Story 01 |
| 10 | Consolidate Audio Processing Abstractions | Ready | Medium | None |
| 11 | Update Copilot Instructions | Ready | High | None |
| 12 | Implement Configuration Schema Migration | Waiting | Low | Story 06 |
| 13 | Add Comprehensive CLI Help and Examples | Ready | Low | None |

---

*Generated: January 9, 2026*
*Review scope: Channel Weaver v0.1.0*
*Tests: 362 passing | Mypy: 57 files, no issues | Ruff: All checks passed*
