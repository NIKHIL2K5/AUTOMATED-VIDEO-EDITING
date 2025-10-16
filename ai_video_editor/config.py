from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class CaptionConfig:
	font: str = "Arial"
	fontsize: int = 36
	position: str = "bottom"  # bottom, top
	stroke_width: int = 2
	stroke_color: str = "black"
	color: str = "white"


@dataclass
class TransitionConfig:
	default: str = "crossfade"
	duration: float = 0.5


@dataclass
class StyleConfig:
	name: Optional[str] = None  # cinematic, vlog, reel, youtube
	stabilize: bool = True
	color_correct: bool = True
	denoise_video: bool = False
	# parameters
	exposure_boost: float = 0.01
	contrast_gain: float = 1.05


@dataclass
class OverlayConfig:
	title: Optional[str] = None
	subtitle: Optional[str] = None
	watermark: Optional[str] = None
	watermark_position: str = "bottom-right"
	title_duration: float = 2.0


@dataclass
class ExportConfig:
	resolutions: List[str] = field(default_factory=lambda: ["1080p", "720p"])
	preview: bool = False


@dataclass
class AppConfig:
	input_dir: Path = Path("./input")
	output_dir: Path = Path("./output")
	music_dir: Optional[Path] = None
	metadata_path: Optional[Path] = None
	videos: List[Dict[str, Any]] = field(default_factory=list)
	captions: CaptionConfig = field(default_factory=CaptionConfig)
	transitions: TransitionConfig = field(default_factory=TransitionConfig)
	style: StyleConfig = field(default_factory=StyleConfig)
	overlay: OverlayConfig = field(default_factory=OverlayConfig)
	export: ExportConfig = field(default_factory=ExportConfig)
	whisper_model: str = "small"
	max_workers: int = 1
	log_json: bool = True
	# new tuning fields
	highlight_min_scene_len: float = 2.0
	highlight_motion_threshold: float = 12.0
	highlight_top_k: int = 5
	music_gain_db: float = -18.0
	dry_run: bool = False


class ConfigError(Exception):
	pass


def _load_metadata_file(path: Path) -> Dict[str, Any]:
	if not path or not path.exists():
		return {}
	if path.suffix.lower() in (".yml", ".yaml"):
		return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
	if path.suffix.lower() == ".json":
		return json.loads(path.read_text(encoding="utf-8"))
	raise ConfigError(f"Unsupported metadata format: {path.suffix}")


def _style_preset(name: Optional[str]) -> Dict[str, Any]:
	name = (name or "").lower()
	if name == "cinematic":
		return {"exposure_boost": 0.02, "contrast_gain": 1.08}
	if name == "vlog":
		return {"exposure_boost": 0.015, "contrast_gain": 1.04}
	if name in {"reel", "instagram", "short"}:
		return {"exposure_boost": 0.025, "contrast_gain": 1.1}
	if name == "youtube":
		return {"exposure_boost": 0.01, "contrast_gain": 1.05}
	return {}


def load_config(
	*,
	input_dir: Path,
	output_dir: Path,
	music_dir: Optional[Path],
	metadata_path: Optional[Path],
	style: Optional[str],
	resolutions: List[str],
	preview: bool,
	whisper_model: str,
	max_workers: int,
) -> AppConfig:
	metadata = _load_metadata_file(metadata_path) if metadata_path else {}

	videos = metadata.get("videos", [])
	if not videos:
		# Discover videos in input directory
		videos = [
			{"file": str(p)}
			for p in sorted(input_dir.glob("*"))
			if p.suffix.lower() in {".mp4", ".mov", ".mkv", ".avi", ".m4v"}
		]

	style_value = metadata.get("style")
	style_cfg = None
	if isinstance(style_value, dict):
		preset_params = _style_preset(style)
		style_cfg = StyleConfig(name=style, **preset_params, **style_value)
	else:
		preset_params = _style_preset(style or style_value)
		style_cfg = StyleConfig(name=style or style_value, **preset_params)

	overlay_cfg = OverlayConfig(**metadata.get("overlay", {}))

	cfg = AppConfig(
		input_dir=input_dir,
		output_dir=output_dir,
		music_dir=music_dir,
		metadata_path=metadata_path,
		videos=videos,
		captions=CaptionConfig(**metadata.get("captions", {})),
		transitions=TransitionConfig(**metadata.get("transitions", {})),
		style=style_cfg,
		overlay=overlay_cfg,
		export=ExportConfig(resolutions=resolutions or ["1080p", "720p"], preview=preview),
		whisper_model=whisper_model,
		max_workers=max_workers,
		log_json=True,
	)

	# Optional metadata-driven tuning
	if "highlight" in metadata:
		h = metadata["highlight"] or {}
		cfg.highlight_min_scene_len = float(h.get("min_scene_len", cfg.highlight_min_scene_len))
		cfg.highlight_motion_threshold = float(h.get("motion_threshold", cfg.highlight_motion_threshold))
		cfg.highlight_top_k = int(h.get("top_k", cfg.highlight_top_k))
	if "audio" in metadata:
		a = metadata["audio"] or {}
		cfg.music_gain_db = float(a.get("music_gain_db", cfg.music_gain_db))

	cfg.output_dir.mkdir(parents=True, exist_ok=True)
	return cfg
