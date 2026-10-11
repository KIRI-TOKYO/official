# 仕上がり確認用のプレビュー動画を作る（CapCutでは使わない）
# 使い方: python3 preview.py caps.json 動画.mp4 出力.mp4 [--compare]
#   --compare: 左に元動画、右にぼかした動画＋テロップ（テロップ入りの完成動画と比べるとき）
import json, sys, os, subprocess
from PIL import Image, ImageDraw, ImageFont
caps = json.load(open(sys.argv[1])); video, out = sys.argv[2], sys.argv[3]
compare = '--compare' in sys.argv
W, H = 720, 1280
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fonts')
BOLD, BLACK = f'{FONTS}/ZenMaruGothic-Bold.ttf', f'{FONTS}/ZenMaruGothic-Black.ttf'
THIN = f'{FONTS}/ZenMaruGothic-Regular.ttf'   # ふりがなは細字（太いとつぶれて読みにくい）
F = lambda p, s: ImageFont.truetype(p, s)
RED, YEL, ORG = (232, 32, 42), (255, 230, 0), (255, 138, 0)
STY = {  # 本文サイズ, ふりがなサイズ, 中心y, 箱, 文字色, フチ色, フチ幅, フォント
 'A':  (50, 22, 175, True,  (20,20,20), None, 0, BOLD),
 'CK': (48, 21, 930, True,  (20,20,20), None, 0, BOLD),
 'CY': (48, 21, 930, True,  YEL, (20,20,20), 4, BLACK),
 'B':  (88, 30, 175, False, RED, (255,255,255), 9, BLACK),
 'D':  (72, 0, 175, False, ORG, (255,255,255), 8, BLACK),
}
def draw_cap(img, kind, lines):
    fs, rs, cy, box, col, sc, sw, fp = STY[kind]
    d = ImageDraw.Draw(img)
    while True:
        font, rfont = F(fp, fs), F(THIN, max(rs, 10))
        widths = [d.textlength(''.join(b for b,_,_ in l), font=font) for l in lines]
        if max(widths) <= W - 80 or fs < 20: break
        fs = int(fs*0.92); rs = int(rs*0.92)
    has_r = [any(r for _,r,_ in l) for l in lines]
    rows_h = [fs + (rs+4 if hr else 0) for hr in has_r]
    gap = 10; total = sum(rows_h) + gap*(len(lines)-1)
    y = cy - total/2
    if box:
        bw = max(widths)
        d.rounded_rectangle([(W-bw)/2-24, y-14, (W+bw)/2+24, y+total+24], radius=16, fill=(255,255,255,240))
    for l, w, hr, rh in zip(lines, widths, has_r, rows_h):
        x = (W - w)/2; ty = y + (rs+4 if hr else 0)
        for b, r, c in l:
            bw = d.textlength(b, font=font)
            fc = RED if c == 'red' else YEL if c == 'yellow' else col
            fsc = (20,20,20) if c == 'yellow' else sc
            fsw = 5 if c == 'yellow' else sw
            d.text((x, ty), b, font=font, fill=fc, stroke_width=fsw, stroke_fill=fsc)
            if r:
                rw = d.textlength(r, font=rfont)
                d.text((x+(bw-rw)/2, ty-rs-4), r, font=rfont, fill=fc if kind != 'CY' else (20,20,20),
                       stroke_width=(2 if fsw else 0), stroke_fill=fsc if kind != 'CY' else None)
            x += bw
        y += rh + gap
tmp = os.path.dirname(out) + '/frames2'; os.makedirs(tmp, exist_ok=True)
allc = [(k, c) for k in caps for c in caps[k]]
cuts = sorted({0.0} | {round(c['s'],3) for _,c in allc} | {round(c['e'],3) for _,c in allc})
lst = []
for i, t0 in enumerate(cuts):
    t1 = cuts[i+1] if i+1 < len(cuts) else t0 + 5
    img = Image.new('RGBA', (W, H), (0,0,0,0))
    for k, c in allc:
        if c['s'] <= t0 + 0.001 and c['e'] > t0 + 0.001: draw_cap(img, k, c['lines'])
    p = f'{i:04d}.png'; img.save(f'{tmp}/{p}'); lst.append((p, t1 - t0))
with open(f'{tmp}/list.txt', 'w') as f:
    for p, d in lst: f.write(f"file '{p}'\nduration {d:.3f}\n")
    f.write(f"file '{lst[-1][0]}'\n")
font = BLACK
fc = "[1:v]format=rgba[o];[0:v][o]overlay=0:0:shortest=1[v]" if not compare else (f"[0:v]split[a][b];[b]boxblur=18:2[bl];[1:v]format=rgba[o];[bl][o]overlay=0:0:shortest=1,"
      f"drawtext=fontfile={font}:text='Claude版':x=20:y=20:fontsize=36:fontcolor=white:box=1:boxcolor=black@0.6[r];"
      f"[a]drawtext=fontfile={font}:text='お手本':x=20:y=20:fontsize=36:fontcolor=white:box=1:boxcolor=black@0.6[l];"
      f"[l][r]hstack[v]")
subprocess.run(['ffmpeg','-v','error','-y','-i',video,'-f','concat','-safe','0','-i',f'{tmp}/list.txt',
  '-filter_complex',fc,'-map','[v]','-map','0:a','-c:v','libx264','-crf','28','-preset','veryfast','-c:a','copy',out], check=True)
