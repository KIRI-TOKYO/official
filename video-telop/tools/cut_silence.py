# 無言が続くところをカットした動画を作る
# 使い方: python3 cut_silence.py 元動画.mp4 出力.mp4 [無言の長さ(秒)=1.0] [前後に残す余白(秒)=0.15]
import sys, re, subprocess
src, out = sys.argv[1], sys.argv[2]
MIN_SIL = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
PAD = float(sys.argv[4]) if len(sys.argv) > 4 else 0.15
NOISE = '-35dB'   # これより小さい音は「無言」とみなす

dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src],
                           capture_output=True, text=True, check=True).stdout)
log = subprocess.run(['ffmpeg', '-i', src, '-af', f'silencedetect=noise={NOISE}:d={MIN_SIL}', '-f', 'null', '-'],
                     capture_output=True, text=True).stderr
starts = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', log)]
ends = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', log)]
ends += [dur] * (len(starts) - len(ends))

# 残す区間を作る（無言の前後に少し余白を残すと、ぶつ切りに聞こえにくい）
keep, t = [], 0.0
for s, e in zip(starts, ends):
    cut_s, cut_e = (s + PAD if s > 0 else 0.0), (e - PAD if e < dur else dur)
    if cut_e - cut_s < 0.3: continue
    if cut_s > t: keep.append((t, cut_s))
    t = cut_e
if t < dur: keep.append((t, dur))

removed = dur - sum(b - a for a, b in keep)
print(f"元の長さ {dur:.1f}秒 → カット後 {dur - removed:.1f}秒（{removed:.1f}秒カット、{len(keep) - 1}か所）")
for (a1, b1), (a2, _) in zip(keep, keep[1:]): print(f"  カット: {b1:6.2f}秒 〜 {a2:6.2f}秒（{a2 - b1:.1f}秒）")

parts = ''.join(f"[0:v]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS[v{i}];[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS[a{i}];"
                for i, (a, b) in enumerate(keep))
parts += ''.join(f"[v{i}][a{i}]" for i in range(len(keep))) + f"concat=n={len(keep)}:v=1:a=1[v][a]"
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-filter_complex', parts, '-map', '[v]', '-map', '[a]',
                '-c:v', 'libx264', '-crf', '17', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k', out], check=True)
