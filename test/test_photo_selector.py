import pytest
import os
import sys
import tempfile
import json
import configparser
from unittest.mock import Mock, patch, MagicMock, mock_open
from PIL import Image
import numpy as np

# テスト対象のモジュールをインポート
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from main import AppConfig, PhotoSelectorApp


class TestAppConfig:
    """AppConfigクラスのテスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, 'test_setting.ini')
    
    def teardown_method(self):
        """各テストメソッドの後に実行される後処理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init_with_default_values(self):
        """デフォルト値でのAppConfig初期化テスト"""
        config = AppConfig(self.config_path)
        
        assert config.width == 1024
        assert config.height == 768
        assert config.key_copy == 'K'
        assert config.key_next == 'Right'
        assert config.key_prev == 'Left'
        assert config.key_delete == 'D'
        assert config.zoom_range == 10
        assert config.zoom_scale == 10
        assert config.blur_threshold == 100.0
        assert config.last_open_dir == ''
        assert config.last_save_dir == ''
    
    def test_load_from_existing_config(self):
        """既存の設定ファイルからの読み込みテスト"""
        # テスト用の設定ファイルを作成
        config_content = """
[window]
width = 1280
height = 720

[keys]
copy = C
next = Space
prev = Backspace
delete = Delete

[zoom]
range = 15
scale = 8

[blur]
threshold = 50.0

[history]
last_open_dir = /test/open
last_save_dir = /test/save
"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        config = AppConfig(self.config_path)
        
        assert config.width == 1280
        assert config.height == 720
        assert config.key_copy == 'C'
        assert config.key_next == 'Space'
        assert config.key_prev == 'Backspace'
        assert config.key_delete == 'Delete'
        assert config.zoom_range == 15
        assert config.zoom_scale == 8
        assert config.blur_threshold == 50.0
        assert config.last_open_dir == '/test/open'
        assert config.last_save_dir == '/test/save'
    
    def test_save_window_size(self):
        """ウィンドウサイズ保存のテスト"""
        config = AppConfig(self.config_path)
        config.save_window_size(1600, 900)
        
        # 設定ファイルが正しく保存されているか確認
        saved_config = configparser.ConfigParser()
        saved_config.read(self.config_path, encoding='utf-8')
        
        assert saved_config.get('window', 'width') == '1600'
        assert saved_config.get('window', 'height') == '900'
    
    def test_save_history(self):
        """履歴保存のテスト"""
        config = AppConfig(self.config_path)
        config.save_history('/new/open', '/new/save')
        
        # 設定ファイルが正しく保存されているか確認
        saved_config = configparser.ConfigParser()
        saved_config.read(self.config_path, encoding='utf-8')
        
        assert saved_config.get('history', 'last_open_dir') == '/new/open'
        assert saved_config.get('history', 'last_save_dir') == '/new/save'


class TestPhotoSelectorApp:
    """PhotoSelectorAppクラスのテスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, 'test_setting.ini')
        self.config = AppConfig(self.config_path)
    
    def teardown_method(self):
        """各テストメソッドの後に実行される後処理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('tkinter.Tk')
    @patch('tkinter.filedialog.askdirectory')
    def test_init(self, mock_askdirectory, mock_tk):
        """PhotoSelectorAppの初期化テスト"""
        mock_askdirectory.side_effect = ['/test/open', '/test/save']
        
        with patch.object(PhotoSelectorApp, 'load_images'), \
             patch.object(PhotoSelectorApp, 'show_image'):
            app = PhotoSelectorApp(self.config)
            
            assert app.config == self.config
            assert app.current_index == 0
            assert app.delete_list == []
            assert app.open_dir == '/test/open'
            assert app.save_dir == '/test/save'
            assert app.prefetch_cache == {}
    
    @patch('os.listdir')
    def test_load_images(self, mock_listdir):
        """画像読み込みテスト"""
        mock_listdir.return_value = [
            'image1.jpg', 'image2.PNG', 'image3.heic',
            'document.txt', 'image4.jpeg', 'image5.HEIC'
        ]
        
        with patch('tkinter.Tk'), \
             patch('tkinter.filedialog.askdirectory', side_effect=['/test/open', '/test/save']), \
             patch.object(PhotoSelectorApp, 'show_image'):
            app = PhotoSelectorApp(self.config)
            app.open_dir = '/test/open'
            app.load_images()
            
            expected_images = ['image1.jpg', 'image2.PNG', 'image3.heic', 'image4.jpeg', 'image5.HEIC']
            assert sorted(app.image_list) == sorted(expected_images)
    
    @patch('PIL.Image.open')
    def test_load_image_success(self, mock_open):
        """画像読み込み成功テスト"""
        mock_img = Mock()
        mock_img.convert.return_value = Mock()
        mock_open.return_value = mock_img
        
        with patch('tkinter.Tk'), \
             patch('tkinter.filedialog.askdirectory', side_effect=['/test/open', '/test/save']), \
             patch.object(PhotoSelectorApp, 'show_image'):
            app = PhotoSelectorApp(self.config)
            
            result = app.load_image('/test/image.jpg')
            
            mock_open.assert_called_once_with('/test/image.jpg')
            mock_img.convert.assert_called_once_with('RGB')
            assert result is not None
    
    @patch('PIL.Image.open')
    def test_load_image_heic(self, mock_open):
        """HEIC画像読み込みテスト"""
        mock_img = Mock()
        mock_img.convert.return_value = Mock()
        mock_open.return_value = mock_img
        
        with patch('tkinter.Tk'), \
             patch('tkinter.filedialog.askdirectory', side_effect=['/test/open', '/test/save']), \
             patch.object(PhotoSelectorApp, 'show_image'), \
             patch('pillow_heif.register_heif_opener') as mock_heif:
            app = PhotoSelectorApp(self.config)
            
            result = app.load_image('/test/image.heic')
            
            mock_heif.assert_called_once()
            mock_open.assert_called_once_with('/test/image.heic')
            assert result is not None
    
    @patch('PIL.Image.open')
    def test_load_image_failure(self, mock_open):
        """画像読み込み失敗テスト"""
        mock_open.side_effect = Exception("File not found")
        
        with patch('tkinter.Tk'), \
             patch('tkinter.filedialog.askdirectory', side_effect=['/test/open', '/test/save']), \
             patch.object(PhotoSelectorApp, 'show_image'):
            app = PhotoSelectorApp(self.config)
            
            result = app.load_image('/test/nonexistent.jpg')
            
            assert result is None
    
    def test_is_blur(self):
        """ぼかし検出テスト"""
        with patch('tkinter.Tk'), \
             patch('tkinter.filedialog.askdirectory', side_effect=['/test/open', '/test/save']), \
             patch.object(PhotoSelectorApp, 'show_image'):
            app = PhotoSelectorApp(self.config)
            
            # テスト用画像を作成
            test_img = Image.new('RGB', (100, 100), color='white')
            
            with patch('numpy.array') as mock_array, \
                 patch('cv2.Laplacian') as mock_laplacian:
                mock_array.return_value = np.zeros((100, 100))
                mock_lap = Mock()
                mock_lap.var.return_value = 50.0  # blur_threshold (100.0) より小さい値
                mock_laplacian.return_value = mock_lap
                
                result = app.is_blur(test_img)
                
                assert result is True
                
                # 閾値より大きい値の場合
                mock_lap.var.return_value = 150.0
                result = app.is_blur(test_img)
                assert result is False
    
    def test_next_image(self):
        """次の画像に移動するテスト"""
        with patch('tkinter.Tk'), \
             patch('tkinter.filedialog.askdirectory', side_effect=['/test/open', '/test/save']), \
             patch.object(PhotoSelectorApp, 'show_image') as mock_show:
            app = PhotoSelectorApp(self.config)
            app.image_list = ['img1.jpg', 'img2.jpg', 'img3.jpg']
            app.current_index = 0
            
            app.next_image()
            
            assert app.current_index == 1
            mock_show.assert_called_once()
            
            # 最後の画像の場合、インデックスは変わらない
            app.current_index = 2
            mock_show.reset_mock()
            app.next_image()
            
            assert app.current_index == 2
            mock_show.assert_not_called()
    
    def test_prev_image(self):
        """前の画像に移動するテスト"""
        with patch('tkinter.Tk'), \
             patch('tkinter.filedialog.askdirectory', side_effect=['/test/open', '/test/save']), \
             patch.object(PhotoSelectorApp, 'show_image') as mock_show:
            app = PhotoSelectorApp(self.config)
            app.image_list = ['img1.jpg', 'img2.jpg', 'img3.jpg']
            app.current_index = 2
            
            app.prev_image()
            
            assert app.current_index == 1
            mock_show.assert_called_once()
            
            # 最初の画像の場合、インデックスは変わらない
            app.current_index = 0
            mock_show.reset_mock()
            app.prev_image()
            
            assert app.current_index == 0
            mock_show.assert_not_called()
    
    def test_mark_delete(self):
        """削除マークのテスト"""
        with patch('tkinter.Tk'), \
             patch('tkinter.filedialog.askdirectory', side_effect=['/test/open', '/test/save']), \
             patch.object(PhotoSelectorApp, 'show_image'), \
             patch.object(PhotoSelectorApp, 'next_image') as mock_next:
            app = PhotoSelectorApp(self.config)
            app.image_list = ['img1.jpg', 'img2.jpg', 'img3.jpg']
            app.current_index = 0
            
            app.mark_delete()
            
            assert 'img1.jpg' in app.delete_list
            mock_next.assert_called_once()
            
            # 同じ画像を再度削除マークしても重複しない
            app.mark_delete()
            assert app.delete_list.count('img1.jpg') == 1
    
    @patch('shutil.copy2')
    def test_copy_and_next_success(self, mock_copy):
        """コピーアンドネクスト成功テスト"""
        with patch('tkinter.Tk'), \
             patch('tkinter.filedialog.askdirectory', side_effect=['/test/open', '/test/save']), \
             patch.object(PhotoSelectorApp, 'show_image'), \
             patch.object(PhotoSelectorApp, 'next_image') as mock_next:
            app = PhotoSelectorApp(self.config)
            app.image_list = ['img1.jpg', 'img2.jpg']
            app.current_index = 0
            app.open_dir = '/test/open'
            app.save_dir = '/test/save'
            
            app.copy_and_next()
            
            mock_copy.assert_called_once_with('/test/open/img1.jpg', '/test/save/img1.jpg')
            mock_next.assert_called_once()
    
    @patch('shutil.copy2')
    @patch('tkinter.messagebox.showerror')
    def test_copy_and_next_failure(self, mock_messagebox, mock_copy):
        """コピーアンドネクスト失敗テスト"""
        mock_copy.side_effect = Exception("Copy failed")
        
        with patch('tkinter.Tk'), \
             patch('tkinter.filedialog.askdirectory', side_effect=['/test/open', '/test/save']), \
             patch.object(PhotoSelectorApp, 'show_image'), \
             patch.object(PhotoSelectorApp, 'next_image') as mock_next:
            app = PhotoSelectorApp(self.config)
            app.image_list = ['img1.jpg']
            app.current_index = 0
            app.open_dir = '/test/open'
            app.save_dir = '/test/save'
            
            app.copy_and_next()
            
            mock_messagebox.assert_called_once()
            mock_next.assert_called_once()
    
    def test_save_delete_list(self):
        """削除リスト保存テスト"""
        with patch('tkinter.Tk'), \
             patch('tkinter.filedialog.askdirectory', side_effect=['/test/open', '/test/save']), \
             patch.object(PhotoSelectorApp, 'show_image'):
            app = PhotoSelectorApp(self.config)
            app.open_dir = '/test/open'
            app.delete_list = ['img1.jpg', 'img2.jpg']
            app.json_delete_path = os.path.join(self.temp_dir, 'delete_list.json')
            
            app.save_delete_list()
            
            # JSONファイルが正しく保存されているか確認
            with open(app.json_delete_path, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
            
            assert saved_data == ['img1.jpg', 'img2.jpg']
    
    @patch('os.remove')
    def test_delete_files_success(self, mock_remove):
        """ファイル削除成功テスト"""
        with patch('tkinter.Tk'), \
             patch('tkinter.filedialog.askdirectory', side_effect=['/test/open', '/test/save']), \
             patch.object(PhotoSelectorApp, 'show_image'):
            app = PhotoSelectorApp(self.config)
            app.open_dir = '/test/open'
            app.delete_list = ['img1.jpg', 'img2.jpg']
            
            app.delete_files()
            
            expected_calls = [
                (('/test/open/img1.jpg',), {}),
                (('/test/open/img2.jpg',), {})
            ]
            assert mock_remove.call_args_list == expected_calls
    
    @patch('os.remove')
    @patch('tkinter.messagebox.showerror')
    def test_delete_files_failure(self, mock_messagebox, mock_remove):
        """ファイル削除失敗テスト"""
        mock_remove.side_effect = Exception("Delete failed")
        
        with patch('tkinter.Tk'), \
             patch('tkinter.filedialog.askdirectory', side_effect=['/test/open', '/test/save']), \
             patch.object(PhotoSelectorApp, 'show_image'):
            app = PhotoSelectorApp(self.config)
            app.open_dir = '/test/open'
            app.delete_list = ['img1.jpg']
            
            app.delete_files()
            
            mock_messagebox.assert_called_once()
    
    def test_resize_image(self):
        """画像リサイズテスト"""
        with patch('tkinter.Tk'), \
             patch('tkinter.filedialog.askdirectory', side_effect=['/test/open', '/test/save']), \
             patch.object(PhotoSelectorApp, 'show_image'):
            app = PhotoSelectorApp(self.config)
            
            # モックフレームのサイズを設定
            app.image_frame = Mock()
            app.image_frame.winfo_width.return_value = 800
            app.image_frame.winfo_height.return_value = 600
            
            # テスト用画像を作成
            test_img = Mock()
            test_img.resize.return_value = Mock()
            
            result = app.resize_image(test_img)
            
            test_img.resize.assert_called_once_with((800, 600), Image.LANCZOS)
            assert result is not None


# テスト実行用のコマンドライン引数
if __name__ == '__main__':
    pytest.main([__file__, '-v'])