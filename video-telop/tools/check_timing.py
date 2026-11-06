# テロップの出始めが、実際の声より早すぎないかを調べる（確認用）
# 使い方: python3 check_timing.py caps.json 動画.mp4 [再生速度=1.1]
import sys, json, subprocess
import numpy as np
caps, video = json.load(open(sys.argv[1])), sys.argv[2]
SPEED = float(sys.argv[3]) if len(sys.argv) > 3 else 1.1
pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', video, '-ac', '1', '-ar', '16000', '-f', 's16le', '-'],
                     capture_output=True, check=True).stdout
au = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
n = len(au) // 160
db = 20 * np.log10(np.sqrt((au[:n*160].reshape(n, 160) ** 2).mean(1)) + 1e-9)
on = db > db.max() - 38
allc = sorted((c['s'], k, c['text']) for k in caps for c in caps[k])
early = []
for s, k, t in allc:
    f = int((s - 0.1) * SPEED * 100)   # 0.1秒の遅らせと速度を戻した、元の動画での時間
    if f < n and not on[f]:
        j = next((x for x in range(f, min(f + 100, n)) if on[x:x+5].all()), None)
        if j is not None and j - f >= 15: early.append((round(s, 2), round((j - f) / 100, 2), k, t))
print(f"{len(allc)}個中 {len(early)}個が、声より0.15秒以上早い")
for e in early: print(e)
