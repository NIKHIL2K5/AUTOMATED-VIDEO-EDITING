from __future__ import annotations

from typing import List, Tuple
from moviepy.editor import CompositeVideoClip, VideoFileClip, ImageClip
import os
import numpy as np
import cv2


def burn_captions(
	video: VideoFileClip,
	entries: List[Tuple[float, float, str]],
	font: str = "Arial",
	fontsize: int = 36,
	position: str = "bottom",
	color: str = "white",
	stroke_color: str = "black",
	stroke_width: int = 2,
):
	"""Render captions without ImageMagick using pygame (preferred) or OpenCV fallback.
	Each caption is rendered onto a transparent full-frame RGBA image and overlaid.
	"""
	W, H = video.size
	margin_x = 40
	margin_y = 40

	def _rgba_from_pygame(text: str) -> np.ndarray:
		os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
		import pygame
		pygame.init()
		try:
			# Full frame with alpha
			surface = pygame.Surface((W, H), flags=pygame.SRCALPHA)
			surface.fill((0, 0, 0, 0))
			pg_font = pygame.font.SysFont(font, fontsize)

			# Word-wrap to fit width
			max_width = W - 2 * margin_x
			words = text.split()
			lines: List[str] = []
			cur = ""
			for w in words:
				test = (cur + " " + w).strip()
				if pg_font.size(test)[0] <= max_width or not cur:
					cur = test
				else:
					lines.append(cur)
					cur = w
			if cur:
				lines.append(cur)

			# Measure heights
			rendered = [pg_font.render(line, True, (255, 255, 255)) for line in lines]
			heights = [r.get_height() for r in rendered]
			total_h = sum(heights) + int(0.4 * fontsize) * (len(lines) - 1)
			y = H - margin_y - total_h if position == "bottom" else margin_y

			# Render stroke then text per line
			stroke_offsets = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)] if stroke_width > 0 else []
			stroke_rgb = (0, 0, 0)
			text_rgb = (255, 255, 255)
			for line in lines:
				line_surf = pg_font.render(line, True, text_rgb)
				x = (W - line_surf.get_width()) // 2
				if stroke_offsets:
					for dx, dy in stroke_offsets:
						shadow = pg_font.render(line, True, stroke_rgb)
						surface.blit(shadow, (x + dx * stroke_width, y + dy * stroke_width))
				# main text
				surface.blit(line_surf, (x, y))
				y += line_surf.get_height() + int(0.4 * fontsize)

			# Convert surface to RGBA array
			arr_rgb = pygame.surfarray.pixels3d(surface).swapaxes(0, 1).copy()
			arr_a = pygame.surfarray.pixels_alpha(surface).swapaxes(0, 1).copy()
			rgba = np.dstack([arr_rgb, arr_a])
			return rgba
		finally:
			pygame.quit()

	def _rgba_from_opencv(text: str) -> np.ndarray:
		# Transparent BGRA canvas
		bgra = np.zeros((H, W, 4), dtype=np.uint8)
		font_face = cv2.FONT_HERSHEY_SIMPLEX
		scale = max(0.5, fontsize / 40.0)
		thickness = max(1, fontsize // 20)
		max_width = W - 2 * margin_x
		# Word-wrap
		words = text.split()
		lines: List[str] = []
		cur = ""
		for w in words:
			test = (cur + " " + w).strip()
			sz = cv2.getTextSize(test, font_face, scale, thickness)[0]
			if sz[0] <= max_width or not cur:
				cur = test
			else:
				lines.append(cur)
				cur = w
		if cur:
			lines.append(cur)

		sizes = [cv2.getTextSize(line, font_face, scale, thickness)[0] for line in lines]
		total_h = sum(sz[1] for sz in sizes) + int(0.4 * fontsize) * (len(lines) - 1)
		y = H - margin_y - total_h if position == "bottom" else margin_y + (sizes[0][1] if sizes else 0)
		for line, sz in zip(lines, sizes):
			x = (W - sz[0]) // 2
			# Stroke (approx) on alpha channel
			if stroke_width > 0:
				for dx in (-stroke_width, 0, stroke_width):
					for dy in (-stroke_width, 0, stroke_width):
						if dx == 0 and dy == 0:
							continue
						cv2.putText(bgra[:, :, 3], line, (x + dx, y + dy), font_face, scale, 255, thickness, cv2.LINE_AA)
			# Main alpha and RGB
			cv2.putText(bgra[:, :, 3], line, (x, y), font_face, scale, 255, thickness, cv2.LINE_AA)
			cv2.putText(bgra[:, :, 0], line, (x, y), font_face, scale, 255, thickness, cv2.LINE_AA)
			cv2.putText(bgra[:, :, 1], line, (x, y), font_face, scale, 255, thickness, cv2.LINE_AA)
			cv2.putText(bgra[:, :, 2], line, (x, y), font_face, scale, 255, thickness, cv2.LINE_AA)
			y += sz[1] + int(0.4 * fontsize)
		# Convert BGRA to RGBA
		rgba = bgra[:, :, [2, 1, 0, 3]]
		return rgba

	caption_clips = []
	for start, end, text in entries:
		if not text.strip():
			continue
		dur = max(0.05, end - start)
		# Try pygame first
		rgba = None
		try:
			rgba = _rgba_from_pygame(text)
		except Exception:
			pass
		if rgba is None:
			rgba = _rgba_from_opencv(text)

		rgb = rgba[:, :, :3]
		alpha = (rgba[:, :, 3] / 255.0).astype("float32")
		img = ImageClip(rgb, ismask=False).set_duration(dur)
		mask = ImageClip(alpha, ismask=True).set_duration(dur)
		img = img.set_mask(mask)
		pos = ("center", "bottom") if position == "bottom" else ("center", "top")
		img = img.set_position(pos).set_start(start)
		caption_clips.append(img)

	return CompositeVideoClip([video, *caption_clips])
