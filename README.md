# 写真選定アプリ「picsel」

## 概要

「picsel」は、写真フォルダ内の画像を効率よくプレビューし、良い写真だけを選んでコピー・削除できるWindows専用のデスクトップアプリです。TkinterによるシンプルなUIと、Pillow/HEIF/OpenCVによる画像処理を組み合わせ、素早い選別作業をサポートします。

## 主な機能

- 指定フォルダ内の画像（jpg, png, heic）を1枚ずつプレビュー
- キー操作で「良い写真」をコピー、不要写真を削除リストに追加
- ぼやけ判定（**ラプラシアン分散法** または **FFT高周波エネルギー比率法**）で自動的に「ぼやけ」画像を検出・ラベル表示
- 画像中央部の一部を拡大し、右下隅にオーバーレイ表示
- 操作キーや拡大範囲・倍率・ぼやけ閾値・ウィンドウサイズなどを`setting.ini`でカスタマイズ可能
- 削除リストはjson形式で一時保存、終了時にまとめて削除可能
- フォルダ選択ダイアログは直近の履歴を記憶
- 画像のプリフェッチによる高速表示
- Windows専用（tkinterバージョン：[`src/main.py`](src/main.py)）
- Mac専用（Qt5バージョン：[`src/main_qt.py`](src/main_qt.py)）

## 画面構成・操作方法

- 上部：画像プレビューエリア（画像中央部の拡大枠・ぼやけラベル付き）
- 下部：操作ボタン（参照先選択／保存先選択／削除して終了／削除せず終了）
- キーボード操作：
  - Kキー：良い写真を保存先にコピーし、次の写真へ
  - →キー：次の写真へ
  - ←キー：前の写真へ
  - Dキー：削除リストに追加し、次の写真へ
  - キー割り当ては`setting.ini`で変更可能

## ぼやけ判定について

picsel は **2 種類のぼやけ判定アルゴリズム**をサポートしています。

### ラプラシアン分散法 (laplacian)

- OpenCVのラプラシアン分散法で画像のシャープさを数値化し、閾値未満なら「ぼやけ」と判定
- 閾値は`setting.ini`の `[blur] threshold` で調整可能
- thresholdの値の目安は、一般的な写真の場合「100.0」前後が標準的です。
  - 50〜80：かなり厳しめ（少しでもぼやけていると判定されやすい）
  - 100〜150：標準的（多くの写真で適切に判定される）
  - 200以上：かなり緩め（よほどぼやけていない限り「シャープ」と判定される）

### FFT高周波エネルギー比率法 (fft)

- グレースケールに変換した画像に2次元 FFT（高速フーリエ変換）を適用し、高周波成分のエネルギー比率をシャープネス指標として用います。
- シャープな画像ほど高周波成分が多い → スコアが高い。ぼやけた画像ほど低周波成分が支配的 → スコアが低い。
- スコアは 0～100 に正規化されます。
- ラベルとスコアの目安：

  | スコア (0–100) | ラベル | 意味 |
  |:--------------:|:------:|:-----|
  | 60 以上        | Sharp  | シャープ |
  | 30 以上 60 未満 | OK    | 許容範囲 |
  | 30 未満        | Blur   | ぼやけ |

- **ラプラシアン法との違い**：
  - ラプラシアン法はエッジの強さ（局所的な輝度変化）を測定します。高コントラストなシーンに強い。
  - FFT法は周波数領域全体の高周波エネルギー比率を測定します。テクスチャが少ない画像やグラデーションが多い写真でも安定して動作しやすい。
  - どちらの手法も画像の種類や用途によって最適値が異なるため、実際の写真で確認しながら選択・調整してください。

## ぼかし判定方法の選択

### CLI（コマンドライン）での選択

```bash
# ラプラシアン法（デフォルト）
python ./src/main.py

# FFT法でGUI起動
python ./src/main.py --blur-method fft

# CLIスキャンモード（GUIなし・ディレクトリ内の全画像を一括スコアリング）
python ./src/main.py --blur-method fft --scan-dir /path/to/photos

# 閾値を上書きしてスキャン
python ./src/main.py --blur-method laplacian --scan-dir /path/to/photos --threshold 80
```

CLI スキャンモードは以下の形式で結果を出力します：

```
File                                       Raw Score   Score (0-100) Label
------------------------------------------------------------------------------
photo001.jpg                                  0.7823          78.23 Sharp
photo002.jpg                                  0.2456          24.56 Blur
...
```

### Qt GUI での選択

Qt GUI版（`src/main_qt.py`）では、ウィンドウ下部のボタン行に **「ぼかし判定: Laplacian」／「ぼかし判定: FFT」** のドロップダウンが表示されます。選択を切り替えると、現在表示中の画像が即座に再判定されます。

## 拡大表示について

- 画像中央から縦横±10ピクセル（デフォルト）の範囲を切り出し、10倍（デフォルト）に拡大
- 拡大範囲・倍率は`setting.ini`で変更可能
- 元画像上にも拡大範囲を赤枠で表示

## 設定ファイル（setting.ini）

- アプリと同じフォルダに配置
- ウィンドウサイズ、キー割り当て、拡大範囲・倍率、ぼやけ閾値、フォルダ履歴などを保存
- exe化（pyinstaller）時も同じ階層に配置

## setting.iniの書き方と各項目の説明

`setting.ini`はアプリの動作やUI、キー割り当てなどを柔軟にカスタマイズできる設定ファイルです。テキストエディタで編集できます。

### サンプル

```raw
[window]
width = 1024
height = 768

[keys]
copy = K
next = Right
prev = Left
delete = D

[zoom]
range = 10
scale = 10

[blur]
threshold = 100.0

[history]
last_open_dir = C:/Users/YourName/Pictures
last_save_dir = C:/Users/YourName/Pictures/Selected
```

### 各項目の意味

- `[window]` … アプリウィンドウの初期サイズ
  - `width`：横幅（ピクセル）
  - `height`：高さ（ピクセル）
- `[keys]` … 操作キーの割り当て
  - `copy`：良い写真をコピーするキー（例：K）
  - `next`：次の写真へ進むキー（例：Right）
  - `prev`：前の写真に戻るキー（例：Left）
  - `delete`：削除リストに追加するキー（例：D）
  - キー名はTkinterのキー名に準拠（例：A, B, C, Right, Left, Up, Down など）
- `[zoom]` … 拡大表示の設定
  - `range`：拡大する範囲（画像中央から±ピクセル数）
  - `scale`：拡大率（何倍に拡大するか）
- `[blur]` … ぼやけ判定の閾値
  - `threshold`：ラプラシアン分散値の閾値（小さいほど厳しく判定／大きいほど緩く判定）
    - 数字を小さくすると、よりシャープな画像のみ「ぼやけ」と判定されます（厳しめ）。
    - 数字を大きくすると、多少ぼやけた画像も「シャープ」と判定されやすくなります（緩め）。
    - FFT法では `threshold` はスコア 0–100 スケールの閾値として扱われます（`blur_label_and_color` 関数内の固定境界値が優先されます）。
- `[history]` … フォルダ選択ダイアログの初期値
  - `last_open_dir`：前回参照したフォルダのパス
  - `last_save_dir`：前回保存先にしたフォルダのパス

### 注意点

- ファイルはUTF-8で保存してください
- exe化した場合も`setting.ini`はexeと同じフォルダに配置してください
- 設定を変更した場合はアプリを再起動してください

## 削除リスト・一時ファイル

- Dキーで削除対象にしたファイルは、json形式で元フォルダに`delete_list.json`として保存
- 「削除して終了」ボタンで一括削除、「削除せず終了」ボタンで削除せず終了

## ソースコード解説

- `src/main.py`：アプリ本体（Tkinter版）。TkinterによるUI、画像表示・リサイズ、ぼやけ判定、拡大表示、ファイル操作、設定管理など全機能を実装
  - `AppConfig`クラス：setting.iniの読み書き、各種設定値の管理
  - `PhotoSelectorApp`クラス：Tkウィンドウ、画像表示、ボタン・キーイベント、画像リスト管理、削除リスト管理、プリフェッチなど
  - `--blur-method {laplacian,fft}` オプション・`--scan-dir` オプションでCLIスキャンモードにも対応
- `src/main_qt.py`：Qt5版アプリ本体（Mac向け）。ぼかし判定方法のドロップダウンを含む
- `src/blur_fft.py`：FFTぼかし判定モジュール
  - `compute_blur_score_fft(image)`：FFT高周波エネルギー比率を返す
  - `blur_label_and_color(score)`：スコアからラベルと色を返す
  - `normalize_score(score, cap)`：スコアを 0–100 に正規化する
- `setting.ini`：初期設定例を同梱
- `requirements.txt`：必要なPythonパッケージ一覧

## インストール・実行方法

1. Python 3.8以降をインストール
2. 必要パッケージをインストール

   ```bash
   pip install -r requirements.txt
   ```

3. アプリを起動

   ```bash
   python ./src/main.py
   ```

   もしくは

   ```bash
   python ./src/main_qt.py
   ```

4. exe化する場合はpyinstaller等を利用

## Mac専用バージョン（PyQt5版）

- Mac環境向けにPyQt5で再実装したバージョン [`src/main_qt.py`](src/main_qt.py) を追加しました。
- Windows版（Tkinter）と同等の機能を持ち、Macで快適に動作します。
- 画面構成・操作方法・設定ファイルはWindows版と共通です。
- 実行方法：

  ```bash
  pip install -r requirements.txt
  python ./src/main_qt.py
  ```

- 必要パッケージ：PyQt5, Pillow, pillow-heif, opencv-python, numpy
- MacでHEIC画像を表示する場合はpillow-heifが必要です。

---

ご質問・ご要望はIssue等でお知らせください。
