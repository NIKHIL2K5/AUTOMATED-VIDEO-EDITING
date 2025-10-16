from __future__ import annotations

import logging
from rich.logging import RichHandler


_logger = None


def get_logger() -> logging.Logger:
	global _logger
	if _logger is not None:
		return _logger

	logger = logging.getLogger("ai_video_editor")
	logger.setLevel(logging.INFO)
	if not logger.handlers:
		handler = RichHandler(rich_tracebacks=True, show_time=True, show_path=False)
		formatter = logging.Formatter("%(message)s")
		handler.setFormatter(formatter)
		logger.addHandler(handler)
	_logger = logger
	return logger
