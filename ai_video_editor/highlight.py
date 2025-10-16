from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np


def detect_scenes_and_highlights(
	video_path: Path,
	min_scene_len_sec: float = 2.0,
	motion_threshold: float = 12.0,
	fps_fallback: float = 30.0,
) -> List[Tuple[float, float, float]]:
	"""
	Return list of (start_sec, end_sec, score) for candidate highlights.
	Uses histogram difference for scene cuts and optical flow magnitude for motion score.
	"""
	cap = cv2.VideoCapture(str(video_path))
	if not cap.isOpened():
		return []

	fps = cap.get(cv2.CAP_PROP_FPS)
	if not fps or fps <= 0:
		fps = fps_fallback

	prev_gray = None
	prev_hist = None
	frame_idx = 0
	scenes = [0]
	motion_scores = []

	while True:
		ret, frame = cap.read()
		if not ret:
			break
		gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		hist = cv2.calcHist([gray], [0], None, [64], [0, 256])
		hist = cv2.normalize(hist, hist).flatten()

		if prev_hist is not None:
			diff = cv2.compareHist(prev_hist.astype(np.float32), hist.astype(np.float32), cv2.HISTCMP_BHATTACHARYYA)
			if diff > 0.5:  # scene cut
				scenes.append(frame_idx)

		if prev_gray is not None:
			flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
			mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
			motion_scores.append(float(np.mean(mag)))
		prev_gray = gray
		prev_hist = hist
		frame_idx += 1

	scenes.append(frame_idx)
	cap.release()

	# Build segments and score by average motion; filter by min length
	highlights: List[Tuple[float, float, float]] = []
	for s, e in zip(scenes[:-1], scenes[1:]):
		start_sec = s / fps
		end_sec = e / fps
		if end_sec - start_sec < min_scene_len_sec:
			continue
		seg_motion = motion_scores[s : max(s, e - 1)] if motion_scores else []
		score = float(np.mean(seg_motion)) if seg_motion else 0.0
		if score >= motion_threshold * 0.1:  # scaled threshold
			highlights.append((start_sec, end_sec, score))

	# Sort by score descending
	highlights.sort(key=lambda x: x[2], reverse=True)
	return highlights
