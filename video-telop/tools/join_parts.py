# 分割して送られた動画をつなげる。つなぎ目で重なっている部分は音を比べて取り除く
# 使い方: python3 join_parts.py 出力.mp4 1.mov 2.mov 3.mov ...
import sys, subprocess
import numpy as np
out, parts = sys.argv[1], sys.argv[2:]
SR = 8000
def pcm(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32)
def dur(p):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p],
                                capture_output=True, text=True, check=True).stdout)

starts = [0.0]   # 各パーツの先頭を何秒から使うか
for a, b in zip(parts, parts[1:]):
    A, B = pcm(a), pcm(b)
    tail, head = A[-SR*15:], B[:SR*3]            # 前のパーツの最後15秒の中に、次のパーツの最初3秒があるか探す
    if np.abs(head).max() < 50:
        starts.append(0.0); continue
    best, best_k = -1, 0
    for k in range(0, len(tail) - len(head), 40):
        seg = tail[k:k+len(head)]
        c = float(np.dot(seg, head) / (np.linalg.norm(seg) * np.linalg.norm(head) + 1e-9))
        if c > best: best, best_k = c, k
    overlap = (len(tail) - best_k) / SR if best > 0.8 else 0.0
    print(f"{b}: 前と {overlap:.2f}秒 重なり（一致度 {best:.2f}）")
    starts.append(overlap)

inputs, f = [], ''
for i, (p, s) in enumerate(zip(parts, starts)):
    inputs += ['-i', p]
    f += f"[{i}:v]trim=start={s:.3f},setpts=PTS-STARTPTS,fps=30[v{i}];[{i}:a]atrim=start={s:.3f},asetpts=PTS-STARTPTS[a{i}];"
f += ''.join(f"[v{i}][a{i}]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=1:a=1[v][a]"
subprocess.run(['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex', f, '-map', '[v]', '-map', '[a]',
                '-c:v', 'libx264', '-crf', '23', '-preset', 'veryfast', '-c:a', 'aac', '-b:a', '160k', out], check=True)
print(f"つなげた長さ: {dur(out):.2f}秒")
