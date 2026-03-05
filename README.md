# 写真選定アプリ「picsel」

## 概要

「picsel」は、写真フォルダ内の画像を効率よくプレビューし、良い写真だけを選んでコピー・削除できるWindows専用のデスクトップアプリです。TkinterによるシンプルなUIと、Pillow/HEIF/OpenCVによる画像処理を組み合わせ、素早い選別作業をサポートします。

## 主な機能

- 指定フォルダ内の画像（jpg, png, heic）を1枚ずつプレビュー
- キー操作で「良い写真」をコピー、不要写真を削除リストに追加
- ぼやけ判定（ラプラシアン分散法）で自動的に「ぼやけ」画像を検出・ラベル表示
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

### Laplacian（ラプラシアン）法

- `src/blur_laplacian.py` モジュールが提供するラプラシアン分散法（Variance of Laplacian）を使用
- 画像をグレースケールに変換してラプラシアンフィルタを適用し、その分散値でシャープさを数値化
- 分散値が大きいほどシャープ（エッジが鮮明）、小さいほどぼやけている
- 閾値は`setting.ini`（Tkinter版）または`100.0`（Qt版仮値）で調整可能
- 典型的な閾値の目安：
  - 50〜80：かなり厳しめ（少しでもぼやけていると判定されやすい）
  - 100〜150：標準的（多くの写真で適切に判定される）
  - 200以上：かなり緩め（よほどぼやけていない限り「シャープ」と判定される）
- まずは「100.0」で試し、判定が厳しすぎる／緩すぎる場合は10〜50刻みで調整してください

### blur_laplacian モジュール API

| 関数 | 説明 |
|------|------|
| `compute_blur_score_laplacian(image)` | NumPy BGR 配列またはファイルパスを受け取り、ラプラシアン分散スコア（float）を返す。高いほどシャープ。 |
| `blur_label_and_color(score)` | スコアに基づく `(label, color)` タプルを返す（例: `("Sharp", "green")` / `("Blur", "red")`）。 |
| `normalize_score(score, cap=400.0)` | スコアを 0〜100 に正規化する。 |

### CLI でのぼやけ判定

`src/main.py` はバッチモード（`--input-dir`）でフォルダ内の全画像のスコアを出力できます：

```bash
python ./src/main.py --blur-method laplacian --input-dir /path/to/photos
```

出力例：

```
File                                      Raw score  Norm(0-100)  Label
------------------------------------------------------------------------
photo_001.jpg                               523.45        100.00  Sharp
photo_002.jpg                                12.30          3.08   Blur
```

`--blur-method` オプション：
- `laplacian`（デフォルト）: ラプラシアン分散法
- `fft`: 未実装（将来の拡張予定）

### Qt GUI でのぼやけ判定

`src/main_qt.py` の下部ツールバーに **Blur method** コンボボックスが表示されます。

- `Laplacian`: ラプラシアン分散法（非同期でスコアを計算し、下部の情報ラベルに表示）
- `FFT`: 未実装（フォールバックとして Laplacian を使用）

画像表示後、情報ラベルに次のように表示されます：

```
参照先: /path/to/photos
保存先: /path/to/selected
Blur [Laplacian]: Sharp  score=523.4  norm=100.0/100
```

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

- `blur_laplacian.py`：ラプラシアン分散法によるぼやけ検出モジュール
  - `compute_blur_score_laplacian(image)`：BGR NumPy 配列またはファイルパスを受け取りスコアを返す
  - `blur_label_and_color(score)`：スコアに基づくラベルと表示色を返す
  - `normalize_score(score, cap=400.0)`：スコアを 0〜100 に正規化する
- `main.py`：アプリ本体。TkinterによるUI、画像表示・リサイズ、ぼやけ判定、拡大表示、ファイル操作、設定管理など全機能を実装
  - `AppConfig`クラス：setting.iniの読み書き、各種設定値の管理
  - `PhotoSelectorApp`クラス：Tkウィンドウ、画像表示、ボタン・キーイベント、画像リスト管理、削除リスト管理、プリフェッチなど
  - 画像表示はFrame内Labelに固定し、ウィンドウリサイズやボタン領域との重なりを防止
  - 画像の拡大枠・ぼやけラベルはPillowで描画
  - HEIC画像はpillow-heifで対応
  - 主要な関数にはコメントあり
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
