from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip

from .config import AppConfig
from .media_probe import probe_media
from .highlight import detect_scenes_and_highlights
from .audio import normalize_audio, denoise_audio, choose_background_track, mix_background_music
from .transcription import transcribe_to_srt
from .captions import burn_captions
from .enhancements import apply_color_correction, stabilize_video
from .export import export_resolutions, export_preview
from .utils import ensure_dir, safe_stem, timestamped_name
from .logger import get_logger
from .transitions import apply_transitions
from .overlays import overlay_watermark, add_title_card


logger = get_logger()


def _build_sequence(video_path: Path, highlights: List[tuple], top_k: int = 5, pad: float = 0.25):
	clip = VideoFileClip(str(video_path))
	selected = highlights[:top_k]
	segments = []
	for s, e, _ in selected:
		start = max(0.0, s - pad)
		end = min(clip.duration, e + pad)
		segments.append(clip.subclip(start, end))
	# Fallback: if no highlights were selected, use the entire clip as a single segment
	if not segments:
		segments = [clip]
	return clip, segments


def process_single_video(config: AppConfig, video_item: Dict[str, Any]) -> Dict[str, Any]:
	video_path = Path(video_item["file"]).resolve()
	result_log: Dict[str, Any] = {
		"file": str(video_path),
		"outputs": [],
		"probe": {},
		"highlights": [],
		"dry_run": bool(config.dry_run),
	}
	if not video_path.exists():
		logger.warning(f"Skipping missing file: {video_path}")
		result_log["error"] = "missing_file"
		return result_log

	meta = probe_media(video_path)
	result_log["probe"] = meta
	logger.info(f"Probed {video_path.name}: {meta}")

	highlights = detect_scenes_and_highlights(
		video_path,
		min_scene_len_sec=config.highlight_min_scene_len,
		motion_threshold=config.highlight_motion_threshold,
	)
	if not highlights and video_item.get("trims"):
		highlights = [(t["start"], t["end"], 1.0) for t in video_item.get("trims", [])]
	result_log["highlights"] = highlights[:10]

	base_clip, segments = _build_sequence(video_path, highlights, top_k=config.highlight_top_k)
	seq_clip = apply_transitions(segments, kind=config.transitions.default, duration=config.transitions.duration)

	# Title card optional
	if config.overlay.title:
		title = add_title_card(base_clip, config.overlay.title, config.overlay.subtitle, duration=config.overlay.title_duration)
		seq_clip = concatenate_videoclips([title, seq_clip], method="compose")

	# Enhancements
	if config.style.color_correct:
		seq_clip = apply_color_correction(seq_clip, exposure_boost=config.style.exposure_boost, contrast_gain=config.style.contrast_gain)
	if config.style.stabilize:
		seq_clip = stabilize_video(seq_clip)

	# Captions
	entries = transcribe_to_srt(video_path, model=config.whisper_model)
	if entries:
		seq_clip = burn_captions(
			seq_clip,
			entries,
			font=config.captions.font,
			fontsize=config.captions.fontsize,
			position=config.captions.position,
			color=config.captions.color,
			stroke_color=config.captions.stroke_color,
			stroke_width=config.captions.stroke_width,
		)

	# Watermark optional
	if config.overlay.watermark:
		wm_path = Path(config.overlay.watermark)
		if wm_path.exists():
			seq_clip = overlay_watermark(seq_clip, wm_path, position=config.overlay.watermark_position)

	# Audio processing
	final_audio = None
	if base_clip.audio is not None:
		tmp_path = Path(config.output_dir) / f"{safe_stem(video_path)}_temp_audio.wav"
		if not config.dry_run:
			base_clip.audio.write_audiofile(str(tmp_path))
			from pydub import AudioSegment
			voice = AudioSegment.from_file(str(tmp_path))
			voice = denoise_audio(voice)
			voice = normalize_audio(voice)
			bg = choose_background_track(config.music_dir)
			mixed = mix_background_music(voice, bg, beat_sync=True, music_gain_db=config.music_gain_db)
			mixed.export(str(tmp_path), format="wav")
			final_audio = AudioFileClip(str(tmp_path))

	# Compose final clip with processed audio if available
	if final_audio is not None:
		seq_clip = seq_clip.set_audio(final_audio)

	ensure_dir(config.output_dir)
	out_base = Path(config.output_dir) / f"{timestamped_name(safe_stem(video_path))}.mp4"

	if config.dry_run:
		logger.info(f"[DRY-RUN] Would export master and resolutions to base: {out_base}")
		result_log["outputs"].append(str(out_base))
		for r in config.export.resolutions:
			result_log["outputs"].append(str(out_base.parent / f"{out_base.stem}_{r}{out_base.suffix}"))
		if config.export.preview:
			result_log["outputs"].append(str(out_base.with_name(out_base.stem + "_preview.mp4")))
	else:
		# Export a master first
		seq_clip.write_videofile(str(out_base), codec="libx264", audio_codec="aac")
		result_log["outputs"].append(str(out_base))
		# Additional exports
		for p in export_resolutions(seq_clip, out_base, config.export.resolutions):
			result_log["outputs"].append(str(p))
		if config.export.preview:
			preview_path = out_base.with_name(out_base.stem + "_preview.mp4")
			export_preview(seq_clip, preview_path)
			result_log["outputs"].append(str(preview_path))

	# Write per-video JSON log
	if config.log_json:
		log_path = Path(config.output_dir) / f"{safe_stem(video_path)}_log.json"
		log_path.write_text(json.dumps(result_log, indent=2), encoding="utf-8")

	logger.info(f"Completed {"DRY-RUN " if config.dry_run else ""}processing for {video_path.name}")
	return result_log


def process_folder(config: AppConfig) -> None:
	results: List[Dict[str, Any]] = []
	if config.max_workers and config.max_workers > 1:
		with ThreadPoolExecutor(max_workers=config.max_workers) as ex:
			futures = {ex.submit(process_single_video, config, v): v for v in config.videos}
			for fut in as_completed(futures):
				try:
					results.append(fut.result())
				except Exception as e:
					logger.exception(f"Parallel task failed: {e}")
	else:
		for v in config.videos:
			try:
				results.append(process_single_video(config, v))
			except Exception as e:
				logger.exception(f"Failed processing {v}: {e}")

	# Optionally aggregate results here if needed
