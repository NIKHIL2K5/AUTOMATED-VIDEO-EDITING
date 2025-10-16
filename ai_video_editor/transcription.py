from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import tempfile
import subprocess


def transcribe_to_srt(audio_or_video_path: Path, model: str = "small") -> List[Tuple[float, float, str]]:
	"""
	Returns list of (start_sec, end_sec, text). Prefers whisper CLI; falls back to Python API if CLI fails.
	"""
	try:
		return _via_cli(audio_or_video_path, model)
	except Exception:
		try:
			return _via_python(audio_or_video_path, model)
		except Exception:
			return []


def _via_cli(audio_or_video_path: Path, model: str) -> List[Tuple[float, float, str]]:
	with tempfile.TemporaryDirectory() as td:
		out_dir = Path(td)
		cmd = [
			"whisper",
			str(audio_or_video_path),
			"--model",
			model,
			"--task",
			"transcribe",
			"--output_dir",
			str(out_dir),
			"--output_format",
			"srt",
		]
		subprocess.run(cmd, check=True)
		srt_path = out_dir / f"{audio_or_video_path.stem}.srt"
		if not srt_path.exists():
			return []
		return _parse_srt(srt_path.read_text(encoding="utf-8", errors="ignore"))


def _via_python(audio_or_video_path: Path, model: str) -> List[Tuple[float, float, str]]:
	import whisper  # type: ignore
	m = whisper.load_model(model)
	result = m.transcribe(str(audio_or_video_path))
	segments = result.get("segments", [])
	entries: List[Tuple[float, float, str]] = []
	for seg in segments:
		entries.append((float(seg.get("start", 0.0)), float(seg.get("end", 0.0)), seg.get("text", "")))
	return entries


def _parse_srt(srt_text: str) -> List[Tuple[float, float, str]]:
	entries: List[Tuple[float, float, str]] = []
	blocks = srt_text.split("\n\n")
	for b in blocks:
		lines = [l for l in b.splitlines() if l.strip()]
		if len(lines) < 2:
			continue
		try:
			time_line = lines[1]
			start_s, end_s = _srt_time_range_to_seconds(time_line)
			text = " ".join(lines[2:])
			entries.append((start_s, end_s, text))
		except Exception:
			continue
	return entries


def _srt_time_range_to_seconds(line: str) -> Tuple[float, float]:
	start_str, _, end_str = line.partition(" --> ")
	return (_srt_time_to_seconds(start_str), _srt_time_to_seconds(end_str))


def _srt_time_to_seconds(t: str) -> float:
	h, m, rest = t.split(":")
	sec, ms = rest.split(",")
	return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000.0
