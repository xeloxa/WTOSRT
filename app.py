import re
import sys
import os
import functools
from typing import List, Dict, Optional
from dataclasses import dataclass
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QLabel, QFileDialog, QMessageBox, QStackedWidget,
                            QListWidget, QProgressBar, QListWidgetItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings, QMutex, QMutexLocker
from PyQt5.QtGui import QFont

@dataclass
class FileInfo:
    input_path: str
    output_path: str
    is_default_output: bool = True
    is_clipboard: bool = False

    def __post_init__(self):
        """Dosya yollarının geçerliliğini kontrol et"""
        if not self.input_path:
            raise ValueError("Input path cannot be empty")
        if not self.output_path:
            raise ValueError("Output path cannot be empty")
        
    @property
    def input_exists(self) -> bool:
        """Girdi dosyasının var olup olmadığını kontrol et"""
        return os.path.exists(self.input_path)
    
    @property
    def output_dir_exists(self) -> bool:
        """Çıktı dizininin var olup olmadığını kontrol et"""
        return os.path.exists(os.path.dirname(self.output_path))
    
    @property
    def output_dir_writable(self) -> bool:
        """Çıktı dizinine yazma izni olup olmadığını kontrol et"""
        return os.access(os.path.dirname(self.output_path), os.W_OK)
    
    def create_output_dir(self) -> None:
        """Çıktı dizinini oluştur"""
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
    
    def cleanup(self) -> None:
        """Geçici dosyaları temizle"""
        if self.is_clipboard and os.path.exists(self.input_path):
            try:
                os.remove(self.input_path)
            except OSError:
                pass

class ConversionWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, input_files: List[FileInfo], batch_size: int = 100):
        super().__init__()
        self.input_files = input_files
        self.batch_size = batch_size
        self._is_cancelled = False
        self._mutex = QMutex()  # Thread güvenliği için mutex

    def run(self) -> None:
        try:
            self._process_files_in_batches()
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    def _process_files_in_batches(self) -> None:
        total = len(self.input_files)
        for i in range(0, total, self.batch_size):
            with QMutexLocker(self._mutex):
                if self._is_cancelled:
                    break
            batch = self.input_files[i:i + self.batch_size]
            self._process_batch(batch, i, total)

    def cancel(self) -> None:
        with QMutexLocker(self._mutex):
            self._is_cancelled = True

    def _process_batch(self, batch: List[FileInfo], index: int, total: int) -> None:
        for i, file_info in enumerate(batch):
            try:
                if not file_info.input_exists:
                    raise FileNotFoundError(f"Input file not found: {file_info.input_path}")
                
                if not file_info.output_dir_exists:
                    file_info.create_output_dir()
                
                if not file_info.output_dir_writable:
                    raise PermissionError(f"No write permission for output directory: {os.path.dirname(file_info.output_path)}")
                
                self._convert_file(file_info.input_path, file_info.output_path)
                progress = int(((i + index) / total) * 100)
                self.progress.emit(progress, os.path.basename(file_info.input_path))
            except Exception as e:
                self.error.emit(f"{os.path.basename(file_info.input_path)}: {str(e)}")

    def _convert_file(self, input_path: str, output_path: str) -> None:
        with open(input_path, "r", encoding='utf-8') as infile, \
             open(output_path, "w", encoding='utf-8') as outfile:
            
            subtitle_index = 1
            for line in infile:
                with QMutexLocker(self._mutex):
                    if self._is_cancelled:
                        return

                time_match = re.search(r'\[(\d+:\d+\.\d+)\s*->\s*(\d+:\d+\.\d+)\]', line)
                if not time_match:
                    continue

                try:
                    start_time = self._time_to_seconds(time_match.group(1))
                    end_time = self._time_to_seconds(time_match.group(2))
                except ValueError as e:
                    self.error.emit(f"Invalid time format in line: {line.strip()}")
                    continue
                
                if start_time >= end_time:
                    continue

                text = re.sub(r'\[.*?\]', '', line).strip()
                if not text:
                    continue

                outfile.write(f"{subtitle_index}\n")
                outfile.write(f"{self._format_time(start_time)} --> {self._format_time(end_time)}\n")
                outfile.write(f"{text}\n\n")
                subtitle_index += 1

    @staticmethod
    def _time_to_seconds(timestamp: str) -> float:
        try:
            m, s = map(float, timestamp.split(':'))
            return max(0, m * 60 + s)
        except ValueError:
            raise ValueError(f"Invalid time format: {timestamp}")

    @staticmethod
    def _format_time(seconds: float) -> str:
        milliseconds = int((seconds - int(seconds)) * 1000)
        seconds = int(seconds)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

class SubtitleConverter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.files_to_convert: List[FileInfo] = []
        self.worker: Optional[ConversionWorker] = None
        self._setup_ui()
        self._setup_connections()
        self._load_settings()

    def closeEvent(self, event) -> None:
        """Uygulama kapatılırken geçici dosyaları temizle ve ayarları kaydet"""
        self._save_settings()
        self._cleanup_temp_files()
        super().closeEvent(event)

    def _save_settings(self) -> None:
        """Uygulama ayarlarını kaydet"""
        settings = QSettings('XeloxaSoft', 'WhisperToSRT')
        settings.setValue('geometry', self.saveGeometry())

    def _cleanup_temp_files(self) -> None:
        """Geçici dosyaları temizle"""
        for file_info in self.files_to_convert:
            file_info.cleanup()

    def _setup_ui(self) -> None:
        """UI bileşenlerini oluştur ve yapılandır"""
        self.setWindowTitle('Whisper Timestamp to SRT')
        self.setGeometry(100, 100, 800, 600)
        self._init_ui()
        self._apply_styles()

    def _apply_styles(self) -> None:
        """UI stillerini uygula"""
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1a1a1a;
            }
            QPushButton {
                background-color: #2d5af5;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 5px;
                font-size: 16px;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #1e3eb3;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #666666;
            }
            QLabel {
                color: #ffffff;
            }
            QMessageBox {
                background-color: #1a1a1a;
                color: #ffffff;
            }
            QMessageBox QLabel {
                color: #ffffff;
            }
            QMessageBox QPushButton {
                min-width: 100px;
            }
            QListWidget {
                background-color: #1E1E1E;
                border: none;
                border-radius: 8px;
                color: #ffffff;
                padding: 8px;
                min-height: 200px;
            }
            QListWidget::item {
                background-color: #2A2A2A;
                border-radius: 6px;
                margin: 4px;
            }
            QListWidget::item:hover {
                background-color: #323232;
            }
            QListWidget::item:selected {
                background-color: #2d5af5;
            }
            QProgressBar {
                border: none;
                background-color: #2a2a2a;
                height: 10px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #2d5af5;
            }
        """)

    def _setup_connections(self) -> None:
        """Sinyal ve yuva bağlantılarını kur"""
        if hasattr(self, 'file_list'):
            self.file_list.itemDoubleClicked.connect(self._change_output_location)
        if hasattr(self, 'input_next_btn'):
            self.input_next_btn.clicked.connect(self._start_batch_conversion)

    def _load_settings(self) -> None:
        """Uygulama ayarlarını yükle"""
        settings = QSettings('XeloxaSoft', 'WhisperToSRT')
        geometry = settings.value('geometry')
        if geometry:
            self.restoreGeometry(geometry)

    def _init_ui(self):
        self.setWindowTitle('Whisper Timestamp to SRT')
        self.setGeometry(100, 100, 600, 400)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        
        self.create_welcome_page()
        self.create_input_page()
        self.create_output_page()
        self.create_complete_page()
        
    def create_welcome_page(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel('Whisper Timestamp to SRT')
        title.setStyleSheet('font-size: 32px; font-weight: bold; margin-bottom: 30px; color: #ffffff;')
        title.setAlignment(Qt.AlignCenter)
        
        desc = QLabel()
        desc.setText(
            'This utility tool is designed to convert timestamped subtitles generated by applications like '
            '<a href="https://huggingface.co/spaces/sanchit-gandhi/whisper-jax" style="color: #2d5af5; text-decoration: none;">'
            'Hugging Face Space</a> into the more commonly used SRT format. '
            'However, this program does not perform subtitle transcription on its own. '
            'It only converts the output format of Whisper-JAX and subtitles using this output format into SRT. '
            'In other words, it does not convert VTT or other formats into SRT format (though these features may '
            'be added in future updates).'
        )
        desc.setStyleSheet('''
            font-size: 16px; 
            color: #999999; 
            margin-bottom: 40px;
            padding: 0 20px;
            min-height: 150px;
        ''')
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setFixedWidth(500)
        desc.setOpenExternalLinks(True)
        
        start_btn = QPushButton('Start')
        start_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        
        links_container = self._create_links_container()
        
        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addWidget(start_btn, alignment=Qt.AlignCenter)
        layout.addWidget(links_container)
        
        self.stack.addWidget(page)

    def _create_links_container(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setSpacing(20)
        
        links = {
            'Github': 'https://github.com/xeloxa',
            'Website': 'https://xeloxa.netlify.app',
            'Contact': 'mailto:alisunbul@proton.me'
        }
        
        layout.addStretch()
        for text, url in links.items():
            link = QLabel()
            link.setText(f'<a href="{url}" style="color: #999999; text-decoration: none;">{text}</a>')
            link.setOpenExternalLinks(True)
            layout.addWidget(link)
        layout.addStretch()
        
        return container

    def create_input_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        
        top_layout = QHBoxLayout()
        
        back_btn = QPushButton('←')
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 24px;
                padding: 5px 15px;
                min-width: 40px;
            }
            QPushButton:hover {
                background-color: #2a2a2a;
                border-radius: 5px;
            }
        """)
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setSpacing(5)
        
        title = QLabel('Select Files to Convert')
        title.setStyleSheet('font-size: 24px; font-weight: bold; color: #ffffff;')
        title.setAlignment(Qt.AlignCenter)
        
        subtitle = QLabel('Convert the format of your subtitle files to SRT, single or multiple.')
        subtitle.setStyleSheet('font-size: 12px; color: #999999;')
        subtitle.setAlignment(Qt.AlignCenter)
        
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        
        top_layout.addWidget(back_btn, alignment=Qt.AlignLeft)
        top_layout.addWidget(title_container)
        top_layout.addStretch()
        
        layout.addLayout(top_layout)
        
        self.file_list = QListWidget()
        self.file_list.setStyleSheet("""
            QListWidget {
                background-color: #1E1E1E;
                border: none;
                border-radius: 8px;
                color: #ffffff;
                padding: 8px;
                min-height: 200px;
            }
            QListWidget::item {
                background-color: #2A2A2A;
                border-radius: 6px;
                margin: 4px;
            }
            QListWidget::item:hover {
                background-color: #323232;
            }
            QListWidget::item:selected {
                background-color: #2d5af5;
            }
        """)
        self.file_list.setAcceptDrops(True)
        self.file_list.itemDoubleClicked.connect(self._change_output_location)
        self.file_list.mousePressEvent = self.list_mouse_press_event
        
        info_label = QLabel('Click on empty area to paste text from clipboard.\nDouble click to change output location.')
        info_label.setStyleSheet('color: #999999; font-size: 12px; font-style: italic;')
        info_label.setAlignment(Qt.AlignCenter)
        
        button_layout = QHBoxLayout()
        
        select_btn = QPushButton('Add TXT File')
        select_btn.clicked.connect(self.select_input_files)
        
        clear_btn = QPushButton('Clear List')
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff3b30;
            }
            QPushButton:hover {
                background-color: #d63029;
            }
        """)
        clear_btn.clicked.connect(self.clear_file_list)
        
        button_layout.addWidget(select_btn)
        button_layout.addWidget(clear_btn)
        
        self.input_next_btn = QPushButton('Start Conversion')
        self.input_next_btn.setEnabled(False)
        self.input_next_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 5px;
                font-size: 16px;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #666666;
            }
        """)
        self.input_next_btn.clicked.connect(self._start_batch_conversion)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #2a2a2a;
                height: 10px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #2d5af5;
            }
        """)
        self.progress_bar.hide()
        
        self.progress_label = QLabel('')
        self.progress_label.setStyleSheet('color: #999999;')
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.hide()
        
        layout.addWidget(self.file_list)
        layout.addWidget(info_label)
        layout.addLayout(button_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.input_next_btn, alignment=Qt.AlignCenter)
        
        self.stack.addWidget(page)
        
    def create_output_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel('Select Output File')
        title.setStyleSheet('font-size: 24px; font-weight: bold; margin-bottom: 20px; color: #ffffff;')
        title.setAlignment(Qt.AlignCenter)
        
        self.output_label = QLabel('No location selected')
        self.output_label.setStyleSheet('color: #999999; margin-bottom: 30px;')
        self.output_label.setAlignment(Qt.AlignCenter)
        
        select_btn = QPushButton('Choose Save Location')
        select_btn.clicked.connect(self._select_output_file)
        
        self.convert_btn = QPushButton('Convert')
        self.convert_btn.setEnabled(False)
        self.convert_btn.clicked.connect(self._start_conversion)
        
        layout.addWidget(title)
        layout.addWidget(self.output_label)
        layout.addWidget(select_btn, alignment=Qt.AlignCenter)
        layout.addWidget(self.convert_btn, alignment=Qt.AlignCenter)
        
        self.stack.addWidget(page)
        
    def create_complete_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel('Conversion Complete!')
        title.setStyleSheet('font-size: 24px; font-weight: bold; margin-bottom: 20px; color: #ffffff;')
        title.setAlignment(Qt.AlignCenter)
        
        restart_btn = QPushButton('New Conversion')
        restart_btn.clicked.connect(self._restart_conversion)
        
        layout.addWidget(title)
        layout.addWidget(restart_btn, alignment=Qt.AlignCenter)
        
        self.stack.addWidget(page)
        
    def select_input_files(self) -> None:
        """Girdi dosyalarını seç"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            'Select TXT Files',
            '',
            'TXT Files (*.txt)'
        )
        
        if not files:
            return
            
        self._process_selected_files(files)

    def _process_selected_files(self, files: List[str]) -> None:
        """Seçilen dosyaları işle"""
        duplicate_files = []
        new_files = []
        
        for input_file in files:
            if self._is_duplicate_file(input_file):
                duplicate_files.append(os.path.basename(input_file))
                continue
                
            try:
                output_file = input_file.rsplit('.', 1)[0] + '.srt'
                file_info = FileInfo(input_path=input_file, output_path=output_file)
                new_files.append(file_info)
            except ValueError as e:
                QMessageBox.warning(self, 'Error', str(e))
                continue
        
        self._add_new_files(new_files)
        self._show_duplicate_files_warning(duplicate_files)

    def _is_duplicate_file(self, input_file: str) -> bool:
        """Dosyanın zaten listede olup olmadığını kontrol et"""
        return any(file_info.input_path == input_file for file_info in self.files_to_convert)

    def _add_new_files(self, new_files: List[FileInfo]) -> None:
        """Yeni dosyaları listeye ekle"""
        for file_info in new_files:
            self.files_to_convert.append(file_info)
            self.update_list_item(len(self.files_to_convert) - 1)
        
        if new_files:
            self.input_next_btn.setEnabled(True)

    def _show_duplicate_files_warning(self, duplicate_files: List[str]) -> None:
        """Yinelenen dosyalar için uyarı göster"""
        if duplicate_files:
            files_str = "\n".join(duplicate_files)
            QMessageBox.warning(
                self,
                'Duplicate Files',
                f'The following files were not added because they are already in the list:\n\n{files_str}'
            )

    def _start_batch_conversion(self) -> None:
        """Toplu dönüştürme işlemini başlat"""
        if not self.files_to_convert:
            QMessageBox.warning(self, 'Error', 'Please select files to convert!')
            return
            
        if not self._confirm_overwrite():
            return
            
        self._prepare_conversion()
        self._start_conversion_worker()

    def _confirm_overwrite(self) -> bool:
        """Var olan dosyaların üzerine yazma onayı al"""
        existing_files = [
            os.path.basename(file_info.output_path)
            for file_info in self.files_to_convert
            if os.path.exists(file_info.output_path)
        ]
        
        if not existing_files:
            return True
            
        files_str = "\n".join(existing_files)
        reply = QMessageBox.question(
            self,
            'Files Already Exist',
            f'The following files already exist:\n\n{files_str}\n\nDo you want to overwrite them?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        return reply == QMessageBox.Yes

    def _prepare_conversion(self) -> None:
        """Dönüştürme işlemi için hazırlık yap"""
        self.input_next_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.progress_label.show()

    def _start_conversion_worker(self) -> None:
        """Dönüştürme worker'ını başlat"""
        if self.worker is not None:
            self.worker.cancel()
            self.worker.wait()
        
        self.worker = ConversionWorker(self.files_to_convert)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.conversion_finished)
        self.worker.error.connect(self.show_error)
        self.worker.start()

    def update_progress(self, value, filename):
        self.progress_bar.setValue(value)
        self.progress_label.setText(f'Converting: {filename}')

    def conversion_finished(self):
        self.progress_label.setText('All conversions completed!')
        self.input_next_btn.setEnabled(True)
        QMessageBox.information(self, 'Success', 'All files have been converted!')
        self.clear_file_list()

    def show_error(self, message):
        QMessageBox.warning(self, 'Error', message)

    def _select_output_file(self):
        default_dir = os.path.dirname(self.files_to_convert[0].input_path) if self.files_to_convert else ''
        default_name = os.path.basename(self.files_to_convert[0].output_path) if self.files_to_convert else 'subtitle.srt'
        default_path = os.path.join(default_dir, default_name)
        
        file_name, _ = QFileDialog.getSaveFileName(
            self, 
            'Save SRT File',
            default_path,
            'SRT Files (*.srt)'
        )
        
        if file_name:
            if not file_name.lower().endswith('.srt'):
                file_name += '.srt'
            self.files_to_convert[0].output_path = file_name
            self.output_label.setText(f'Selected: {file_name}')
            self.output_label.setStyleSheet('color: #999999; margin-bottom: 30px;')
            self.convert_btn.setEnabled(True)
            
    def _start_conversion(self):
        try:
            self.convert_subtitles()
            self.stack.setCurrentIndex(3)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'An error occurred during conversion:\n{str(e)}')
            
    def _restart_conversion(self):
        self.files_to_convert.clear()
        self.output_label.setText('No location selected')
        self.input_next_btn.setEnabled(False)
        self.convert_btn.setEnabled(False)
        self.stack.setCurrentIndex(0)

    def convert_subtitles(self) -> None:
        if not self._validate_conversion():
            return
        
        try:
            with open(self.files_to_convert[0].input_path, "r", encoding='utf-8') as infile:
                lines = infile.readlines()
                
            self._process_subtitle_conversion(lines)
            self._show_success_message()
            
        except FileNotFoundError:
            QMessageBox.critical(self, 'Error', 'Source file not found.')
        except PermissionError:
            QMessageBox.critical(self, 'Error', 'Permission denied when accessing file.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'An error occurred during conversion:\n{str(e)}')

    def _validate_conversion(self) -> bool:
        if not self.files_to_convert:
            QMessageBox.warning(self, 'Error', 'Please select files to convert!')
            return False
        
        if not os.path.exists(self.files_to_convert[0].input_path):
            QMessageBox.warning(self, 'Error', 'Source file not found!')
            return False
        
        return True

    def _process_subtitle_conversion(self, lines: List[str]) -> None:
        total_lines = len(lines)
        with open(self.files_to_convert[0].output_path, "w", encoding='utf-8') as outfile:
            subtitle_index = 1
            
            for current_line, line in enumerate(lines, 1):
                self._update_conversion_progress(current_line, total_lines)
                
                if subtitle := self._parse_subtitle_line(line, subtitle_index):
                    outfile.write(subtitle)
                    subtitle_index += 1

    def _show_success_message(self) -> None:
        QMessageBox.information(
            self, 
            'Success', 
            f'Conversion completed!\nFile saved as: {self.files_to_convert[0].output_path}'
        )

    def _parse_subtitle_line(self, line: str, index: int) -> Optional[str]:
        time_match = re.search(r'\[(\d+:\d+\.\d+)\s*->\s*(\d+:\d+\.\d+)\]', line)
        if not time_match:
            return None

        start_time = self._time_to_seconds(time_match.group(1))
        end_time = self._time_to_seconds(time_match.group(2))
        
        if start_time >= end_time:
            return None

        text = re.sub(r'\[.*?\]', '', line).strip()
        if not text:
            return None

        return f"{index}\n{self._format_time(start_time)} --> {self._format_time(end_time)}\n{text}\n\n"

    def _update_conversion_progress(self, current: int, total: int) -> None:
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        self.progress_label.setText(f'Converting: {current}/{total} lines')

    def list_mouse_press_event(self, event):
        if event.button() == Qt.LeftButton and not self.file_list.itemAt(event.pos()):
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            
            if text.strip():
                reply = QMessageBox.question(
                    self,
                    'Paste Text',
                    'Do you want to paste text from clipboard?',
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self.paste_clipboard_text()
        
        super(QListWidget, self.file_list).mousePressEvent(event)

    def paste_clipboard_text(self) -> None:
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        
        if not text.strip():
            QMessageBox.warning(self, 'Error', 'No text found in clipboard!')
            return
        
        output_file = self._get_output_file_path()
        if not output_file:
            return
        
        if not self._validate_output_file(output_file):
            return
            
        try:
            # Önce geçici dosyayı oluştur
            temp_input = self._create_temp_file(text)
            
            # Çıktı dizininin varlığını kontrol et
            output_dir = os.path.dirname(output_file)
            if not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir)
                except Exception as e:
                    # Geçici dosyayı temizle
                    try:
                        os.remove(temp_input)
                    except:
                        pass
                    QMessageBox.critical(self, 'Error', f'Could not create output directory: {str(e)}')
                    return
            
            # Çıktı dizinine yazma izni kontrolü
            if not os.access(output_dir, os.W_OK):
                try:
                    os.remove(temp_input)
                except:
                    pass
                QMessageBox.critical(self, 'Error', 'No write permission for the output directory')
                return
            
            file_info = FileInfo(
                input_path=temp_input, 
                output_path=output_file, 
                is_clipboard=True,
                is_default_output=False
            )
            
            self.files_to_convert.append(file_info)
            self.update_list_item(len(self.files_to_convert) - 1)
            self.input_next_btn.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error while pasting text:\n{str(e)}')
            # Hata durumunda geçici dosyayı temizle
            try:
                os.remove(temp_input)
            except:
                pass

    def _get_output_file_path(self) -> Optional[str]:
        output_file, _ = QFileDialog.getSaveFileName(
            self,
            'Save Output File',
            os.path.expanduser('~/Desktop/clipboard_text.srt'),
            'SRT Files (*.srt)'
        )
        
        if not output_file:
            return None
        
        if not output_file.lower().endswith('.srt'):
            output_file += '.srt'
        
        return output_file

    def _validate_output_file(self, output_file: str) -> bool:
        for file_info in self.files_to_convert:
            if file_info.output_path == output_file:
                QMessageBox.warning(
                    self,
                    'Duplicate Output',
                    f'The output file "{os.path.basename(output_file)}" already exists in the list.\n'
                    'Please choose a different name.'
                )
                return False
        
        if os.path.exists(output_file):
            reply = QMessageBox.question(
                self,
                'File Already Exists',
                f'"{os.path.basename(output_file)}" already exists.\nDo you want to overwrite it?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            return reply == QMessageBox.Yes
        
        return True

    def _create_temp_file(self, text: str) -> str:
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_input = os.path.join(temp_dir, 'clipboard_text.txt')
        
        with open(temp_input, 'w', encoding='utf-8') as f:
            f.write(text)
        
        return temp_input

    @staticmethod
    def safe_file_operations(func):
        """Dosya işlemleri için güvenlik dekoratörü.
        
        Hem statik metotlar hem de sınıf metotları için çalışır.
        Hata durumunda QMessageBox gösterir.
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except PermissionError:
                # İlk argüman self ise onu kullan, değilse None olarak bırak
                self = args[0] if args and isinstance(args[0], QMainWindow) else None
                if self:
                    QMessageBox.critical(self, 'Error', 'Permission denied when accessing file.')
                else:
                    QMessageBox.critical(None, 'Error', 'Permission denied when accessing file.')
            except OSError as e:
                self = args[0] if args and isinstance(args[0], QMainWindow) else None
                if self:
                    QMessageBox.critical(self, 'Error', f'File operation failed: {e}')
                else:
                    QMessageBox.critical(None, 'Error', f'File operation failed: {e}')
            return None
        return wrapper

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    converter = SubtitleConverter()
    converter.show()
    sys.exit(app.exec_())