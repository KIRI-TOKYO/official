# テロップの出始めが、その言葉を話し始めた時間（区切り文字起こし）とずれていないかを調べる（確認用）
# 使い方: python3 check_words.py caps.json 区切り.json [再生速度=1.1] [許すずれ=0.25]
# 早すぎ・遅すぎの両方を出す。話の途中で区切ったテロップは音だけでは判断できないので、こちらで確認する
import sys, json
caps, chunks = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
SPEED = float(sys.argv[3]) if len(sys.argv) > 3 else 1.1
LIM = float(sys.argv[4]) if len(sys.argv) > 4 else 0.25
SKIP = set('、。，,.!?！？ 　「」ー〜~＝=/:：・\n…')
chars = []
for seg in chunks:
    for w in seg['words']:
        t = [x for x in w['w'] if x not in SKIP]
        for i, x in enumerate(t): chars.append((x, w['s'] + i * (w['e'] - w['s']) / len(t)))
txt = ''.join(x for x, _ in chars)
allc = sorted((c['s'], k, c['text']) for k in caps for c in caps[k])
bad = []
for s, k, t in allc:
    raw = (s - 0.1) * SPEED                      # 0.1秒の遅らせと速度を戻した、元の動画での時間
    key = ''.join(ch for ch in t if ch not in SKIP)[:3]
    hits = [chars[i][1] for i in range(len(chars)) if txt.startswith(key, i) and abs(chars[i][1] - raw) < 3]
    if not hits: continue
    w = min(hits, key=lambda h: abs(h - raw))
    if abs(w - raw) >= LIM: bad.append((round(s, 2), round(raw - w, 2), k, t.replace('\n', '')))
print(f"{len(allc)}個中 {len(bad)}個が、話し始めと{LIM}秒以上ずれている（＋は遅い、－は早い）")
for b in bad: print(b)
