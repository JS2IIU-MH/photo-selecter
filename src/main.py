import argparse
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
import cv2
import pillow_heif
import json
import configparser

SETTINGS_PATH = os.path.join(os.path.dirname(sys.argv[0]), 'setting.ini')

class AppConfig:
    def __init__(self, path=SETTINGS_PATH):
        self.config = configparser.ConfigParser()
        self.path = path
        self.load()

    def load(self):
        self.config.read(self.path, encoding='utf-8')
        self.width = self.config.getint('window', 'width', fallback=1024)
        self.height = self.config.getint('window', 'height', fallback=768)
        self.key_copy = self.config.get('keys', 'copy', fallback='K')
        self.key_next = self.config.get('keys', 'next', fallback='Right')
        self.key_prev = self.config.get('keys', 'prev', fallback='Left')
        self.key_delete = self.config.get('keys', 'delete', fallback='D')
        self.zoom_range = self.config.getint('zoom', 'range', fallback=10)
        self.zoom_scale = self.config.getint('zoom', 'scale', fallback=10)
        self.blur_threshold = self.config.getfloat('blur', 'threshold', fallback=100.0)
        self.last_open_dir = self.config.get('history', 'last_open_dir', fallback='')
        self.last_save_dir = self.config.get('history', 'last_save_dir', fallback='')

    def save_window_size(self, width, height):
        self.config.set('window', 'width', str(width))
        self.config.set('window', 'height', str(height))
        with open(self.path, 'w', encoding='utf-8') as f:
            self.config.write(f)

    def save_history(self, open_dir, save_dir):
        self.config.set('history', 'last_open_dir', open_dir)
        self.config.set('history', 'last_save_dir', save_dir)
        with open(self.path, 'w', encoding='utf-8') as f:
            self.config.write(f)

class PhotoSelectorApp(tk.Tk):
    def __init__(self, config: AppConfig, blur_method: str = 'laplacian'):
        super().__init__()
        self.config = config
        self.blur_method = blur_method
        self.title('写真選定アプリ picsel')
        self.geometry(f'{self.config.width}x{self.config.height}')
        self.protocol('WM_DELETE_WINDOW', self.on_exit)
        self.image_frame = tk.Frame(self)
        self.image_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.image_panel = tk.Label(self.image_frame)
        self.image_panel.pack(fill=tk.BOTH, expand=True)
        self.image_frame.pack_propagate(False)
        self.create_buttons()
        self.bind_keys()
        self.image_list = []
        self.current_index = 0
        self.delete_list = []
        self.open_dir = ''
        self.save_dir = ''
        self.prefetch_cache = {}
        self.json_delete_path = ''
        self.load_dirs()
        self.load_images()
        self.show_image()

    def create_buttons(self):
        self.button_frame = tk.Frame(self, height=60)
        self.button_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.button_frame.pack_propagate(False)  # 高さ固定
        self.btn_open = tk.Button(self.button_frame, text='参照先選択', command=self.select_open_dir)
        self.btn_open.pack(side=tk.LEFT, padx=5, pady=5)
        self.btn_save = tk.Button(self.button_frame, text='保存先選択', command=self.select_save_dir)
        self.btn_save.pack(side=tk.LEFT, padx=5, pady=5)
        self.btn_exit = tk.Button(self.button_frame, text='削除して終了', command=self.exit_and_delete)
        self.btn_exit.pack(side=tk.RIGHT, padx=5, pady=5)
        self.btn_exit2 = tk.Button(self.button_frame, text='削除せず終了', command=self.exit_without_delete)
        self.btn_exit2.pack(side=tk.RIGHT, padx=5, pady=5)

    def bind_keys(self):
        self.bind(f'<{self.config.key_copy}>', self.copy_and_next)
        self.bind(f'<{self.config.key_next}>', self.next_image)
        self.bind(f'<{self.config.key_prev}>', self.prev_image)
        self.bind(f'<{self.config.key_delete}>', self.mark_delete)

    def load_dirs(self):
        self.open_dir = self.config.last_open_dir or filedialog.askdirectory(title='写真フォルダを選択')
        self.save_dir = self.config.last_save_dir or filedialog.askdirectory(title='保存先フォルダを選択')
        self.config.save_history(self.open_dir, self.save_dir)
        self.json_delete_path = os.path.join(self.open_dir, 'delete_list.json')

    def select_open_dir(self):
        d = filedialog.askdirectory(initialdir=self.open_dir, title='写真フォルダを選択')
        if d:
            self.open_dir = d
            self.config.save_history(self.open_dir, self.save_dir)
            self.load_images()
            self.current_index = 0
            self.show_image()

    def select_save_dir(self):
        d = filedialog.askdirectory(initialdir=self.save_dir, title='保存先フォルダを選択')
        if d:
            self.save_dir = d
            self.config.save_history(self.open_dir, self.save_dir)

    def load_images(self):
        exts = ('.jpg', '.jpeg', '.png', '.heic')
        self.image_list = [f for f in os.listdir(self.open_dir) if f.lower().endswith(exts)]
        self.image_list.sort()
        self.prefetch_cache = {}

    def show_image(self):
        if not self.image_list:
            self.image_panel.config(image='', text='画像がありません')
            return
        fname = self.image_list[self.current_index]
        path = os.path.join(self.open_dir, fname)
        img = self.load_image(path)
        if img is None:
            self.image_panel.config(image='', text='画像を開けません')
            return
        img_disp = self.resize_image(img)
        blur = self.is_blur(img, self.blur_method)
        img_disp = self.overlay_zoom(img_disp, img)
        if blur:
            img_disp = self.overlay_blur_label(img_disp)
        self.tk_img = ImageTk.PhotoImage(img_disp)
        self.image_panel.config(image=self.tk_img)
        self.prefetch_next()

    def load_image(self, path):
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == '.heic':
                pillow_heif.register_heif_opener()
            img = Image.open(path)
            return img.convert('RGB')
        except Exception as e:
            print(f'画像読み込み失敗: {e}')
            return None

    def resize_image(self, img):
        # 画像表示用Frameのサイズに合わせてリサイズ
        w = self.image_frame.winfo_width()
        h = self.image_frame.winfo_height()
        if w < 10 or h < 10:
            w, h = self.config.width, self.config.height - 60
        return img.resize((w, h), Image.LANCZOS)

    def overlay_zoom(self, base_img, orig_img):
        from PIL import ImageDraw
        base_img = base_img.copy()  # 画像の重なり防止
        cx, cy = orig_img.width // 2, orig_img.height // 2
        r = self.config.zoom_range
        left = max(cx - r, 0)
        upper = max(cy - r, 0)
        right = min(cx + r, orig_img.width)
        lower = min(cy + r, orig_img.height)
        # 拡大枠を元画像に描画
        draw = ImageDraw.Draw(base_img)
        # 元画像の表示サイズに合わせて枠位置を変換
        disp_w, disp_h = base_img.width, base_img.height
        scale_x = disp_w / orig_img.width
        scale_y = disp_h / orig_img.height
        rect = [left*scale_x, upper*scale_y, right*scale_x, lower*scale_y]
        draw.rectangle(rect, outline='red', width=3)
        # 拡大部分の作成
        crop = orig_img.crop((left, upper, right, lower)).resize((r*2*self.config.zoom_scale, r*2*self.config.zoom_scale), Image.LANCZOS)
        # 拡大部分の枠
        crop_draw = ImageDraw.Draw(crop)
        crop_draw.rectangle([0, 0, crop.width-1, crop.height-1], outline='red', width=3)
        # ボタン領域に重ならないように下部マージンを確保
        margin = 60  # ボタン領域の高さ+余白
        pos_x = base_img.width - crop.width - 10
        pos_y = base_img.height - crop.height - margin
        if pos_y < 0:
            pos_y = 0
        base_img.paste(crop, (pos_x, pos_y))
        return base_img

    def overlay_blur_label(self, img):
        from PIL import ImageDraw, ImageFont
        img = img.copy()  # 画像の重なり防止
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 32)
        except:
            font = ImageFont.load_default()
        draw.rectangle([0,0,100,40], fill=(255,255,255,128))
        draw.text((5,5), 'Blur', fill='red', font=font)
        return img

    def is_blur(self, img, method: str = 'laplacian') -> bool:
        arr = np.array(img.convert('L'))
        if method == 'fft':
            from blur_fft import compute_blur_score_fft, normalize_score
            raw = compute_blur_score_fft(arr)
            score = normalize_score(raw)
            return score < self.config.blur_threshold
        lap = cv2.Laplacian(arr, cv2.CV_64F)
        var = lap.var()
        return var < self.config.blur_threshold

    def prefetch_next(self):
        # プリフェッチ（次画像を事前読み込み）
        idx = self.current_index + 1
        if idx < len(self.image_list):
            fname = self.image_list[idx]
            path = os.path.join(self.open_dir, fname)
            if fname not in self.prefetch_cache:
                img = self.load_image(path)
                self.prefetch_cache[fname] = img

    def copy_and_next(self, event=None):
        if not self.image_list:
            return
        fname = self.image_list[self.current_index]
        src = os.path.join(self.open_dir, fname)
        dst = os.path.join(self.save_dir, fname)
        try:
            import shutil
            shutil.copy2(src, dst)
        except Exception as e:
            messagebox.showerror('コピー失敗', str(e))
        self.next_image()

    def next_image(self, event=None):
        if self.current_index < len(self.image_list) - 1:
            self.current_index += 1
            self.show_image()

    def prev_image(self, event=None):
        if self.current_index > 0:
            self.current_index -= 1
            self.show_image()

    def mark_delete(self, event=None):
        fname = self.image_list[self.current_index]
        if fname not in self.delete_list:
            self.delete_list.append(fname)
        self.next_image()

    def exit_and_delete(self):
        self.save_delete_list()
        self.delete_files()
        self.destroy()

    def exit_without_delete(self):
        self.save_delete_list()
        self.destroy()

    def save_delete_list(self):
        with open(self.json_delete_path, 'w', encoding='utf-8') as f:
            json.dump(self.delete_list, f, ensure_ascii=False, indent=2)

    def delete_files(self):
        for fname in self.delete_list:
            try:
                os.remove(os.path.join(self.open_dir, fname))
            except Exception as e:
                messagebox.showerror('削除失敗', f'{fname}: {e}')

    def on_exit(self):
        self.exit_without_delete()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='picsel – 写真選定アプリ')
    parser.add_argument(
        '--blur-method',
        choices=['laplacian', 'fft'],
        default=None,
        help=(
            'Blur-detection method to use. '
            '"laplacian" uses the Laplacian variance method; '
            '"fft" uses the FFT high-frequency energy ratio. '
            'When specified together with --scan-dir the app runs in '
            'non-interactive CLI mode and prints per-image scores.'
        ),
    )
    parser.add_argument(
        '--scan-dir',
        default=None,
        metavar='DIR',
        help='Directory of images to scan in CLI mode (no GUI).',
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=None,
        help='Override the blur threshold from setting.ini.',
    )
    args = parser.parse_args()

    config = AppConfig()
    if args.threshold is not None:
        config.blur_threshold = args.threshold

    if args.scan_dir is not None:
        # ── CLI / non-interactive mode ────────────────────────────────────
        from blur_fft import compute_blur_score_fft, normalize_score, blur_label_and_color
        method = args.blur_method or 'laplacian'
        exts = ('.jpg', '.jpeg', '.png', '.heic')
        image_files = sorted(
            f for f in os.listdir(args.scan_dir) if f.lower().endswith(exts)
        )
        if not image_files:
            print(f'No images found in {args.scan_dir}')
            sys.exit(0)

        print(f'{"File":<40} {"Raw Score":>12} {"Score (0-100)":>14} {"Label":<8}')
        print('-' * 78)
        for fname in image_files:
            path = os.path.join(args.scan_dir, fname)
            try:
                img_bgr = cv2.imread(path)
                if img_bgr is None:
                    raise IOError('Cannot read image')
                if method == 'fft':
                    raw = compute_blur_score_fft(img_bgr)
                    norm = normalize_score(raw)
                else:
                    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY).astype('float64')
                    lap = cv2.Laplacian(gray, cv2.CV_64F)
                    raw = float(lap.var())
                    norm = min(raw, 1000.0) / 1000.0 * 100.0
                label, _ = blur_label_and_color(norm)
                print(f'{fname:<40} {raw:>12.4f} {norm:>14.2f} {label:<8}')
            except Exception as exc:
                print(f'{fname:<40} ERROR: {exc}')
    else:
        # ── GUI mode ─────────────────────────────────────────────────────
        blur_method = args.blur_method or 'laplacian'
        app = PhotoSelectorApp(config, blur_method=blur_method)
        app.mainloop()
