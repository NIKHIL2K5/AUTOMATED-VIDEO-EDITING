import argparse
import sys
from pathlib import Path

from .config import load_config
from .pipeline import process_folder
from .logger import get_logger


def parse_args(argv=None):
	parser = argparse.ArgumentParser(
		description="AI-driven automated video editing pipeline"
	)
	parser.add_argument("--input", required=True, help="Folder with raw video files")
	parser.add_argument("--output", required=True, help="Output folder for exports")
	parser.add_argument("--music", default=None, help="Folder with royalty-free tracks")
	parser.add_argument("--metadata", default=None, help="Optional YAML/JSON metadata file")
	parser.add_argument("--style", default=None, help="Style preset: cinematic, vlog, reel, youtube")
	parser.add_argument(
		"--resolutions", default="1080p,720p", help="Comma-separated output resolutions"
	)
	parser.add_argument("--preview", action="store_true", help="Export preview clips")
	parser.add_argument("--whisper-model", default="small", help="Whisper model size")
	parser.add_argument("--max-workers", type=int, default=1, help="Parallel videos")
	# New flags
	parser.add_argument("--min-scene-len", type=float, default=2.0, help="Min scene length seconds")
	parser.add_argument("--motion-threshold", type=float, default=12.0, help="Motion score threshold")
	parser.add_argument("--top-k", type=int, default=5, help="Number of top highlights to keep")
	parser.add_argument("--music-gain-db", type=float, default=-18.0, help="Background music gain in dB")
	parser.add_argument("--title", default=None, help="Override title card text")
	parser.add_argument("--subtitle", default=None, help="Override subtitle text")
	parser.add_argument("--watermark", default=None, help="Path to watermark image")
	parser.add_argument("--watermark-position", default=None, help="Watermark position (bottom-right, etc)")
	parser.add_argument("--log-level", default="info", help="Log level: debug, info, warning, error")
	parser.add_argument("--dry-run", action="store_true", help="Run without writing files")
	return parser.parse_args(argv)


def main(argv=None):
	args = parse_args(argv)
	logger = get_logger()
	# Adjust log level
	lvl = str(args.log_level).upper()
	try:
		logger.setLevel(lvl)
	except Exception:
		pass

	input_dir = Path(args.input)
	output_dir = Path(args.output)
	music_dir = Path(args.music) if args.music else None
	metadata_path = Path(args.metadata) if args.metadata else None

	config = load_config(
		input_dir=input_dir,
		output_dir=output_dir,
		music_dir=music_dir,
		metadata_path=metadata_path,
		style=args.style,
		resolutions=[x.strip() for x in args.resolutions.split(",") if x.strip()],
		preview=args.preview,
		whisper_model=args.whisper_model,
		max_workers=args.max_workers,
	)

	# CLI overrides
	config.highlight_min_scene_len = float(args.min_scene_len)
	config.highlight_motion_threshold = float(args.motion_threshold)
	config.highlight_top_k = int(args.top_k)
	config.music_gain_db = float(args.music_gain_db)
	config.dry_run = bool(args.dry_run)
	if args.title is not None:
		config.overlay.title = args.title
	if args.subtitle is not None:
		config.overlay.subtitle = args.subtitle
	if args.watermark is not None:
		config.overlay.watermark = args.watermark
	if args.watermark_position is not None:
		config.overlay.watermark_position = args.watermark_position

	process_folder(config)
	logger.info("All done.")


if __name__ == "__main__":
	main(sys.argv[1:])
