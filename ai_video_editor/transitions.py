from __future__ import annotations

from typing import List
from moviepy.editor import VideoFileClip, concatenate_videoclips


def apply_transitions(segments: List[VideoFileClip], kind: str = "crossfade", duration: float = 0.5) -> VideoFileClip:
	if not segments:
		raise ValueError("No segments to stitch")
	if len(segments) == 1:
		return segments[0]
	kind = (kind or "crossfade").lower()
	if kind in {"crossfade", "fade"}:
		return concatenate_videoclips(segments, method="compose", padding=-duration)
	# default fallback
	return concatenate_videoclips(segments, method="compose")
