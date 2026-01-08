#!/usr/bin/env python3
"""Quick click analysis test script for debugging section splitting."""

import sys
from pathlib import Path
import numpy as np
import soundfile as sf
from rich.console import Console

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.audio.click.analyzer import ScipyClickAnalyzer
from src.config.models import SectionSplittingConfig


def generate_synthetic_click_track(output_path: Path, sample_rate: int = 48000):
    """Generate a synthetic click track with known BPM changes for testing."""
    console = Console()
    console.print(f"[bold]Generating synthetic click track: {output_path}[/bold]")
    
    # Define the structure:
    # Section 1: 120 BPM for 60 seconds
    # Gap: 5 seconds silence
    # Section 2: 100 BPM for 90 seconds  
    # Gap: 8 seconds silence
    # Section 3: 140 BPM for 45 seconds
    # Gap: 12 seconds silence
    # Section 4: 80 BPM for 120 seconds (slow song)
    # Gap: 15 seconds silence
    # Section 5: Speaking section (no clicks) for 60 seconds
    
    sections = [
        {"bpm": 120, "duration": 60.0, "name": "120 BPM song"},
        {"bpm": None, "duration": 35.0, "name": "Gap"},
        {"bpm": 100, "duration": 90.0, "name": "100 BPM song"},
        {"bpm": None, "duration": 28.0, "name": "Gap"},
        {"bpm": 140, "duration": 45.0, "name": "140 BPM song"},
        {"bpm": None, "duration": 12.0, "name": "Gap"},
        {"bpm": 80, "duration": 120.0, "name": "80 BPM song"},
        {"bpm": None, "duration": 15.0, "name": "Gap"},
        {"bpm": None, "duration": 60.0, "name": "Speaking section"},
    ]
    
    # Generate audio
    audio_data = []
    
    for section in sections:
        duration = section["duration"]
        bpm = section["bpm"]
        
        if bpm is None:
            # Silence
            samples = np.zeros(int(duration * sample_rate))
            console.print(f"  {section['name']}: {duration}s silence")
        else:
            # Click track
            # Calculate click interval
            clicks_per_second = bpm / 60.0
            click_interval_samples = int(sample_rate / clicks_per_second)
            
            # Generate click impulses
            num_clicks = int(duration * clicks_per_second)
            samples = np.zeros(int(duration * sample_rate))
            
            for i in range(num_clicks):
                click_sample = i * click_interval_samples
                if click_sample < len(samples):
                    # Generate continuous click tone with amplitude modulation
                    # Click lasts for 50ms with high amplitude
                    click_length = int(0.05 * sample_rate)  # 50ms click
                    start = click_sample
                    end = min(click_sample + click_length, len(samples))
                    
                    # Generate 1600 Hz tone
                    t = np.linspace(0, (end-start)/sample_rate, end-start)
                    tone = 0.3 * np.sin(2 * np.pi * 1600 * t)  # 1600 Hz tone
                    
                    # Apply amplitude envelope: quick attack, slow decay
                    attack_samples = int(0.005 * sample_rate)  # 5ms attack
                    decay_samples = click_length - attack_samples
                    
                    envelope = np.ones(end-start)
                    envelope[:attack_samples] = np.linspace(0, 1, attack_samples)  # Linear attack
                    envelope[attack_samples:] = np.exp(-np.linspace(0, 3, decay_samples))  # Exponential decay
                    
                    click_wave = tone * envelope
                    samples[start:end] += click_wave
            
            console.print(f"  {section['name']}: {duration}s, {bpm} BPM ({num_clicks} clicks)")
        
        audio_data.append(samples)
    
    # Concatenate all sections
    full_audio = np.concatenate(audio_data)
    
    # Normalize
    max_val = np.max(np.abs(full_audio))
    if max_val > 0:
        full_audio = full_audio / max_val * 0.8
    
    # Save
    sf.write(str(output_path), full_audio, sample_rate)
    
    total_duration = len(full_audio) / sample_rate
    console.print(f"[green]Saved synthetic click track: {total_duration:.1f} seconds[/green]")
    
    return sections


def analyze_click_track(click_path: Path, config: SectionSplittingConfig):
    """Analyze a click track and show detailed results."""
    console = Console()

    if not click_path.exists():
        console.print(f"[red]Error: Click track file not found: {click_path}[/red]")
        return

    # Get basic file info
    with sf.SoundFile(str(click_path)) as f:
        sample_rate = f.samplerate
        channels = f.channels
        duration = len(f) / sample_rate

    console.print(f"[bold]Click Track Analysis[/bold]")
    console.print(f"File: {click_path}")
    console.print(f"Sample rate: {sample_rate} Hz")
    console.print(f"Channels: {channels}")
    console.print(f"Duration: {duration:.1f} seconds")

    # Check signal levels
    with sf.SoundFile(str(click_path)) as f:
        # Read first 60 seconds or whole file if shorter
        samples_to_read = min(int(60 * sample_rate), len(f))
        data = f.read(samples_to_read)

        if data.ndim > 1:
            data = np.mean(data, axis=1)  # Convert to mono

        peak_amplitude = np.max(np.abs(data))
        rms_amplitude = np.sqrt(np.mean(data**2))

        # Count samples above various thresholds
        thresholds = [0.001, 0.01, 0.1]
        for threshold in thresholds:
            above_threshold = np.sum(np.abs(data) > threshold)
            percent_above = 100 * above_threshold / len(data)
            console.print(f"Samples above {threshold}: {above_threshold} ({percent_above:.1f}%)")

        console.print(f"Peak amplitude: {peak_amplitude:.4f}")
        console.print(f"RMS amplitude: {rms_amplitude:.4f}")
        
        # Analyze frequency content
        from scipy import signal as scipy_signal
        freqs, psd = scipy_signal.welch(data, fs=sample_rate, nperseg=4096)
        peak_freq_idx = np.argmax(psd)
        peak_freq = freqs[peak_freq_idx]
        console.print(f"Peak frequency: {peak_freq:.1f} Hz")
        
        # Check for high frequency content
        high_freq_mask = freqs > 1000
        if np.any(high_freq_mask):
            high_freq_power = np.sum(psd[high_freq_mask])
            total_power = np.sum(psd)
            high_freq_percent = 100 * high_freq_power / total_power
            console.print(f"Power above 1kHz: {high_freq_percent:.1f}%")

    # Analyze with current config
    console.print(f"\n[bold]Analysis with current config:[/bold]")
    console.print(f"Bandpass: {config.bandpass_low}-{config.bandpass_high} Hz")
    console.print(f"Peak prominence: {config.peak_prominence}")
    console.print(f"Min peak distance: {config.min_peak_distance} seconds")
    console.print(f"Gap threshold: {config.gap_threshold_seconds} seconds")

    analyzer = ScipyClickAnalyzer(config)
    boundaries = analyzer.analyze(click_path, sample_rate)

    console.print(f"\n[bold]Results:[/bold]")
    console.print(f"Detected {len(boundaries.sections)} sections")

    for section in boundaries.sections:
        duration_sec = section.get_duration_seconds(sample_rate)
        console.print(f"  Section {section.section_number}: {section.section_type.value}, "
                     f"{duration_sec:.1f}s, BPM: {section.bpm}")

    # Test different gap thresholds
    console.print(f"\n[bold]Testing different gap thresholds:[/bold]")
    
    for gap_threshold in [3.0, 5.0, 10.0, 15.0]:
        console.print(f"\n[blue]Gap threshold: {gap_threshold}s[/blue]")
        test_config = SectionSplittingConfig(
            enabled=True, gap_threshold_seconds=gap_threshold, min_section_length_seconds=15.0,
            bandpass_low=20, bandpass_high=20000, filter_order=4,
            min_peak_distance=0.1, peak_prominence=0.001, novelty_window=0.001,  # Reduced from 0.05
            bpm_window_seconds=5.0, min_bpm=45, max_bpm=300, bpm_change_threshold=5
        )
        analyzer = ScipyClickAnalyzer(test_config)
        boundaries = analyzer.analyze(click_path, sample_rate)
        console.print(f"Detected {len(boundaries.sections)} sections")
        for section in boundaries.sections:
            duration_sec = section.get_duration_seconds(sample_rate)
            console.print(f"  Section {section.section_number}: {section.section_type.value}, "
                         f"{duration_sec:.1f}s, BPM: {section.bpm}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_click_analysis.py <click_track_path> [--generate]")
        print("  --generate: Generate synthetic click track instead of analyzing")
        print("Examples:")
        print("  python test_click_analysis.py synthetic_click.wav --generate")
        print("  python test_click_analysis.py 'D:/Exchange Recordings/20260104/test_sbc4/17_Click.wav'")
        sys.exit(1)

    click_path = Path(sys.argv[1])
    
    if len(sys.argv) > 2 and sys.argv[2] == "--generate":
        # Generate synthetic click track
        sections = generate_synthetic_click_track(click_path)
        print("\nExpected sections:")
        current_time = 0
        for i, section in enumerate(sections, 1):
            print(f"  Section {i}: {section['name']} ({section['duration']}s, BPM: {section['bpm']})")
            current_time += section['duration']
        print(f"Total duration: {current_time}s")
    else:
        # Analyze existing click track
        # Default config
        config = SectionSplittingConfig(
            enabled=True,
            gap_threshold_seconds=10.0,  # Updated default
            min_section_length_seconds=15.0,
            bpm_change_threshold=5,  # Updated default
            bandpass_low=20,  # Updated defaults
            bandpass_high=20000,
            filter_order=4,
            min_peak_distance=0.1,
            peak_prominence=0.001,  # Updated default
            novelty_window=0.001,  # Reduced from 0.05
            bpm_window_seconds=5.0,
            min_bpm=45,
            max_bpm=300,
        )

        analyze_click_track(click_path, config)


if __name__ == "__main__":
    main()