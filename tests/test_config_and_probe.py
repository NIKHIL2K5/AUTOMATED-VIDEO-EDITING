from pathlib import Path
from ai_video_editor.config import load_config
from ai_video_editor.media_probe import probe_media


def test_load_config_defaults(tmp_path: Path):
	inp = tmp_path / "in"
	outp = tmp_path / "out"
	inp.mkdir()
	outp.mkdir()
	cfg = load_config(
		input_dir=inp,
		output_dir=outp,
		music_dir=None,
		metadata_path=None,
		style=None,
		resolutions=["720p"],
		preview=True,
		whisper_model="small",
		max_workers=1,
	)
	assert cfg.output_dir.exists()
	assert cfg.export.preview is True
	assert cfg.export.resolutions == ["720p"]


def test_probe_handles_missing(tmp_path: Path):
	p = tmp_path / "missing.mp4"
	info = probe_media(p)
	assert "width" in info and "fps" in info
