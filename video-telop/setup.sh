#!/bin/bash
# 作業環境の準備（新しいセッションで最初に1回だけ実行）
set -e
cd "$(dirname "$0")"
pip install --break-system-packages -q faster-whisper pillow numpy
mkdir -p fonts
for w in Regular Bold Black; do
  [ -f fonts/ZenMaruGothic-$w.ttf ] || curl -sSL -o fonts/ZenMaruGothic-$w.ttf \
    "https://raw.githubusercontent.com/google/fonts/main/ofl/zenmarugothic/ZenMaruGothic-$w.ttf"
done
echo "準備OK"
