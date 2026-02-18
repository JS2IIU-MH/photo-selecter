# パフォーマンス改善について

## 概要

このドキュメントでは、画像読み込み速度を向上させるために実装された最適化について説明します。

## 実装された改善点

### 1. プリフェッチキャッシュの活用 ✨

**変更前:**
- 画像を表示するたびに、ファイルから読み込み直していた
- プリフェッチしても、表示時に再度読み込んでいた

**変更後:**
- プリフェッチキャッシュに画像がある場合は、それを使用
- ディスクI/Oを削減し、表示速度が大幅に向上

```python
# Use prefetch cache if available
if fname in self.prefetch_cache:
    img = self.prefetch_cache[fname]
else:
    img = self.load_image(path)
```

### 2. 複数画像の先読み 🚀

**変更前:**
- 次の1枚のみをプリフェッチ

**変更後:**
- 次の3枚を先読み
- 前の1枚も先読み（戻る操作も高速化）
- スムーズな画像ナビゲーションを実現

```python
# Load next 3 images for faster navigation
for offset in range(1, 4):
    idx = self.current_index + offset
    if idx < len(self.image_list):
        # ... prefetch logic ...

# Also load previous image for backward navigation
idx = self.current_index - 1
if idx >= 0:
    # ... prefetch logic ...
```

### 3. JPEGドラフトモードの使用 📸

**変更前:**
- 全てのJPEG画像をフル解像度で読み込み

**変更後:**
- JPEGの`draft()`モードを使用して、必要な解像度に近い低解像度で高速に読み込み
- 特に大きな画像ファイルで効果が顕著

```python
if ext in ('.jpg', '.jpeg'):
    # Request approximate size for faster decoding
    img.draft('RGB', (self.config.width * 2, self.config.height * 2))
```

### 4. ぼやけ判定結果のキャッシュ 💾

**変更前:**
- 画像を表示するたびに、OpenCVでぼやけ判定を実行

**変更後:**
- 一度計算したぼやけ判定結果をキャッシュ
- 同じ画像を再表示する際の処理時間を削減

```python
# Use blur cache if available
if fname in self.blur_cache:
    blur = self.blur_cache[fname]
else:
    blur = self.is_blur(img)
    self.blur_cache[fname] = blur
```

### 5. 高速な画像リサイズアルゴリズム ⚡

**変更前:**
- `Image.LANCZOS`を使用（高品質だが遅い）

**変更後:**
- `Image.BILINEAR`を使用（品質と速度のバランスが良い）
- 表示用途では視覚的な差はほとんどなく、処理速度が向上

```python
# Use faster resizing for better performance
return img.resize((w, h), Image.BILINEAR)
```

### 6. メモリ管理の最適化 🧹

**変更前:**
- キャッシュが無制限に増加する可能性

**変更後:**
- 現在位置から前後5枚のみをキャッシュに保持
- メモリ使用量を適切に管理しながら、パフォーマンスを維持

```python
# Clean up old cache entries to prevent memory issues
# Keep only nearby images in cache (5 before, 5 after)
cache_range = 5
keep_indices = set(range(
    max(0, self.current_index - cache_range),
    min(len(self.image_list), self.current_index + cache_range + 1)
))
```

## パフォーマンス向上の効果

### 予想される改善

1. **初回画像表示**: 20-40%高速化
   - JPEGドラフトモードとBILINEARリサイズによる効果

2. **2回目以降の表示**: 70-90%高速化
   - キャッシュの活用により、ディスクI/Oとぼやけ判定が不要

3. **画像ナビゲーション**: 最大90%高速化
   - プリフェッチにより、次の画像が即座に表示可能

4. **メモリ使用量**: 適切に管理
   - 最大11枚（現在+前5枚+後5枚）のキャッシュで制限

## 適用ファイル

- `src/main.py` (Windows版 - Tkinter)
- `src/main_qt.py` (Mac版 - PyQt5)

両方のファイルに同じ最適化を適用しました。

## 注意事項

- 画像品質は`LANCZOS`から`BILINEAR`に変更されましたが、視覚的な差はほとんどありません
- 大量の画像を扱う場合、メモリ使用量が若干増加する可能性がありますが、キャッシュ管理により制限されています
- HEICファイルは`draft()`モードに対応していないため、従来通りの読み込み方法を使用します

## 今後の改善案

- 非同期/バックグラウンドでのプリフェッチ（現在は同期処理）
- サムネイルの事前生成と保存
- より高度なキャッシュ戦略（LRUキャッシュなど）
