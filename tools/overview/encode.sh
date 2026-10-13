#!/usr/bin/env bash
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
PAGE="$(cd "$HERE/../.." && pwd)"
FR="${1:-/tmp/claude-1001/-home-cvlab20-project-eunbeen-LagerNVS4d/2029518d-9a2f-403f-a387-494dcea53f53/scratchpad/ovframes}"
ffmpeg -y -v error -framerate 30 -i "$FR/f%05d.jpg" -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p -movflags +faststart "$PAGE/static/videos/overview.mp4"
ffmpeg -y -v error -ss 1.5 -i "$PAGE/static/videos/overview.mp4" -frames:v 1 -c:v libwebp -quality 88 "$PAGE/static/images/overview-poster.webp"
ffprobe -v error -show_entries format=duration,size -of csv=p=0 "$PAGE/static/videos/overview.mp4"
