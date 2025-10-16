from __future__ import annotations

from pathlib import Path
from typing import Optional

from moviepy.editor import ImageClip, CompositeVideoClip, VideoFileClip
import os
import cv2
import numpy as np


def add_title_card(clip: VideoFileClip, title: str, subtitle: Optional[str] = None, duration: float = 2.0, font: str = "Arial", fontsize: int = 64):
    w, h = clip.size
    txt = title if not subtitle else f"{title}\n{subtitle}"

    # 1) Try pygame (no ImageMagick). Works headless with SDL_VIDEODRIVER=dummy.
    try:
        # Defer import so pygame isn't a hard dependency if not used
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        import pygame

        pygame.init()
        try:
            # Create a surface in memory (no window shown due to dummy driver)
            surface = pygame.Surface((w, h))
            surface.fill((0, 0, 0))

            # Use system font; if font name not found, fallback automatically
            pg_font = pygame.font.SysFont(font, fontsize)

            lines = txt.split("\n")
            # Render lines to get sizes first
            rendered = [pg_font.render(line, True, (255, 255, 255)) for line in lines]
            total_h = sum(r.get_height() for r in rendered) + int(0.6 * fontsize) * (len(rendered) - 1)
            y = (h - total_h) // 2
            for i, r in enumerate(rendered):
                x = (w - r.get_width()) // 2
                surface.blit(r, (x, y))
                y += r.get_height() + int(0.6 * fontsize)

            # Convert to numpy array (RGB)
            arr = pygame.surfarray.pixels3d(surface).swapaxes(0, 1).copy()
            # MoviePy expects RGB; pygame surface is already RGB
            img_clip = ImageClip(arr).set_duration(duration)
            return CompositeVideoClip([img_clip])
        finally:
            pygame.quit()
    except Exception:
        pass

    # 2) Fallback: OpenCV text (no ImageMagick needed)
    bg = np.zeros((h, w, 3), dtype=np.uint8)
    lines = txt.split("\n")
    # Approximate mapping from fontsize to OpenCV scale
    scale = max(0.5, fontsize / 40.0)
    thickness = max(1, fontsize // 20)
    font_face = cv2.FONT_HERSHEY_SIMPLEX
    # Compute total text block height to vertically center
    sizes = [cv2.getTextSize(line, font_face, scale, thickness)[0] for line in lines]
    total_h = sum(sz[1] for sz in sizes) + (len(lines) - 1) * int(0.6 * fontsize)
    y = (h - total_h) // 2 + sizes[0][1]
    for i, (line, sz) in enumerate(zip(lines, sizes)):
        x = (w - sz[0]) // 2
        cv2.putText(bg, line, (x, y), font_face, scale, (255, 255, 255), thickness, cv2.LINE_AA)
        y += sz[1] + int(0.6 * fontsize)
    img_clip = ImageClip(bg[:, :, ::-1]).set_duration(duration)
    return CompositeVideoClip([img_clip])


def overlay_watermark(clip: VideoFileClip, image_path: Path, position: str = "bottom-right", opacity: float = 0.7, width_ratio: float = 0.15):
    w, h = clip.size
    wm = ImageClip(str(image_path)).set_opacity(opacity)
    new_w = int(w * width_ratio)
    wm = wm.resize(width=new_w)
    pos = {
        "bottom-right": (w - wm.w - 20, h - wm.h - 20),
        "bottom-left": (20, h - wm.h - 20),
        "top-right": (w - wm.w - 20, 20),
        "top-left": (20, 20),
    }.get(position, (w - wm.w - 20, h - wm.h - 20))
    return CompositeVideoClip([clip, wm.set_position(pos).set_duration(clip.duration)])
