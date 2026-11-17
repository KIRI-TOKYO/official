# 台本の文字と音声を直接対応させて（強制アラインメント）、文字ごとの時間を出す
# 使い方: python3 align.py 台本.txt 動画.mp4 出力.json
# 出力は transcribe_chunks.py と同じ形なので、そのまま build.py に渡せる。
# Whisperの文字起こしは言葉の時間が0.3〜0.6秒早めに出ることがあり、音だけで直すのにも限界があった。
# こちらは「何を話しているか（台本）」がわかっている前提で、音の中の位置を探すので時間が正確。
import sys, re, json, subprocess
import numpy as np, torch, torchaudio
import pykakasi
from torchaudio.pipelines import MMS_FA as bundle

script, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
SR = bundle.sample_rate
RUBY = re.compile(r'\{([^|}]+)\|([^}]+)\}')
LETTERS = {'A': 'ei', 'B': 'bii', 'C': 'shii', 'D': 'dii', 'E': 'ii', 'F': 'efu', 'G': 'jii', 'H': 'eichi', 'I': 'ai',
           'J': 'jei', 'K': 'kei', 'L': 'eru', 'M': 'emu', 'N': 'enu', 'O': 'oo', 'P': 'pii', 'Q': 'kyuu', 'R': 'aaru',
           'S': 'esu', 'T': 'tii', 'U': 'yuu', 'V': 'bui', 'W': 'daburyuu', 'X': 'ekkusu', 'Y': 'wai', 'Z': 'zetto'}
DIG = ['', 'ichi', 'ni', 'san', 'yon', 'go', 'roku', 'nana', 'hachi', 'kyuu']
def num_romaji(s):
    v = int(s)
    if v == 0: return 'zero'
    out = ''
    for unit, name in ((10000, 'man'), (1000, 'sen'), (100, 'hyaku'), (10, 'juu')):
        q, v = divmod(v, unit)
        if q: out += ('' if q == 1 and unit < 10000 else DIG[q]) + name
    return out + DIG[v]

# 台本から、話す行の文字（ふりがなは読みに使う）を取り出す
kks = pykakasi.kakasi()
items = []
for raw in open(script, encoding='utf-8'):
    raw = raw.rstrip('\n')
    if not raw.strip(): continue
    kind, _, body = raw.partition(' ')
    if kind in ('B+', 'B-') or not body: continue
    body = re.sub(r'\s@[\d.]+(-[\d.]+)?$', '', body)
    body = body.replace('[[', '').replace(']]', '').replace('((', '').replace('))', '').replace('/', '')
    units = []          # (台本の文字, 読みのローマ字)
    pos = 0
    for m in list(RUBY.finditer(body)) + [None]:
        plain = body[pos:m.start()] if m else body[pos:]
        for tok in kks.convert(plain) if plain else []:
            o = tok['orig']
            if re.fullmatch(r'\d+', o): units.append((o, num_romaji(o)))
            elif re.fullmatch(r'[A-Z]+', o): units.append((o, ''.join(LETTERS[c] for c in o)))
            else: units.append((o, tok['hepburn']))
        if m:
            units.append((m.group(1), kks.convert(m.group(2))[0]['hepburn'] if m.group(2) else ''))
            pos = m.end()
    clean = [(o, re.sub(r'[^a-z]', '', r.lower())) for o, r in units]
    items.append([u for u in clean if u[0].strip()])

# 音声
pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'],
                     capture_output=True, check=True).stdout
wave = torch.from_numpy(np.frombuffer(pcm, np.int16).astype(np.float32) / 32768).unsqueeze(0)
model = bundle.get_model(with_star=True)
DICT = bundle.get_dict(star='*')
with torch.inference_mode():
    em = []
    step = SR * 30                                 # 30秒ずつ計算してつなげる（メモリ節約）
    for a in range(0, wave.shape[1], step):
        e, _ = model(wave[:, a:a + step]); em.append(e)
    emission = torch.cat(em, dim=1)
ratio = wave.shape[1] / emission.shape[1] / SR     # 1フレームの秒数

# 読みを1列に並べる。行と行の間、言葉と言葉の間に「*」（台本にない声：はい、えー など）を入れる
tokens, owner = [], []          # owner: (行, 言葉) / None は「*」
for li, units in enumerate(items):
    for ui, (o, r) in enumerate(units):
        if not r: continue
        tokens.append(DICT['*']); owner.append(None)
        for ch in r:
            if ch in DICT: tokens.append(DICT[ch]); owner.append((li, ui))
tokens.append(DICT['*']); owner.append(None)
ali, scores = torchaudio.functional.forced_align(emission, torch.tensor([tokens], dtype=torch.int32), blank=0)
ali = ali[0].tolist()
# フレームごとの記号 → 記号ごとの時間（同じ記号が続く所をまとめる）
spans, ti, prev = [], -1, 0
for f, tok in enumerate(ali):
    if tok != 0 and (tok != prev or (ti + 1 < len(tokens) and tokens[ti + 1] == tok and f > 0 and ali[f-1] == 0)):
        ti += 1; spans.append([f, f + 1])
    elif tok != 0: spans[-1][1] = f + 1
    prev = tok
times = {}
for (a, b), ow in zip(spans, owner):
    if ow is None: continue
    s, e = a * ratio, b * ratio
    if ow in times: times[ow][1] = e
    else: times[ow] = [s, e]

segs = []
for li, units in enumerate(items):
    words = []
    for ui, (o, r) in enumerate(units):
        if (li, ui) not in times: continue
        s, e = times[(li, ui)]
        d = (e - s) / len(o)
        for k, ch in enumerate(o): words.append({'s': s + k * d, 'e': s + (k + 1) * d, 'w': ch})
    if words:
        segs.append({'start': words[0]['s'], 'end': words[-1]['e'], 'text': ''.join(w['w'] for w in words), 'words': words, 'aligned': True})
        print(f"{words[0]['s']:7.2f}-{words[-1]['e']:7.2f} {segs[-1]['text']}")
json.dump(segs, open(out, 'w'), ensure_ascii=False, indent=1)
