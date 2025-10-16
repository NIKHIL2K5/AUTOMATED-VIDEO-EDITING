param(
	[string]$InputDir = "./raw_videos",
	[string]$OutputDir = "./exports",
	[string]$MusicDir = "./music",
	[string]$Metadata = "./metadata.yaml",
	[string]$Style = "cinematic"
)

py -3.13 -m ai_video_editor.cli `
	--input $InputDir `
	--output $OutputDir `
	--music $MusicDir `
	--metadata $Metadata `
	--style $Style `
	--resolutions 1080p,720p `
	--preview `
	--max-workers 2
