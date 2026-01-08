#!/usr/bin/env python
"""Debug script to trace section boundary detection."""

import sys

import numpy as np
import soundfile as sf
from scipy import signal


def main() -> None:
    """Main entry point."""
    filepath = sys.argv[1] if len(sys.argv) > 1 else r"D:\Exchange Recordings\20260104\test_sbc4\17_Click.wav"
    
    # Load the click track
    audio, sr = sf.read(filepath)
    total_samples = len(audio)
    total_duration = len(audio) / sr
    print(f"Total duration: {total_duration:.1f}s ({total_samples} samples)")

    # Compute envelope
    envelope = np.abs(signal.hilbert(audio))

    # Smooth envelope
    window_size = int(0.05 * sr)
    smoothed = signal.convolve(envelope, np.ones(window_size) / window_size, mode="same")

    # Find peaks
    peaks, _ = signal.find_peaks(smoothed, distance=int(0.1 * sr), prominence=0.001)
    print(f"Found {len(peaks)} onset peaks")
    
    first_peak_time = peaks[0] / sr if len(peaks) > 0 else 0
    print(f"First peak at: {first_peak_time:.2f}s")

    # New algorithm: find song regions first, then add speaking sections in gaps
    gap_threshold = 3.0
    gap_threshold_samples = int(gap_threshold * sr)

    # Find song regions (clusters of onsets)
    song_regions = []
    current_onsets = []

    for i, onset in enumerate(peaks):
        if i == 0:
            current_onsets.append(onset)
        else:
            gap = onset - peaks[i - 1]
            if gap >= gap_threshold_samples:
                # Gap detected - finalize current song region
                song_regions.append({
                    "start": current_onsets[0],
                    "end": current_onsets[-1] + int(0.1 * sr),
                    "onsets": len(current_onsets),
                })
                current_onsets = [onset]
            else:
                current_onsets.append(onset)

    # Add final song region
    if current_onsets:
        song_regions.append({
            "start": current_onsets[0],
            "end": current_onsets[-1] + int(0.1 * sr),
            "onsets": len(current_onsets),
        })

    # Build complete section list with speaking sections in gaps
    sections = []
    current_pos = 0

    for song_region in song_regions:
        # Check if there's a speaking section before this song
        if song_region["start"] - current_pos >= gap_threshold_samples:
            sections.append({
                "start": current_pos,
                "end": song_region["start"],
                "onsets": 0,
                "type": "speaking",
            })

        # Add the song section
        sections.append({
            "start": song_region["start"],
            "end": song_region["end"],
            "onsets": song_region["onsets"],
            "type": "song",
        })
        current_pos = song_region["end"]

    # Check for trailing silence (speaking section at end)
    if total_samples - current_pos >= gap_threshold_samples:
        sections.append({
            "start": current_pos,
            "end": total_samples,
            "onsets": 0,
            "type": "speaking",
        })

    print(f"\nDetected {len(sections)} sections:")
    for i, s in enumerate(sections):
        duration = (s["end"] - s["start"]) / sr
        sec_type = s["type"]
        start_time = s["start"] / sr
        end_time = s["end"] / sr
        onsets = s["onsets"]
        print(f"{i+1}. {sec_type}: {start_time:.1f}s - {end_time:.1f}s ({duration:.1f}s, {onsets} onsets)")

    # Sum of durations
    total_covered = sum((s["end"] - s["start"]) / sr for s in sections)
    print(f"\nTotal covered: {total_covered:.1f}s")
    print(f"File duration: {total_duration:.1f}s")


if __name__ == "__main__":
    main()
