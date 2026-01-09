"""Section boundary processing and merging logic for click-based section splitting."""

from src.audio.click.enums import SectionType
from src.audio.click.models import SectionInfo


class SectionProcessor:
    """Processes and refines section boundaries from click track analysis.

    This class handles post-processing of detected sections including:
    - Merging short sections that fall below minimum length thresholds
    - Calculating metadata like start times and durations
    - Classifying sections as song or speaking based on BPM presence
    """

    @staticmethod
    def merge_short_sections(
        sections: list[SectionInfo], min_length_seconds: float, sample_rate: int
    ) -> list[SectionInfo]:
        """Merge sections shorter than min_length_seconds into adjacent sections.

        Args:
            sections: List of section info objects to process
            min_length_seconds: Minimum allowed section length in seconds
            sample_rate: Sample rate for duration calculations

        Returns:
            List of sections with short sections merged into adjacent ones

        Note:
            Never drops sections entirely - always merges into adjacent sections.
            If the first section is short, merges into the next section.
        """
        if not sections:
            return sections

        if len(sections) == 1:
            return sections

        merged_sections: list[SectionInfo] = []
        i = 0

        while i < len(sections):
            current_section = sections[i]

            # Calculate duration for current section
            current_duration = (current_section.end_sample - current_section.start_sample) / sample_rate

            # Check if current section is too short
            if current_duration < min_length_seconds:
                # Find the best section to merge into
                if i == 0:
                    # First section is short - merge into next section
                    if i + 1 < len(sections):
                        next_section = sections[i + 1]
                        # When merging A into B, keep B's BPM if B is longer, otherwise A's BPM
                        current_duration = (current_section.end_sample - current_section.start_sample) / sample_rate
                        next_duration = (next_section.end_sample - next_section.start_sample) / sample_rate
                        if next_duration > current_duration:
                            bpm_to_keep = next_section.bpm
                        else:
                            bpm_to_keep = current_section.bpm
                        
                        merged_section = SectionInfo(
                            section_number=current_section.section_number,  # Keep first section's number
                            start_sample=current_section.start_sample,
                            end_sample=next_section.end_sample,
                            start_seconds=0.0,  # Will be calculated later
                            duration_seconds=0.0,  # Will be calculated later
                            section_type=next_section.section_type,  # Use next section's type
                            bpm=bpm_to_keep,
                        )
                        merged_sections.append(merged_section)
                        i += 2  # Skip the next section since we merged it
                        continue
                    else:
                        # Last section is short but there's nothing to merge into
                        # Keep it as-is (edge case)
                        merged_sections.append(current_section)
                        i += 1
                        continue
                else:
                    # Not first section - merge into previous section
                    prev_section = merged_sections[-1]
                    # When merging A into B, keep B's BPM if B is longer, otherwise A's BPM
                    current_duration = (current_section.end_sample - current_section.start_sample) / sample_rate
                    prev_duration = (prev_section.end_sample - prev_section.start_sample) / sample_rate
                    if prev_duration > current_duration:
                        bpm_to_keep = prev_section.bpm
                    else:
                        bpm_to_keep = current_section.bpm
                    
                    merged_section = SectionInfo(
                        section_number=prev_section.section_number,
                        start_sample=prev_section.start_sample,
                        end_sample=current_section.end_sample,
                        start_seconds=0.0,  # Will be calculated later
                        duration_seconds=0.0,  # Will be calculated later
                        section_type=prev_section.section_type,  # Keep previous type
                        bpm=bpm_to_keep,
                    )
                    merged_sections[-1] = merged_section  # Replace previous
                    i += 1
                    continue

            # Section is long enough, add it
            merged_sections.append(current_section)
            i += 1

        # Renumber sections after merging
        for idx, section in enumerate(merged_sections, 1):
            section.section_number = idx

        return merged_sections

    @staticmethod
    def calculate_section_metadata(
        sections: list[SectionInfo], sample_rate: int
    ) -> list[SectionInfo]:
        """Calculate and update metadata for sections (start times, durations, etc.).

        Args:
            sections: List of section info objects to update
            sample_rate: Sample rate for time calculations

        Returns:
            List of sections with updated metadata
        """
        updated_sections = []

        for section in sections:
            # Calculate the time-based metadata
            start_seconds = section.start_sample / sample_rate
            duration_seconds = (section.end_sample - section.start_sample) / sample_rate

            # Create a new section with updated computed fields
            updated_section = SectionInfo(
                section_number=section.section_number,
                start_sample=section.start_sample,
                end_sample=section.end_sample,
                start_seconds=start_seconds,
                duration_seconds=duration_seconds,
                section_type=section.section_type,
                bpm=section.bpm,
            )

            updated_sections.append(updated_section)

        return updated_sections

    @staticmethod
    def classify_sections(sections: list[SectionInfo]) -> list[SectionInfo]:
        """Classify sections as song or speaking based on BPM presence.

        Args:
            sections: List of section info objects to classify

        Returns:
            List of sections with updated section types
        """
        classified_sections = []

        for section in sections:
            # Determine section type based on BPM
            if section.bpm is not None:
                section_type = SectionType.SONG
            else:
                section_type = SectionType.SPEAKING

            # Create new section with updated type
            classified_section = SectionInfo(
                section_number=section.section_number,
                start_sample=section.start_sample,
                end_sample=section.end_sample,
                section_type=section_type,
                bpm=section.bpm,
            )

            classified_sections.append(classified_section)

        return classified_sections

    @classmethod
    def process_sections(
        cls,
        raw_sections: list[SectionInfo],
        sample_rate: int,
        min_section_length_seconds: float,
    ) -> list[SectionInfo]:
        """Complete section processing pipeline.

        Args:
            raw_sections: Raw sections from analyzer
            sample_rate: Sample rate for time calculations
            min_section_length_seconds: Minimum section length for merging

        Returns:
            Fully processed sections with metadata and classifications
        """
        # First classify sections based on BPM
        classified_sections = cls.classify_sections(raw_sections)

        # Then merge short sections
        merged_sections = cls.merge_short_sections(
            classified_sections, min_section_length_seconds, sample_rate
        )

        # Finally calculate metadata
        processed_sections = cls.calculate_section_metadata(merged_sections, sample_rate)

        return processed_sections