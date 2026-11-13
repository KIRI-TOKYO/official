# ショート動画 テロップ作成ツール

KIRI TOKYO にほんご のショート動画用に、CapCut Pro に読み込める字幕ファイル（.srt）を作るためのフォルダです。
公式サイト（`docs/`）とは関係ありません。

## 流れ

1. テロップを入れる前の動画をClaudeに渡す
2. Claudeが文字起こしをする（`tools/transcribe.py`）
3. Claudeが [テロップルール.md](テロップルール.md) に沿って「台本.txt」を書く（区切り・変換の修正・ふりがな・色・位置）
4. 台本と文字起こしから、種類ごとの字幕ファイルを作る（`tools/build.py`）
5. 仕上がり確認用のプレビュー動画を作る（`tools/preview.py`）
6. CapCutで字幕ファイルを読み込み、種類ごとに見た目を1回設定して「すべてに適用」

## できあがるファイル

| ファイル | CapCutでの見た目 |
|---|---|
| A_上_通常.srt | 白い箱＋黒字（ゼンマル）、上 |
| B_上_キーワード.srt | 赤い大きな字＋白フチ、上 |
| C_胸元_黄色.srt | 白い箱＋黄色字に黒フチ、胸元 |
| C_胸元_黒.srt | 白い箱＋黒字、胸元 |
| D_締め.srt | オレンジ字 |
| ふりがな_*.srt | ふりがな（全角スペースで位置合わせ。ずれたらCapCutで調整） |
| 手直しメモ.txt | 一部だけ赤・黄色にする場所と、ふりがなを付ける場所の一覧 |

## 台本.txt の書き方

1行に1テロップ。行の頭に種類を書きます。

| 書き方 | 意味 |
|---|---|
| `A 文字` | 通常テロップ（上） |
| `B+ 文字` 〜 `B-` | キーワード（上）。`B+` から `B-` の間のセリフのあいだ出しっぱなし |
| `CY 文字` / `CY+ 文字` | 胸元・黄色（`+` は前のテロップの下に積み重ねる） |
| `CK 文字` | 胸元・黒 |
| `D 文字` | 締め |
| `- セリフ` | テロップは出さず、時間合わせだけに使うセリフ |
| `{漢字\|かんじ}` | ふりがな |
| `[[文字]]` | 赤字 |
| `((文字))` | 黄色字 |
| `/` | 改行 |
| 行の最後に ` @73.9` | その秒（元の動画の時間）から出す。ため息など、文字起こしと合わない声に使う |

例：[examples/2026-10_運転見合わせ/台本.txt](examples/2026-10_運転見合わせ/台本.txt)

## コマンド

```bash
./setup.sh                                            # 最初に1回
python3 -I tools/transcribe.py 動画.mp4 work/文字起こし.json          # 全体の文字起こし（台本を書く用）
python3 -I tools/transcribe_chunks.py 動画.mp4 work/区切り.json      # 間ごとに区切った文字起こし（時間合わせ用・こちらを build に使う）
python3 -I tools/build.py 台本.txt work/区切り.json work/out --audio 動画.mp4   # 1.1倍速用（1.0 を付けると等速）
python3 -I tools/check_timing.py work/out/caps.json 動画.mp4                       # 声より早いテロップがないか確認
python3 -I tools/preview.py work/out/caps.json 1.1倍速にした動画.mp4 work/out/プレビュー.mp4
```

## 横動画（長尺）

[横動画ルール.md](横動画ルール.md) を参照。台本の種類は `H`（本人）と `S`（スタッフ）。カット・速度変更後の音声を使うので再生速度は `1.0`。

```bash
python3 -I tools/transcribe_chunks.py 音声.mp3 work/文字起こし.json
python3 -I tools/build.py 台本.txt work/文字起こし.json work/out 1.0 --audio 音声.mp3 --gap 3
python3 -I tools/check_timing.py work/out/caps.json 音声.mp3 1.0   # 早すぎるテロップ
python3 -I tools/check_late.py work/out/caps.json 音声.mp3 1.0     # 遅すぎるテロップ
```
