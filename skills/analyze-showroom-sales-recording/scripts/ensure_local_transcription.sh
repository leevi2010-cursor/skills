#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "This installer currently supports the approved Apple Silicon macOS environment only." >&2
  exit 2
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  if ! command -v brew >/dev/null 2>&1; then
    echo "Missing ffmpeg and Homebrew. Install Homebrew or provide ffmpeg, then retry." >&2
    exit 3
  fi
  brew install ffmpeg
fi

if ! command -v mlx_whisper >/dev/null 2>&1; then
  if ! command -v uv >/dev/null 2>&1; then
    if ! command -v brew >/dev/null 2>&1; then
      echo "Missing uv and Homebrew. Install uv or provide mlx_whisper, then retry." >&2
      exit 4
    fi
    brew install uv
  fi
  uv tool install mlx-whisper
fi

ffmpeg -version | head -n 1
mlx_whisper --help >/dev/null
echo "Local transcription dependencies are ready."
