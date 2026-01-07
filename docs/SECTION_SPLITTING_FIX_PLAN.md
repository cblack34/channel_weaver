# Section Splitting Architecture Fix Plan

## Problem Analysis

The current implementation of section splitting has a fundamental architectural flaw:

### Current (Incorrect) Flow
```
1. AudioExtractor splits multichannel → mono segments (ch01_0001.wav, ch01_0002.wav, ...)
2. SectionSplitter.split_segments_if_enabled() REPLACES segments:
   - Concatenates ALL mono segments per channel
   - Splits at section boundaries  
   - Returns NEW segment paths (ch01_section0001.wav, ch01_section0002.wav, ...)
3. TrackBuilder receives section-split segments
4. SectionMonoTrackWriter writes ONE file per section (expects 1 segment = 1 section)
```

### Problem
The `SectionSplitter._split_all_segments()` method **replaces** the original multi-file segments with section-based segments. This creates a fundamental incompatibility:

1. **Segments are no longer sequential files** - they become section files
2. **TrackBuilder expects segments = files to concatenate**, not sections
3. **The normal flow concatenates segments → single track** but section mode needs **segments grouped by section**

The current implementation conflates two different concepts:
- **Segment**: A portion of a source file (multiple segments per channel = one continuous recording)
- **Section**: A logical division of the final output (multiple outputs per channel)

### Why It Works Without Section Splitting
Without `--section-by-click`:
1. AudioExtractor produces: `ch01_0001.wav`, `ch01_0002.wav` (one per source file)
2. TrackBuilder concatenates them → `01 - Channel Name.wav`
3. Result: One continuous file per channel

### Why It Breaks With Section Splitting
With `--section-by-click`:
1. AudioExtractor produces: `ch01_0001.wav`, `ch01_0002.wav`
2. SectionSplitter replaces these with: `ch01_section0001.wav`, `ch01_section0002.wav`
3. TrackBuilder sees these as "files to concatenate" 
4. SectionMonoTrackWriter tries to use index `section_idx` on the segment list
5. But the list is organized differently than expected

## Correct Architecture

Section splitting should be a **post-processing step on the final concatenated tracks**, not a modification to the segment pipeline.

### Corrected Flow
```
1. AudioExtractor splits multichannel → mono segments
2. TrackBuilder concatenates segments → final mono tracks AND bus mixes
3. IF section_by_click enabled:
   a. SectionSplitter analyzes click track (from temp segments)
   b. SectionSplitter splits FINAL TRACKS into section folders
   c. BPM metadata applied to section files
4. Cleanup temp files
```

## Implementation Plan

### Story A: Refactor SectionSplitter to Split Final Tracks (Not Segments)

**Description:**
Change SectionSplitter to work on the **final output files** instead of intermediate segments.

**Changes Required:**

1. **Remove `split_segments_if_enabled()` from the processing pipeline**
   - This method currently runs between extract and build
   - It should be removed from this position

2. **Create new method `split_output_tracks()`**
   - Operates on files in `output_dir` after TrackBuilder completes
   - Reads each final WAV file
   - Splits into section subdirectories
   - Preserves original files or replaces them (configurable)

3. **Keep click analysis on segments (before concatenation)**
   - The click analysis still needs to happen on the click track segments
   - This determines WHERE to split
   - Store section boundaries for use after track building

4. **Update CLI command flow:**
   ```python
   # Current (wrong):
   segments = extractor.extract_segments()
   segments, sections = section_splitter.split_segments_if_enabled(segments, channels)
   builder.build_tracks(channels, buses, segments)
   
   # Corrected:
   segments = extractor.extract_segments()
   sections = section_splitter.analyze_click_track_if_enabled(segments, channels)
   builder.build_tracks(channels, buses, segments)  # Normal concatenation
   section_splitter.split_output_tracks_if_enabled(output_dir, sections)  # Post-process
   ```

**Acceptance Criteria:**
- Normal processing (no section splitting) works exactly as before
- Section splitting creates section folders with correctly split files
- All tracks in a section have identical durations
- Click track is NOT included in final output (only used for analysis)

### Story B: Update TrackBuilder to Use Standard Writers

**Description:**
Remove section-awareness from TrackBuilder. It should always use the standard MonoTrackWriter and StereoTrackWriter.

**Changes Required:**

1. **Remove conditional writer selection in TrackBuilder.__init__()**
   - Always use `MonoTrackWriter` and `StereoTrackWriter`
   - Remove `SectionMonoTrackWriter` and `SectionStereoTrackWriter` (or repurpose)

2. **Remove sections parameter from TrackBuilder**
   - TrackBuilder should not know about sections
   - It only concatenates segments → tracks

3. **Move BPM metadata embedding to SectionSplitter**
   - After splitting output tracks into sections
   - Apply BPM tags to the section files

**Acceptance Criteria:**
- TrackBuilder has no section-related code
- Single responsibility: concatenate segments into tracks

### Story C: Update SectionMonoTrackWriter and SectionStereoTrackWriter

**Description:**
Repurpose these classes to split existing tracks (not write from segments).

**Changes Required:**

1. **Rename to SectionFileSplitter or similar**
   - Make it clear this splits existing files
   - Input: list of WAV files in output_dir
   - Output: section subdirectories with split files

2. **Implement file splitting logic**
   ```python
   def split_file(self, input_path: Path, sections: list[SectionInfo], output_base: Path) -> None:
       """Split a single audio file into sections."""
       audio_data, sr = sf.read(input_path)
       for section in sections:
           section_audio = audio_data[section.start_sample:section.end_sample]
           section_dir = output_base / f"section_{section.section_number:02d}"
           output_path = section_dir / input_path.name
           sf.write(output_path, section_audio, sr)
   ```

**Acceptance Criteria:**
- Works on any WAV file in the output directory
- Creates correct section subdirectories
- Handles both mono and stereo files

### Story D: Handle Click Channel Exclusion

**Description:**
Ensure the click channel is  written to the final output.

**Changes Required:**

**Acceptance Criteria:**
- Click channel always appears in output_dir


### Story E: Update CLI Integration

**Description:**
Update the CLI command flow to use the corrected architecture.

**Changes Required in `src/cli/commands.py`:**

```python
# Extract segments (unchanged)
segments = extractor.extract_segments(target_bit_depth=bit_depth)

# Analyze click track if enabled (NEW - analysis only)
section_splitter = SectionSplitter(...)
sections = section_splitter.analyze_if_enabled(segments, channels)

# Build tracks (MODIFIED - no section awareness)
builder = TrackBuilder(
    sample_rate=extractor.sample_rate,
    bit_depth=bit_depth,
    source_bit_depth=extractor.bit_depth,
    temp_dir=temp_root,
    output_dir=output_dir,
    keep_temp=keep_temp,
    console=console,
    # sections parameter REMOVED
    # metadata_writer REMOVED from here
)
builder.build_tracks(channels, buses, segments)

# Split output tracks into sections if enabled (NEW - post-processing)
if sections:
    section_splitter.split_output_tracks(output_dir, sections)
    
    # Apply BPM metadata to section files
    metadata_writer = MutagenMetadataWriter()
    section_splitter.apply_metadata(output_dir, sections, metadata_writer)
    
    # Print section summary
    output_handler = ConsoleOutputHandler(console)
    output_handler.print_section_summary(sections)
```

**Acceptance Criteria:**
- Clear separation of: extract → build → split
- Section splitting is truly optional and additive
- Normal processing unaffected when disabled

## Summary of Key Changes

| Component | Current Behavior | Corrected Behavior |
|-----------|-----------------|-------------------|
| SectionSplitter | Replaces segments with section files | Analyzes click, then splits output files |
| TrackBuilder | Conditional section-aware writers | Always uses standard writers |
| MonoTrackWriter | Section variant exists | Standard only, no section knowledge |
| Output flow | segments → section-segments → section-output | segments → output → split-output |
| Click channel | Converted to PROCESS | Excluded from output entirely |

## Implementation Order

1. **Story A**: Refactor SectionSplitter (core fix)
2. **Story B**: Simplify TrackBuilder  
3. **Story D**: Handle click channel exclusion
4. **Story E**: Update CLI integration
5. **Story C**: Update section file writers (may be removed if logic moves to SectionSplitter)

## Testing Strategy

1. **Regression tests**: Ensure non-section processing works exactly as before
2. **Section integration tests**: Full pipeline with section splitting enabled
3. **Click exclusion tests**: Verify click channel never in output
4. **Boundary accuracy tests**: Section splits at exact sample positions
