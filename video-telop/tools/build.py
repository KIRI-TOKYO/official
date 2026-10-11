# 使い方: python3 build.py 台本.txt 文字起こし.json[,追加.json] 出力フォルダ [再生速度=1.1]
#   再生速度：CapCutで動画全体を速くする倍率。字幕の時間をそれに合わせて縮める
# 台本（種類つき）＋文字起こし → 種類ごとのSRT、ふりがなSRT、手直しメモ、プレビュー用JSON
import json, re, sys, difflib, os
script, jsons, outdir = sys.argv[1], sys.argv[2].split(','), sys.argv[3]
SPEED = float(sys.argv[4]) if len(sys.argv) > 4 else 1.1
os.makedirs(outdir, exist_ok=True)
PUNCT = set('、。，,.!?！？ 　「」ー〜~＝=/:：')

chars = []
for jp in jsons:
    for seg in json.load(open(jp)):
        for w in seg['words']:
            if w['e'] - w['s'] < 0.001: continue   # 長さ0の言葉はWhisperの繰り返し（作文）なので使わない
            t = [c for c in w['w'] if c not in PUNCT]
            if not t: continue
            d = (w['e'] - w['s']) / len(t)
            for i, c in enumerate(t): chars.append((c, w['s']+i*d, w['s']+(i+1)*d))
chars.sort(key=lambda x: x[1])

TOK = re.compile(r'\[\[|\]\]|\(\(|\)\)|\{[^|}]+\|[^}]+\}|/|[^\[\]\(\){/]+|.')
def parse(text):
    """-> 行のリスト。各行は [(文字, ふりがな, 色)]  色: None/'red'/'yellow'"""
    lines, cur, color = [], [], None
    for t in TOK.findall(text):
        if t == '[[': color = 'red'
        elif t == '((': color = 'yellow'
        elif t in (']]', '))'): color = None
        elif t == '/': lines.append(cur); cur = []
        elif t.startswith('{'):
            b, r = t[1:-1].split('|'); cur.append((b, r, color))
        else: cur.append((t, None, color))
    lines.append(cur); return lines
plain = lambda lines: '\n'.join(''.join(b for b,_,_ in l) for l in lines)

items = []   # {'kind', 'lines', 'text'}
for raw in open(script, encoding='utf-8'):
    raw = raw.rstrip('\n')
    if not raw.strip(): continue
    kind, _, body = raw.partition(' ')
    items.append({'kind': kind, 'lines': parse(body) if body else [], 'body': body})
    items[-1]['text'] = plain(items[-1]['lines'])

# 音声に対応する行（A, C*, D, -）だけ時間合わせ
speech = [i for i, it in enumerate(items) if it['kind'] not in ('B+', 'B-')]
flat, owner = [], []
for i in speech:
    for c in items[i]['text']:
        if c not in PUNCT and c != '\n': flat.append(c); owner.append(i)
sm = difflib.SequenceMatcher(None, flat, [c for c,_,_ in chars], autojunk=False)
for a, b, n in sm.get_matching_blocks():
    for k in range(n):
        it = items[owner[a+k]]; _, s, e = chars[b+k]
        it['s'] = min(it.get('s', s), s); it['e'] = max(it.get('e', e), e)
prev_e = 0.0
for i in speech:
    it = items[i]
    if 's' not in it: it['s'] = prev_e; it['e'] = prev_e + 0.8
    prev_e = it['e']

def next_speech_start(i):
    for j in range(i+1, len(items)):
        if 's' in items[j] and items[j]['kind'] not in ('B+','B-'): return items[j]['s']
    return None

# 表示の終わり：次のセリフの頭まで（1秒以上あいたら消す）
for i in speech:
    it = items[i]; n = next_speech_start(i)
    it['end'] = n if (n is not None and n - it['e'] < 1.0) else it['e'] + 0.3

# キーワード(B)の期間と、胸元(C)の積み重ね
caps = {'A': [], 'B': [], 'CY': [], 'CK': [], 'D': []}
b_open = None; c_stack = None
for i, it in enumerate(items):
    k = it['kind']
    if k == 'B+':
        b_open = {'lines': it['lines'], 'text': it['text'], 'first': None, 'last': None}
    elif k == 'B-':
        bs, be = items[b_open['first']]['s'], items[b_open['last']]['end']
        caps['B'].append({'s': bs, 'e': be, 'lines': b_open['lines'], 'text': b_open['text']})
        for c in ('CY', 'CK'):   # Bが消えるまで胸元は残す
            if caps[c] and caps[c][-1]['e'] >= items[b_open['last']]['s'] - 0.01: caps[c][-1]['e'] = be
        b_open = None
    else:
        if b_open is not None:
            if b_open['first'] is None: b_open['first'] = i
            b_open['last'] = i
        if k == '-': continue
        if k == 'CY+':
            p = caps['CY'][-1]; p['e'] = it['s']
            caps['CY'].append({'s': it['s'], 'e': it['end'], 'lines': p['lines'] + it['lines'],
                               'text': p['text'] + '\n' + it['text']})
        else:
            if k in ('CY', 'CK'):   # 胸元は1か所なので、新しいものが出たら前のものは消す
                for c in ('CY', 'CK'):
                    if caps[c] and caps[c][-1]['e'] > it['s']: caps[c][-1]['e'] = it['s']
            caps[k].append({'s': it['s'], 'e': it['end'], 'lines': it['lines'], 'text': it['text']})

# 文字起こしの時間は実際の声より少し早く出るので、全体を遅らせる（依頼者の確認で0.1秒）
DELAY = 0.1
for k in caps:
    for c in caps[k]: c['s'] = c['s'] / SPEED + DELAY; c['e'] = c['e'] / SPEED + DELAY

def ts(t):
    ms = int(round(t*1000)); return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"
def write_srt(path, entries):
    if not entries: return
    with open(path, 'w', encoding='utf-8') as f:
        for n, (s, e, t) in enumerate(entries, 1): f.write(f"{n}\n{ts(s)} --> {ts(e)}\n{t}\n\n")

W = lambda s: sum(1 if ord(c) < 0x2000 else 2 for c in s)   # 半角は1マス、全角は2マス
def ruby_row(line):   # 全角スペースで位置合わせ（1マス＝ふりがな1文字＝本文の半分）
    total = sum(W(b) for b,_,_ in line); pos = 0; placed = []
    for b, r, _ in line:
        if r: placed.append([pos + (W(b) - len(r))//2, r])
        pos += W(b)
    out = ''; cur = 0
    for p in placed:
        s = max(p[0], cur, 0); out += '　'*(s-cur) + p[1]; cur = s + len(p[1])
    return out + '　'*max(0, total-cur) if placed else '　'*total
def ruby_text(lines):
    if not any(r for l in lines for _,r,_ in l): return None
    return '\n'.join(ruby_row(l) for l in lines)

names = {'A': 'A_上_通常', 'B': 'B_上_キーワード', 'CY': 'C_胸元_黄色', 'CK': 'C_胸元_黒', 'D': 'D_締め'}
for k, nm in names.items():
    write_srt(f"{outdir}/{nm}.srt", [(c['s'], c['e'], c['text']) for c in caps[k]])
for k, nm in (('A', 'ふりがな_A_上'), ('B', 'ふりがな_B_キーワード')):
    write_srt(f"{outdir}/{nm}.srt", [(c['s'], c['e'], r) for c in caps[k] if (r := ruby_text(c['lines']))])
cc = sorted(caps['CY'] + caps['CK'], key=lambda c: c['s'])
write_srt(f"{outdir}/ふりがな_C_胸元.srt", [(c['s'], c['e'], r) for c in cc if (r := ruby_text(c['lines']))])

with open(f"{outdir}/手直しメモ.txt", 'w', encoding='utf-8') as f:
    f.write("CapCutで文字の一部だけ色を変える場所\n\n")
    rows = []
    for k in ('A', 'B', 'CY', 'CK'):
        for c in caps[k]:
            for l in c['lines']:
                runs = []
                for b, _, col in l:
                    if col and runs and runs[-1][1] == col and runs[-1][2]: runs[-1][0] += b
                    else: runs.append([b, col, bool(col)])
                for b, col, _ in runs:
                    if col: rows.append((c['s'], f"{ts(c['s'])[3:8]}  [{names[k]}] 「{c['text'].replace(chr(10),'')}」の「{b}」→ {'赤' if col=='red' else '黄色'}\n"))
    for _, r in sorted(rows): f.write(r)
json.dump(caps, open(f"{outdir}/caps.json", 'w'), ensure_ascii=False, indent=1)
for k in caps:
    for c in caps[k]: print(f"{k:2} {c['s']:6.2f}-{c['e']:6.2f} {c['text']!r}")
