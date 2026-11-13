# テロップの出始めが、実際の話し始めより遅すぎないかを調べる（確認用。早すぎは check_timing.py）
# 使い方: python3 check_late.py caps.json 音声 [再生速度=1.1] [許す遅れ=0.25]
# テロップの出始め（0.1秒の遅らせを戻した時間）の直前に「間→声」の切り替わりがあり、
# そこから声が途切れずに続いているなら、その切り替わりが本当の話し始め。差が大きければ遅い。
import sys, json, subprocess
import numpy as np
caps, src = json.load(open(sys.argv[1])), sys.argv[2]
SPEED = float(sys.argv[3]) if len(sys.argv) > 3 else 1.1
LIM = float(sys.argv[4]) if len(sys.argv) > 4 else 0.25
pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-ac', '1', '-ar', '16000', '-f', 's16le', '-'],
                     capture_output=True, check=True).stdout
au = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
n = len(au) // 160
db = 20 * np.log10(np.sqrt((au[:n*160].reshape(n, 160) ** 2).mean(1)) + 1e-9)
on = db > db.max() - 38
allc = sorted((c['s'], k, c['text'], c.get('voice_e')) for k in caps for c in caps[k])
late = []
for i, (s, k, t, _) in enumerate(allc):
    f = int((s - 0.1) * SPEED * 100)
    prev_s = int((allc[i-1][0] - 0.1) * SPEED * 100) if i else 0
    if f >= n or not on[min(f, n-1)]: continue      # 出始めが無音なら遅れではない
    j = f
    while j > prev_s and (on[j-1] or on[max(j-8, 0):j].any()): j -= 1   # 0.08秒未満の切れ目は声が続いているとみなす
    # 切り替わりの前に0.12秒以上の間がある＝本当の話し始め（話し続けている途中の区切りは対象外）
    # 前のテロップの声がまだ続いている所の区切りは、音だけでは判断できないので対象外
    pe = allc[i-1][3] if i else None
    if pe is not None and j / 100 < pe - 0.05: continue
    if j > prev_s and not on[max(j-12, 0):j].any() and (f - j) / 100 > LIM: late.append((round(s, 2), round((f - j) / 100, 2), k, t))
print(f"{len(allc)}個中 {len(late)}個が、話し始めより{LIM}秒以上遅い")
for x in late: print(x)
