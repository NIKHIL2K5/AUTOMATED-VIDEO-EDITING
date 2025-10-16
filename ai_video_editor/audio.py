from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from pydub import AudioSegment, effects
import librosa
import noisereduce as nr


def load_audio(path: Path) -> AudioSegment:
	return AudioSegment.from_file(str(path))


def normalize_audio(audio: AudioSegment, target_dBFS: float = -14.0) -> AudioSegment:
	change = target_dBFS - audio.dBFS
	return audio.apply_gain(change)


def denoise_audio(audio: AudioSegment) -> AudioSegment:
	# Convert to numpy for noise reduction
	samples = np.array(audio.get_array_of_samples()).astype(np.float32)
	if audio.channels == 2:
		samples = samples.reshape((-1, 2)).mean(axis=1)
	y = samples / (np.max(np.abs(samples)) + 1e-9)
	y_reduced = nr.reduce_noise(y=y, sr=audio.frame_rate)
	y_reduced = (y_reduced * 32767.0).astype(np.int16)
	clean = AudioSegment(
		data=y_reduced.tobytes(),
		sample_width=2,
		frame_rate=audio.frame_rate,
		channels=1,
	)
	return clean


def choose_background_track(music_dir: Optional[Path]) -> Optional[Path]:
	if not music_dir or not music_dir.exists():
		return None
	supported = {".mp3", ".wav", ".flac", ".m4a"}
	tracks = [p for p in music_dir.iterdir() if p.suffix.lower() in supported]
	if not tracks:
		return None
	# Simple heuristic: pick the shortest track to avoid long exports
	tracks.sort(key=lambda p: load_audio(p).duration_seconds)
	return tracks[0]


def _find_beats(audio: AudioSegment) -> List[float]:
	y = np.array(audio.get_array_of_samples()).astype(np.float32)
	if audio.channels == 2:
		y = y.reshape((-1, 2)).mean(axis=1)
	y = y / (np.max(np.abs(y)) + 1e-9)
	sr = audio.frame_rate
	tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
	beat_times = librosa.frames_to_time(beats, sr=sr)
	return beat_times.tolist()


def _align_to_nearest_beat(audio: AudioSegment) -> AudioSegment:
	beats = _find_beats(audio)
	if not beats:
		return audio
	first = beats[0]
	offset_ms = int(first * 1000)
	return audio[offset_ms:]


def mix_background_music(
	voice: AudioSegment,
	music_path: Optional[Path],
	music_gain_db: float = -18.0,
	beat_sync: bool = True,
) -> AudioSegment:
	if not music_path:
		return voice
	music = load_audio(music_path)
	music = effects.normalize(music) + music_gain_db
	if beat_sync:
		music = _align_to_nearest_beat(music)
	if len(music) < len(voice):
		loops = int(np.ceil(len(voice) / len(music)))
		music = music * loops
	music = music[: len(voice)]
	return voice.overlay(music)
