from __future__ import annotations

from pathlib import Path
from typing import List

from moviepy.editor import VideoFileClip

RES_MAP = {
	"1080p": (1920, 1080),
	"720p": (1280, 720),
	"480p": (854, 480),
}


def export_resolutions(clip: VideoFileClip, out_base: Path, resolutions: List[str]) -> List[Path]:
	paths: List[Path] = []
	for r in resolutions:
		size = None
		if "x" in r:
			w, h = r.lower().split("x")
			size = (int(w), int(h))
		else:
			size = RES_MAP.get(r.lower())
		if not size:
			continue
		res_clip = clip.resize(newsize=size)
		out_path = out_base.parent / f"{out_base.stem}_{r}{out_base.suffix}"
		res_clip.write_videofile(str(out_path), codec="libx264", audio_codec="aac")
		paths.append(out_path)
	return paths


def export_preview(clip: VideoFileClip, out_path: Path, duration: float = 15.0) -> Path:
	sub = clip.subclip(0, min(duration, clip.duration))
	sub.write_videofile(str(out_path), codec="libx264", audio_codec="aac")
	return out_path
