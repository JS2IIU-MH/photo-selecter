import sys
import os
import configparser
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel
)
from PyQt5.QtCore import Qt
from PIL import Image


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
        self.last_open_dir = self.config.get('history', 'last_open_dir', fallback='')
        self.last_save_dir = self.config.get('history', 'last_save_dir', fallback='')

    def save_history(self, open_dir, save_dir):
        if not self.config.has_section('history'):
            self.config.add_section('history')
        self.config.set('history', 'last_open_dir', open_dir)
        self.config.set('history', 'last_save_dir', save_dir)
        with open(self.path, 'w', encoding='utf-8') as f:
            self.config.write(f)

class PhotoSelectorApp(QMainWindow):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setWindowTitle('写真選定アプリ picsel')
        self.resize(self.config.width, self.config.height)
        self.open_dir = self.config.last_open_dir
        self.save_dir = self.config.last_save_dir
        self.image_list = []
        self.current_index = 0
        self.prefetch_cache = {}
        self.delete_list = []
        self.json_delete_path = ''
        self.init_ui()
        self.bind_keys()
        self.load_images()
        self.set_json_delete_path()
        self.show_image()
    def bind_keys(self):
        from PyQt5.QtGui import QKeySequence
        from PyQt5.QtWidgets import QShortcut
        QShortcut(QKeySequence('K'), self, self.copy_and_next)
        QShortcut(QKeySequence('Right'), self, self.next_image)
        QShortcut(QKeySequence('Left'), self, self.prev_image)
        QShortcut(QKeySequence('D'), self, self.mark_delete)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        vbox = QVBoxLayout(central)
        self.info_label = QLabel('フォルダを選択してください')
        vbox.addWidget(self.info_label)
        self.image_label = QLabel('画像がありません')
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setScaledContents(True)
        vbox.addWidget(self.image_label, stretch=1)
        hbox = QHBoxLayout()
        self.btn_open = QPushButton('参照先選択')
        self.btn_open.clicked.connect(self.select_open_dir)
        hbox.addWidget(self.btn_open)
        self.btn_save = QPushButton('保存先選択')
        self.btn_save.clicked.connect(self.select_save_dir)
        hbox.addWidget(self.btn_save)
        self.btn_exit = QPushButton('削除して終了')
        self.btn_exit.clicked.connect(self.exit_and_delete)
        hbox.addWidget(self.btn_exit)
        self.btn_exit2 = QPushButton('削除せず終了')
        self.btn_exit2.clicked.connect(self.exit_without_delete)
        hbox.addWidget(self.btn_exit2)
        vbox.addLayout(hbox)
        self.update_info_label()

    def select_open_dir(self):
        d = QFileDialog.getExistingDirectory(self, '写真フォルダを選択', self.open_dir or os.getcwd())
        if d:
            self.open_dir = d
            self.config.save_history(self.open_dir, self.save_dir)
            self.load_images()
            self.current_index = 0
            self.set_json_delete_path()
            self.show_image()
            self.update_info_label()

    def select_save_dir(self):
        d = QFileDialog.getExistingDirectory(self, '保存先フォルダを選択', self.save_dir or os.getcwd())
        if d:
            self.save_dir = d
            self.config.save_history(self.open_dir, self.save_dir)
            self.update_info_label()
    def load_images(self):
        exts = ('.jpg', '.jpeg', '.png', '.heic')
        if not self.open_dir or not os.path.isdir(self.open_dir):
            self.image_list = []
            return
        self.image_list = [f for f in os.listdir(self.open_dir) if f.lower().endswith(exts)]
        self.image_list.sort()
        self.current_index = 0

    def show_image(self):
        from PyQt5.QtGui import QPixmap
        if not self.image_list:
            self.image_label.setText('画像がありません')
            self.image_label.setPixmap(QPixmap())
            return
        fname = self.image_list[self.current_index]
        path = os.path.join(self.open_dir, fname)
        img = self.load_image(path)
        if img is None:
            self.image_label.setText('画像を開けません')
            self.image_label.setPixmap(QPixmap())
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, 'エラー', f'画像を開けません: {fname}')
            return
        img_disp = self.resize_image(img)
        blur = self.is_blur(img)
        img_disp = self.overlay_zoom(img_disp, img)
        if blur:
            img_disp = self.overlay_blur_label(img_disp)
        # Pillow画像をQPixmapに変換
        import io
        buf = io.BytesIO()
        img_disp.save(buf, format='PNG')
        buf.seek(0)
        qt_img = QPixmap()
        qt_img.loadFromData(buf.getvalue())
        self.image_label.setPixmap(qt_img)
        self.image_label.setText('')
        self.prefetch_next()

    def is_blur(self, img):
        import numpy as np
        import cv2
        arr = np.array(img.convert('L'))
        lap = cv2.Laplacian(arr, cv2.CV_64F)
        var = lap.var()
        return var < 100.0  # 閾値は仮値

    def overlay_blur_label(self, img):
        from PIL import ImageDraw, ImageFont
        img = img.copy()
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 32)
        except:
            font = ImageFont.load_default()
        draw.rectangle([0,0,100,40], fill=(255,255,255,128))
        draw.text((5,5), 'Blur', fill='red', font=font)
        return img

    def prefetch_next(self):
        idx = self.current_index + 1
        if idx < len(self.image_list):
            fname = self.image_list[idx]
            path = os.path.join(self.open_dir, fname)
            if fname not in self.prefetch_cache:
                img = self.load_image(path)
                self.prefetch_cache[fname] = img

    def next_image(self):
        if self.current_index < len(self.image_list) - 1:
            self.current_index += 1
            self.show_image()

    def prev_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.show_image()

    def copy_and_next(self):
        if not self.image_list:
            return
        fname = self.image_list[self.current_index]
        src = os.path.join(self.open_dir, fname)
        dst = os.path.join(self.save_dir, fname)
        try:
            import shutil
            shutil.copy2(src, dst)
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, 'コピー失敗', str(e))
        self.next_image()

    def mark_delete(self):
        if not self.image_list:
            return
        fname = self.image_list[self.current_index]
        if fname not in self.delete_list:
            self.delete_list.append(fname)
        self.next_image()

    def save_delete_list(self):
        if self.json_delete_path:
            import json
            with open(self.json_delete_path, 'w', encoding='utf-8') as f:
                json.dump(self.delete_list, f, ensure_ascii=False, indent=2)

    def delete_files(self):
        import os
        from PyQt5.QtWidgets import QMessageBox
        for fname in self.delete_list:
            try:
                os.remove(os.path.join(self.open_dir, fname))
            except Exception as e:
                QMessageBox.critical(self, '削除失敗', f'{fname}: {e}')

    def exit_and_delete(self):
        self.save_delete_list()
        self.delete_files()
        QApplication.quit()

    def exit_without_delete(self):
        self.save_delete_list()
        QApplication.quit()

    def set_json_delete_path(self):
        if self.open_dir:
            self.json_delete_path = os.path.join(self.open_dir, 'delete_list.json')

    def load_image(self, path):
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == '.heic':
                import pillow_heif
                pillow_heif.register_heif_opener()
            from PIL import Image
            img = Image.open(path)
            return img.convert('RGB')
        except Exception as e:
            print(f'画像読み込み失敗: {e}')
            return None

    def resize_image(self, img):
        # アスペクト比を維持してリサイズ
        w = self.image_label.width() or self.config.width
        h = self.image_label.height() or self.config.height - 60
        img_w, img_h = img.size
        ratio = min(w / img_w, h / img_h)
        new_size = (int(img_w * ratio), int(img_h * ratio))
        return img.resize(new_size, Image.LANCZOS)

    def overlay_zoom(self, base_img, orig_img):
        from PIL import ImageDraw
        base_img = base_img.copy()
        cx, cy = orig_img.width // 2, orig_img.height // 2
        r = 10  # 仮値: 拡大枠サイズ
        left = max(cx - r, 0)
        upper = max(cy - r, 0)
        right = min(cx + r, orig_img.width)
        lower = min(cy + r, orig_img.height)
        draw = ImageDraw.Draw(base_img)
        disp_w, disp_h = base_img.width, base_img.height
        scale_x = disp_w / orig_img.width
        scale_y = disp_h / orig_img.height
        rect = [left*scale_x, upper*scale_y, right*scale_x, lower*scale_y]
        draw.rectangle(rect, outline='red', width=3)
        # 拡大部分の作成
        crop = orig_img.crop((left, upper, right, lower)).resize((r*2*5, r*2*5), Image.LANCZOS)
        crop_draw = ImageDraw.Draw(crop)
        crop_draw.rectangle([0, 0, crop.width-1, crop.height-1], outline='red', width=3)
        margin = 60
        pos_x = base_img.width - crop.width - 10
        pos_y = base_img.height - crop.height - margin
        if pos_y < 0:
            pos_y = 0
        base_img.paste(crop, (pos_x, pos_y))
        return base_img

    def update_info_label(self):
        self.info_label.setText(f'参照先: {self.open_dir}\n保存先: {self.save_dir}')

if __name__ == '__main__':
    config = AppConfig()
    app = QApplication(sys.argv)
    win = PhotoSelectorApp(config)
    win.show()
    sys.exit(app.exec_())
