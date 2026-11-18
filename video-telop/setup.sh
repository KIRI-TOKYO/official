#!/bin/bash
# 作業環境の準備（新しいセッションで最初に1回だけ実行）
set -e
cd "$(dirname "$0")"
pip install --break-system-packages -q faster-whisper pillow numpy pykakasi
pip install --break-system-packages -q torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu
mkdir -p fonts
for w in Regular Bold Black; do
  [ -f fonts/ZenMaruGothic-$w.ttf ] || curl -sSL -o fonts/ZenMaruGothic-$w.ttf \
    "https://raw.githubusercontent.com/google/fonts/main/ofl/zenmarugothic/ZenMaruGothic-$w.ttf"
done
# キーワード用：コーポレート・ロゴ（LOGOTYPE.JP、SIL Open Font License）
if [ ! -f fonts/Corporate-Logo-Bold-ver3.otf ]; then
  curl -sSL -o fonts/cl.zip https://logotype.jp/wp-content/uploads/2022/10/Corporate-Logo-Bold-ver3.zip
  python3 -c "import zipfile;z=zipfile.ZipFile('fonts/cl.zip');open('fonts/Corporate-Logo-Bold-ver3.otf','wb').write(z.read('Corporate-Logo-Bold-ver3/Corporate-Logo-Bold-ver3.otf'))"
  rm -f fonts/cl.zip
fi
echo "準備OK"
