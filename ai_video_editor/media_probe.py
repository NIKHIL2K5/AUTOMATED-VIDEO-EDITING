from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

import ffmpeg
import cv2
import numpy as np


def probe_media(path: Path) -> Dict[str, Any]:
	info = {
		"path": str(path),
		"duration": None,
		"width": None,
		"height": None,
		"fps": None,
		"audio_channels": None,
		"sample_rate": None,
		"bit_rate": None,
	}
	try:
		probe = ffmpeg.probe(str(path))
		streams = probe.get("streams", [])
		format_info = probe.get("format", {})
		info["duration"] = float(format_info.get("duration")) if format_info.get("duration") else None
		info["bit_rate"] = int(format_info.get("bit_rate")) if format_info.get("bit_rate") else None
		for s in streams:
			if s.get("codec_type") == "video" and info["width"] is None:
				info["width"] = int(s.get("width")) if s.get("width") else None
				info["height"] = int(s.get("height")) if s.get("height") else None
				# fps could be in r_frame_rate like '30000/1001'
				rate = s.get("r_frame_rate") or s.get("avg_frame_rate")
				if rate and "/" in rate:
					num, den = rate.split("/")
					info["fps"] = float(num) / float(den) if float(den) != 0 else None
				elif rate:
					info["fps"] = float(rate)
			elif s.get("codec_type") == "audio" and info["audio_channels"] is None:
				info["audio_channels"] = int(s.get("channels")) if s.get("channels") else None
				info["sample_rate"] = int(s.get("sample_rate")) if s.get("sample_rate") else None
	except Exception:
		pass

	# fallback to cv2 for fps if missing
	if info.get("fps") is None:
		cap = cv2.VideoCapture(str(path))
		if cap.isOpened():
			fps = cap.get(cv2.CAP_PROP_FPS)
			info["fps"] = float(fps) if fps > 0 else None
			if info.get("width") is None:
				info["width"] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or None
			if info.get("height") is None:
				info["height"] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or None
		cap.release()

	return info
