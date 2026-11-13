# 使い方: python3 build.py 台本.txt 文字起こし.json[,追加.json] 出力フォルダ [再生速度=1.1] [--audio 動画.mp4]
#   再生速度：CapCutで動画全体を速くする倍率。字幕の時間をそれに合わせて縮める
#   --audio：元の動画を渡すと、テロップの出始めを実際に声が出た瞬間に合わせる（おすすめ）
# 台本（種類つき）＋文字起こし → 種類ごとのSRT、ふりがなSRT、手直しメモ（色・ふりがなの場所）、プレビュー用JSON
import json, re, sys, difflib, os, subprocess
args = sys.argv[1:]
AUDIO = None
if '--audio' in args:
    k = args.index('--audio'); AUDIO = args[k+1]; del args[k:k+2]
script, jsons, outdir = args[0], args[1].split(','), args[2]
SPEED = float(args[3]) if len(args) > 3 else 1.1
os.makedirs(outdir, exist_ok=True)
PUNCT = set('、。，,.!?！？ 　「」ー〜~＝=/:：')

# 音の大きさから「無音→声」に変わる瞬間（話し始め）を探しておく
onsets, pauses = [], []
if AUDIO:
    import numpy as np
    pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', AUDIO, '-ac', '1', '-ar', '16000', '-f', 's16le', '-'],
                         capture_output=True, check=True).stdout
    au = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
    n = len(au) // 160                       # 10ミリ秒ごとの音の大きさ
    db = 20 * np.log10(np.sqrt((au[:n*160].reshape(n, 160) ** 2).mean(1)) + 1e-9)
    on = db > db.max() - 38                  # 一番大きい声より38dB以上小さければ無音
    # 0.08秒以上の無音のあとに、0.05秒以上声が続く所＝話し始め
    onsets = [j / 100 for j in range(8, n - 5) if on[j:j+5].all() and not on[j-8:j].any()]
    # 0.3秒以上の「間」の（始まり, 終わり＝話し始め）
    pauses, j = [], 0
    while j < n:
        if not on[j]:
            k = j
            while k < n and not on[k]: k += 1
            # 間のすぐあとの小さな音（息など）は飛ばして、声が0.05秒続く所を話し始めにする
            st = next((x for x in range(k, min(k + 20, n - 5)) if on[x:x+5].all()), None)
            if k - j >= 30 and st is not None: pauses.append((j / 100, st / 100))
            j = k
        else: j += 1
def silent_at(s):
    return bool(AUDIO) and 0 <= int(s * 100) < n and not on[int(s * 100)]
def onset_after(s, upto=0.6):
    # テロップの出始めのすぐ近くで「間」が始まっていれば、間の終わり（1.3秒先まで）に合わせる
    # （Whisperは間の時間を前の言葉にくっつけて記録することがある）
    p = next((b for a, b in pauses if a <= s + 0.3 and s - 0.05 < b <= s + 1.3), None)
    if p is not None: return p
    return next((x for x in onsets if s - 0.05 < x <= s + upto), None)

# 台本でひらがなにした言葉を、文字起こし側もひらがなにして時間合わせできるようにする
ALIASES = {'可愛': 'かわい', '子供': '子ども', 'カミ': '紙', 'はぁー': 'へー', 'ふぅぅぅぅぅぅ': 'うーん', 'えっ': 'え'}
def ALIAS(s):
    for k, v in ALIASES.items(): s = s.replace(k, v)
    return s
chars = []
for jp in jsons:
    for seg in json.load(open(jp)):
        # Whisperは間（ま）のあとのまとまりを、まるごと0.3〜0.5秒早く記録しがち → 実際の話し始めに合わせてずらす
        o = onset_after(seg['start']) if seg['words'] else None
        shift = (o - seg['start']) if o is not None and o > seg['start'] else 0.0
        for w in seg['words']:
            w = dict(w, s=w['s'] + shift, e=w['e'] + shift)
            if w['e'] - w['s'] < 0.001: continue   # 長さ0の言葉はWhisperの繰り返し（作文）なので使わない
            t = [c for c in ALIAS(w['w']) if c not in PUNCT]
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
    # 行の最後に「 @73.9」と書くと、その秒（元の動画の時間）から出す（ため息など、文字起こしと合わない声用）
    m = re.search(r'\s@(\d+(?:\.\d+)?)$', body)
    at = float(m.group(1)) if m else None
    if m: body = body[:m.start()]
    items.append({'kind': kind, 'lines': parse(body) if body else [], 'body': body, 'at': at})
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
for i in speech:
    it = items[i]
    if it['at'] is not None:
        d = it['e'] - it['s'] if 's' in it else 0.8
        it['s'], it['e'] = it['at'], it['at'] + max(d, 0.8)
prev_e = 0.0
for i in speech:
    it = items[i]
    if 's' not in it: it['s'] = prev_e; it['e'] = prev_e + 0.8
    prev_e = it['e']

# まとまりの途中にあるテロップも、出始めの少しあとに話し始めがあれば合わせる
sp = [items[i] for i in speech]
for k, it in enumerate(sp):
    nxt = sp[k+1]['s'] if k + 1 < len(sp) else 1e9
    # 出始めの時点がまだ無音（話の途中の間）なら、少し遠くまで話し始めを探す
    o = onset_after(it['s'], 1.2 if silent_at(it['s']) else 0.6)
    if o is not None and o < nxt - 0.2 and o < it['e']: it['s'] = o

def next_speech_start(i):
    for j in range(i+1, len(items)):
        if 's' in items[j] and items[j]['kind'] not in ('B+','B-'): return items[j]['s']
    return None

# 表示の終わり：次のセリフの頭まで（1秒以上あいたら消す）
for i in speech:
    it = items[i]; n = next_speech_start(i)
    it['end'] = n if (n is not None and n - it['e'] < 1.0) else it['e'] + 0.3

# キーワード(B)の期間と、胸元(C)の積み重ね
caps = {'A': [], 'B': [], 'CY': [], 'CK': [], 'D': [], 'H': [], 'S': []}
b_open = None; c_stack = None
for i, it in enumerate(items):
    k = it['kind']
    if k == 'B+':
        b_open = {'lines': it['lines'], 'text': it['text'], 'first': None, 'last': None}
    elif k == 'B-':
        bs, be = items[b_open['first']]['s'], items[b_open['last']]['end']
        caps['B'].append({'s': bs, 'e': be, 'lines': b_open['lines'], 'text': b_open['text']})
        # Bが消えるまで、最後に出た胸元のテロップだけ残す（前に出ていたものは延ばさない）
        last_c = max((caps[c][-1] for c in ('CY', 'CK') if caps[c]), key=lambda x: x['s'], default=None)
        if last_c and last_c['s'] >= bs - 0.01 and last_c['e'] >= items[b_open['last']]['s'] - 0.01: last_c['e'] = be   # このBの間に出たものだけ
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

# 短すぎて読めないテロップ（「じゃあ」など）は、前のテロップから時間をもらって0.5秒は出す。
# 前から足りなければ、次のテロップの出始めを最大0.3秒遅らせる
MIN_SHOW = 0.5
for k in caps:
    lst = caps[k]
    for i, cur in enumerate(lst):
        lack = MIN_SHOW - (cur['e'] - cur['s'])
        if lack <= 0: continue
        prev = lst[i-1] if i > 0 else None
        if prev and abs(prev['e'] - cur['s']) < 0.01:
            take = min(lack, max(0, prev['e'] - prev['s'] - 1.0))
            cur['s'] -= take; prev['e'] = cur['s']; lack -= take
        nxt = lst[i+1] if i + 1 < len(lst) else None
        if lack > 0 and nxt and abs(nxt['s'] - cur['e']) < 0.01:
            take = min(lack, 0.3, max(0, nxt['e'] - nxt['s'] - 1.0))
            cur['e'] += take; nxt['s'] = cur['e']

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

names = {'A': 'A_上_通常', 'B': 'B_上_キーワード', 'CY': 'C_胸元_黄色', 'CK': 'C_胸元_黒', 'D': 'D_締め',
         'H': '本人_下_オレンジ', 'S': 'スタッフ_下_水色'}   # H・Sは横動画用
for k, nm in names.items():
    write_srt(f"{outdir}/{nm}.srt", [(c['s'], c['e'], c['text']) for c in caps[k]])
# ふりがな（全角スペースで位置合わせ。CapCutでずれたら依頼者が調整する。手直しメモにも一覧を書く）
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
    f.write("\n\nふりがなを付ける場所\n\n")
    rows = []
    for k in ('A', 'B', 'CY', 'CK', 'D', 'H', 'S'):
        for c in caps[k]:
            for l in c['lines']:
                for b, r, _ in l:
                    if r: rows.append((c['s'], f"{ts(c['s'])[3:8]}  [{names[k]}] 「{c['text'].replace(chr(10),'')}」の「{b}」→ {r}\n"))
    for _, r in sorted(rows): f.write(r)
json.dump(caps, open(f"{outdir}/caps.json", 'w'), ensure_ascii=False, indent=1)
for k in caps:
    for c in caps[k]: print(f"{k:2} {c['s']:6.2f}-{c['e']:6.2f} {c['text']!r}")
