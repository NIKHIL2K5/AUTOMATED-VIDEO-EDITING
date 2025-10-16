from __future__ import annotations

from pathlib import Path
import hashlib
import time


def ensure_dir(path: Path) -> None:
	path.mkdir(parents=True, exist_ok=True)


def safe_stem(path: Path) -> str:
	return path.stem.replace(" ", "_")


def timestamped_name(base: str) -> str:
	return f"{base}_{int(time.time())}"


def hash_path(path: Path) -> str:
	return hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:8]
