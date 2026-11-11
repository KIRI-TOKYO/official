# 「間（ま）」で音声を細かく区切ってから、区切りごとに文字起こしする（時間が正確になる）
# 使い方: python3 transcribe_chunks.py 動画.mp4 出力.json
# Whisperは長いまとまりで文字起こしすると、言葉の時間が0.3〜1秒ずれることがある。
# 間の終わり＝話し始めは音から正確にわかるので、そこを区切りの頭にして時間のずれを防ぐ。
import sys, json, subprocess
import numpy as np
from faster_whisper import WhisperModel
src, out_path = sys.argv[1], sys.argv[2]
SR = 16000
pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'],
                     capture_output=True, check=True).stdout
au = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
n = len(au) // 160
db = 20 * np.log10(np.sqrt((au[:n*160].reshape(n, 160) ** 2).mean(1)) + 1e-9)
on = db > db.max() - 38
# 声のある区間を、0.25秒以上の間で区切る（短い息などは無視）
runs, j = [], 0
while j < n:
    if on[j]:
        k = j
        while k < n and (on[k] or (k + 25 < n and on[k:k+25].any())): k += 1
        if k - j >= 10: runs.append((j / 100, k / 100))
        j = k
    else: j += 1
model = WhisperModel("large-v3", device="cpu", compute_type="int8")
segs = []
for a, b in runs:
    pa, pb = max(0, a - 0.15), min(len(au) / SR, b + 0.15)   # 前後に少し余白をつけて渡す
    res, _ = model.transcribe(au[int(pa*SR):int(pb*SR)], language="ja", word_timestamps=True,
                              condition_on_previous_text=False, vad_filter=False)
    words = []
    for s in res:
        for w in s.words:
            ws, we = max(w.start + pa, a), min(max(w.end + pa, a + 0.01), b)   # 声のある区間の中に収める
            words.append({"s": ws, "e": max(we, ws + 0.01), "w": w.word})
    if words:
        text = ''.join(w['w'] for w in words)
        segs.append({"start": words[0]['s'], "end": words[-1]['e'], "text": text, "words": words})
        print(f"{a:6.2f}-{b:6.2f} {text}", flush=True)
json.dump(segs, open(out_path, 'w'), ensure_ascii=False, indent=1)
