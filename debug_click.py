#!/usr/bin/env python3
"""Debug script for click track analysis algorithm development."""

import numpy as np
import soundfile as sf
from scipy import signal


def analyze_click_track(audio_path: str, gap_threshold_seconds: float = 3.0) -> list[dict]:
    """New algorithm for click track analysis."""
    
    # Load entire audio file
    audio, sr = sf.read(audio_path)
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)
    
    total_samples = len(audio)
    total_duration = total_samples / sr
    print(f"Loaded: {total_duration:.1f}s, {total_samples} samples")
    
    # Compute envelope using Hilbert transform
    envelope = np.abs(signal.hilbert(audio))
    
    # Smooth envelope with 50ms window
    window_size = int(0.05 * sr)
    smoothed = signal.convolve(envelope, np.ones(window_size)/window_size, mode='same')
    
    # Find onset peaks
    min_distance = int(0.1 * sr)  # 100ms minimum between peaks
    peaks, _ = signal.find_peaks(smoothed, distance=min_distance, prominence=0.001)
    
    if len(peaks) == 0:
        print("No onsets detected - entire file is speaking")
        return [{"type": "speaking", "start": 0, "end": total_duration, "bpm": None}]
    
    print(f"Found {len(peaks)} onset peaks")
    
    # Convert to seconds
    onset_times = peaks / sr
    
    # Find gaps between onsets
    gap_threshold = gap_threshold_seconds
    sections = []
    current_section_start = 0.0
    current_onsets = []
    
    for i, onset_time in enumerate(onset_times):
        if i == 0:
            current_onsets.append(onset_time)
        else:
            gap = onset_time - onset_times[i-1]
            if gap >= gap_threshold:
                # End current section, start new one
                section_end = onset_times[i-1] + 0.1
                sections.append({
                    "type": "song",
                    "start": current_section_start,
                    "end": section_end,
                    "onsets": current_onsets.copy()
                })
                current_section_start = onset_time
                current_onsets = [onset_time]
            else:
                current_onsets.append(onset_time)
    
    # Add final song section
    if current_onsets:
        last_onset = current_onsets[-1]
        section_end = last_onset + 0.1
        sections.append({
            "type": "song",
            "start": current_section_start,
            "end": section_end,
            "onsets": current_onsets.copy()
        })
    
    # Check for trailing silence
    if sections:
        last_section_end = sections[-1]["end"]
        remaining_duration = total_duration - last_section_end
        if remaining_duration >= gap_threshold:
            sections.append({
                "type": "speaking",
                "start": last_section_end,
                "end": total_duration,
                "onsets": []
            })
    
    # Calculate BPM for each section
    for section in sections:
        if section["type"] == "song" and len(section["onsets"]) >= 4:
            onsets = section["onsets"]
            iois = [onsets[i] - onsets[i-1] for i in range(1, len(onsets))]
            median_ioi = np.median(iois)
            bpm = 60.0 / median_ioi if median_ioi > 0 else None
            section["bpm"] = int(round(bpm)) if bpm and 45 <= bpm <= 300 else None
        else:
            section["bpm"] = None
    
    return sections


if __name__ == "__main__":
    # Test on synthetic file
    sections = analyze_click_track("synthetic_click.wav", gap_threshold_seconds=3.0)
    
    print("\nDetected sections:")
    for i, section in enumerate(sections):
        duration = section["end"] - section["start"]
        stype = section["type"]
        bpm = section.get("bpm")
        start = section["start"]
        end = section["end"]
        print(f"  {i+1}. {stype}: {start:.1f}s - {end:.1f}s ({duration:.1f}s), BPM: {bpm}")
    
    # Expected sections
    print("\nExpected sections:")
    expected = [
        ("song", 0, 60, 120),
        ("song", 65, 155, 100),
        ("song", 163, 208, 140),
        ("song", 220, 340, 80),
        ("speaking", 355, 415, None),
    ]
    for i, (stype, start, end, bpm) in enumerate(expected):
        duration = end - start
        print(f"  {i+1}. {stype}: {start:.1f}s - {end:.1f}s ({duration:.1f}s), BPM: {bpm}")
