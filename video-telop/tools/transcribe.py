# 動画（または音声）を文字起こしして、言葉ごとの時間をJSONに保存する
# 使い方: python3 transcribe.py 動画.mp4 出力.json
import sys, json, subprocess
import numpy as np
from faster_whisper import WhisperModel

src, out_path = sys.argv[1], sys.argv[2]
SR = 16000
pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'],
                     capture_output=True, check=True).stdout
audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
model = WhisperModel("large-v3", device="cpu", compute_type="int8")

def run(a, offset=0.0):
    # initial_prompt や vad_filter を使うと、冒頭が抜けたり作文されたりしたので使わない
    segs, _ = model.transcribe(a, language="ja", word_timestamps=True, vad_filter=False)
    return [{"start": s.start + offset, "end": s.end + offset, "text": s.text,
             "words": [{"s": w.start + offset, "e": w.end + offset, "w": w.word} for w in s.words]}
            for s in segs]

segs = run(audio)
# Whisperはときどき一部（特に冒頭）を飛ばすので、5秒以上の空白は区間だけもう一度文字起こしする
dur = len(audio) / SR
edges = [0.0] + [x for s in segs for x in (s["start"], s["end"])] + [dur]
fill = []
for a, b in zip(edges[0::2], edges[1::2]):
    if b - a > 5:
        fill += [s for s in run(audio[int(a*SR):int(b*SR)], a) if s["start"] >= a - 0.1 and s["end"] <= b + 0.1]
segs = sorted(segs + fill, key=lambda s: s["start"])
for s in segs: print(f"{s['start']:6.2f}-{s['end']:6.2f} {s['text']}")
json.dump(segs, open(out_path, "w"), ensure_ascii=False, indent=1)
