from __future__ import annotations

from moviepy.editor import VideoFileClip
import numpy as np


def apply_color_correction(clip: VideoFileClip, exposure_boost: float = 0.01, contrast_gain: float = 1.05) -> VideoFileClip:
	def _fx(frame):
		arr = frame.astype(np.float32) / 255.0
		arr = np.clip(arr * contrast_gain + exposure_boost, 0.0, 1.0)
		return (arr * 255.0).astype("uint8")
	return clip.fl_image(_fx)


def stabilize_video(clip: VideoFileClip) -> VideoFileClip:
	# Placeholder: moviepy has no built-in stabilization; would require cv2 transform estimation
	# For now, return clip unchanged
	return clip
