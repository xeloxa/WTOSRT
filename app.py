import re
import sys
import os
import functools
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QLabel, QFileDialog, QMessageBox, QStackedWidget,
                            QListWidget, QProgressBar, QListWidgetItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import QSettings

class ConversionWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, input_files, batch_size=100):
        super().__init__()
        self.input_files = input_files
        self.batch_size = batch_size
        self._is_cancelled = False

    def run(self):
        try:
            self.process_files_in_batches()
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    def process_files_in_batches(self):
        """Dosyaları batch'ler halinde işler."""
        total = len(self.input_files)
        for i in range(0, total, self.batch_size):
            if self._is_cancelled:
                break
                
            batch = self.input_files[i:i + self.batch_size]
            self.process_batch(batch, i, total)

    def cancel(self):
        """Dönüştürme işlemini iptal eder."""
        self._is_cancelled = True

    def process_batch(self, batch, index, total):
        for i, file_info in enumerate(batch):
            try:
                input_file = file_info['input']
                output_file = file_info['output']
                
                with open(input_file, "r", encoding='utf-8') as infile:
                    lines = infile.readlines()
                
                with open(output_file, "w", encoding='utf-8') as outfile:
                    subtitle_index = 1
                    
                    for line in lines:
                        time_match = re.search(r'\[(\d+:\d+\.\d+)\s*->\s*(\d+:\d+\.\d+)\]', line)
                        
                        if time_match:
                            start_time = self.time_to_seconds(time_match.group(1))
                            end_time = self.time_to_seconds(time_match.group(2))
                            
                            if start_time >= end_time:
                                continue
                                
                            outfile.write(f"{subtitle_index}\n")
                            outfile.write(f"{self.format_time(start_time)} --> {self.format_time(end_time)}\n")
                            
                            text = re.sub(r'\[.*?\]', '', line).strip()
                            if text:
                                outfile.write(f"{text}\n\n")
                                subtitle_index += 1
                
                progress = int(((i + index) / total) * 100)
                self.progress.emit(progress, os.path.basename(input_file))
            except Exception as e:
                self.error.emit(f"{os.path.basename(input_file)}: {str(e)}")
                continue

    def time_to_seconds(self, timestamp):
        try:
            m, s = map(float, timestamp.split(':'))
            return max(0, m * 60 + s)
        except ValueError:
            raise ValueError(f"Invalid time format: {timestamp}")

    def format_time(self, seconds):
        milliseconds = int((seconds - int(seconds)) * 1000)
        seconds = int(seconds)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

class SubtitleConverter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.files_to_convert = []  # Dosya listesini başlat
        self.setup_ui()
        self.setup_connections()
        self.load_settings()

    def setup_ui(self):
        """Kullanıcı arayüzünü hazırlar."""
        self.setWindowTitle('Whisper Timestamp to SRT')
        self.setGeometry(100, 100, 800, 600)  # Pencere boyutunu ayarla
        self.initUI()  # Mevcut UI kurulum metodunu çağır

    def setup_connections(self):
        """Sinyal ve yuva bağlantılarını kurar."""
        if hasattr(self, 'file_list'):
            self.file_list.itemDoubleClicked.connect(self.change_output_location)
        if hasattr(self, 'input_next_btn'):
            self.input_next_btn.clicked.connect(self.start_batch_conversion)

    def load_settings(self):
        """Uygulama ayarlarını yükler."""
        settings = QSettings('XeloxaSoft', 'WhisperToSRT')
        geometry = settings.value('geometry')
        if geometry:
            self.restoreGeometry(geometry)

    def initUI(self):
        self.setWindowTitle('Whisper Timestamp to SRT')
        self.setGeometry(100, 100, 600, 400)
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
        """)
        
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
        
    def create_welcome_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        
        # Banner görselini ekle
        banner_label = QLabel()
        banner_pixmap = QPixmap('banner.png')
        scaled_pixmap = banner_pixmap.scaledToWidth(500, Qt.SmoothTransformation)
        banner_label.setPixmap(scaled_pixmap)
        banner_label.setAlignment(Qt.AlignCenter)
        banner_label.setStyleSheet('margin-bottom: 20px;')
        
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
        
        links_container = QWidget()
        links_layout = QHBoxLayout(links_container)
        links_layout.setSpacing(20)
        
        github_link = QLabel()
        github_link.setText('<a href="https://github.com/xeloxa" style="color: #999999; text-decoration: none;">Github</a>')
        github_link.setOpenExternalLinks(True)
        
        website_link = QLabel()
        website_link.setText('<a href="https://xeloxa.netlify.app" style="color: #999999; text-decoration: none;">Website</a>')
        website_link.setOpenExternalLinks(True)
        
        contact_link = QLabel()
        contact_link.setText('<a href="mailto:alisunbul@proton.me" style="color: #999999; text-decoration: none;">Contact</a>')
        contact_link.setOpenExternalLinks(True)
        
        links_layout.addStretch()
        links_layout.addWidget(github_link)
        links_layout.addWidget(website_link)
        links_layout.addWidget(contact_link)
        links_layout.addStretch()
        
        layout.addWidget(banner_label)  # Banner'ı ekle
        layout.addWidget(desc)
        layout.addWidget(start_btn, alignment=Qt.AlignCenter)
        layout.addWidget(links_container)
        
        self.stack.addWidget(page)
        
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
        self.file_list.itemDoubleClicked.connect(self.change_output_location)
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
        self.input_next_btn.clicked.connect(self.start_batch_conversion)
        
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
        select_btn.clicked.connect(self.select_output_file)
        
        convert_btn = QPushButton('Convert')
        convert_btn.setEnabled(False)
        convert_btn.clicked.connect(self.start_conversion)
        self.convert_btn = convert_btn
        
        layout.addWidget(title)
        layout.addWidget(self.output_label)
        layout.addWidget(select_btn, alignment=Qt.AlignCenter)
        layout.addWidget(convert_btn, alignment=Qt.AlignCenter)
        
        self.stack.addWidget(page)
        
    def create_complete_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel('Conversion Complete!')
        title.setStyleSheet('font-size: 24px; font-weight: bold; margin-bottom: 20px; color: #ffffff;')
        title.setAlignment(Qt.AlignCenter)
        
        restart_btn = QPushButton('New Conversion')
        restart_btn.clicked.connect(self.restart_conversion)
        
        layout.addWidget(title)
        layout.addWidget(restart_btn, alignment=Qt.AlignCenter)
        
        self.stack.addWidget(page)
        
    def select_input_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            'Select TXT Files',
            '',
            'TXT Files (*.txt)'
        )
        
        if files:
            duplicate_files = []
            new_files = []
            
            for input_file in files:
                is_duplicate = any(file_info['input'] == input_file for file_info in self.files_to_convert)
                
                if is_duplicate:
                    duplicate_files.append(os.path.basename(input_file))
                else:
                    output_file = input_file.rsplit('.', 1)[0] + '.srt'
                    file_info = {
                        'input': input_file,
                        'output': output_file,
                        'is_default_output': True
                    }
                    new_files.append(file_info)
            
            for file_info in new_files:
                self.files_to_convert.append(file_info)
                self.update_list_item(len(self.files_to_convert) - 1)
            
            if new_files:
                self.input_next_btn.setEnabled(True)
            
            if duplicate_files:
                files_str = "\n".join(duplicate_files)
                QMessageBox.warning(
                    self,
                    'Duplicate Files',
                    f'The following files were not added because they are already in the list:\n\n{files_str}'
                )

    def update_list_item(self, index):
        file_info = self.files_to_convert[index]
        
        if file_info.get('is_clipboard'):
            input_name = "Pasted Text"
        else:
            input_name = os.path.basename(file_info['input'])
        
        output_name = os.path.basename(file_info['output'])
        
        item_widget = QWidget()
        layout = QHBoxLayout(item_widget)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(15)
        
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 10, 0, 10)
        info_layout.setSpacing(2)
        
        file_label = QLabel(input_name)
        file_label.setStyleSheet("""
            color: white;
            font-size: 14px;
            font-weight: 500;
        """)
        
        if file_info['is_default_output']:
            path_text = f"→ {output_name} (Default Location)"
        else:
            output_path = os.path.dirname(file_info['output'])
            path_text = f"→ {output_name} ({output_path})"
            
        path_label = QLabel(path_text)
        path_label.setStyleSheet("""
            color: #8E8E8E;
            font-size: 12px;
        """)
        
        info_layout.addWidget(file_label)
        info_layout.addWidget(path_label)
        
        remove_btn = QPushButton("Remove")
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff3b30;
                color: white;
                border: none;
                padding: 3px 8px;
                border-radius: 2px;
                font-size: 11px;
                min-width: 45px;
            }
            QPushButton:hover {
                background-color: #d63029;
            }
        """)
        remove_btn.setCursor(Qt.PointingHandCursor)
        remove_btn.clicked.connect(lambda: self.remove_file(index))
        remove_btn.setFixedWidth(45)
        remove_btn.setFixedHeight(22)
        
        layout.addWidget(info_container, stretch=1)
        layout.addWidget(remove_btn)
        
        list_item = QListWidgetItem()
        list_item.setSizeHint(item_widget.sizeHint())
        
        if index < self.file_list.count():
            self.file_list.takeItem(index)
            self.file_list.insertItem(index, list_item)
        else:
            self.file_list.addItem(list_item)
        
        self.file_list.setItemWidget(list_item, item_widget)

    def remove_file(self, index):
        if 0 <= index < len(self.files_to_convert):
            self.files_to_convert.pop(index)
            self.file_list.takeItem(index)
            
            for i in range(index, self.file_list.count()):
                item_widget = self.file_list.itemWidget(self.file_list.item(i))
                for child in item_widget.children():
                    if isinstance(child, QPushButton):
                        child.clicked.disconnect()
                        child.clicked.connect(lambda checked, idx=i: self.remove_file(idx))
            
            if not self.files_to_convert:
                self.input_next_btn.setEnabled(False)

    def change_output_location(self, item):
        index = self.file_list.row(item)
        file_info = self.files_to_convert[index]
        
        default_name = os.path.basename(file_info['output'])
        default_dir = os.path.dirname(file_info['output'])
        
        new_output, _ = QFileDialog.getSaveFileName(
            self,
            'Select Output Location',
            os.path.join(default_dir, default_name),
            'SRT Files (*.srt)'
        )
        
        if new_output:
            if not new_output.lower().endswith('.srt'):
                new_output += '.srt'
            
            if os.path.exists(new_output):
                reply = QMessageBox.question(
                    self,
                    'File Already Exists',
                    f'The file "{os.path.basename(new_output)}" already exists.\nDo you want to overwrite it?',
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.No:
                    return
            
            self.files_to_convert[index]['output'] = new_output
            self.files_to_convert[index]['is_default_output'] = False
            self.update_list_item(index)

    def clear_file_list(self):
        for file_info in self.files_to_convert:
            if file_info.get('is_clipboard'):
                try:
                    os.remove(file_info['input'])
                except:
                    pass
                
        self.file_list.clear()
        self.files_to_convert.clear()
        self.input_next_btn.setEnabled(False)
        self.progress_bar.hide()
        self.progress_label.hide()

    def start_batch_conversion(self):
        if not self.files_to_convert:
            QMessageBox.warning(self, 'Error', 'Please select files to convert!')
            return
            
        existing_files = []
        for file_info in self.files_to_convert:
            if os.path.exists(file_info['output']):
                existing_files.append(os.path.basename(file_info['output']))
        
        if existing_files:
            files_str = "\n".join(existing_files)
            reply = QMessageBox.question(
                self,
                'Files Already Exist',
                f'The following files already exist:\n\n{files_str}\n\nDo you want to overwrite them?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
            
        self.input_next_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.progress_label.show()
        
        for file_info in self.files_to_convert:
            if not os.path.exists(file_info['input']):
                QMessageBox.warning(self, 'Error', f"File not found: {file_info['input']}")
                self.input_next_btn.setEnabled(True)
                return
                
            output_dir = os.path.dirname(file_info['output'])
            if not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir)
                except Exception as e:
                    QMessageBox.warning(self, 'Error', f"Could not create output directory: {output_dir}\n{str(e)}")
                    self.input_next_btn.setEnabled(True)
                    return
        
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

    def select_output_file(self):
        default_dir = os.path.dirname(self.files_to_convert[0]['input']) if self.files_to_convert else ''
        default_name = os.path.basename(self.files_to_convert[0]['output']) if self.files_to_convert else 'subtitle.srt'
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
            self.files_to_convert[0]['output'] = file_name
            self.output_label.setText(f'Selected: {file_name}')
            self.output_label.setStyleSheet('color: #999999; margin-bottom: 30px;')
            self.convert_btn.setEnabled(True)
            
    def start_conversion(self):
        try:
            self.convert_subtitles()
            self.stack.setCurrentIndex(3)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'An error occurred during conversion:\n{str(e)}')
            
    def restart_conversion(self):
        self.files_to_convert.clear()
        self.output_label.setText('No location selected')
        self.input_next_btn.setEnabled(False)
        self.convert_btn.setEnabled(False)
        self.stack.setCurrentIndex(0)

    def convert_subtitles(self):
        """Altyazı dosyasını SRT formatına dönüştürür."""
        if not self.validate_conversion():
            return
        
        try:
            with open(self.files_to_convert[0]['input'], "r", encoding='utf-8') as infile:
                lines = infile.readlines()
                
            self.process_subtitle_conversion(lines)
            self.show_success_message()
            
        except FileNotFoundError:
            QMessageBox.critical(self, 'Hata', 'Kaynak dosya bulunamadı.')
        except PermissionError:
            QMessageBox.critical(self, 'Hata', 'Dosya erişim izni reddedildi.')
        except Exception as e:
            QMessageBox.critical(self, 'Hata', f'Dönüştürme sırasında hata oluştu:\n{str(e)}')

    def validate_conversion(self):
        """Dönüştürme işlemi için gerekli kontrolleri yapar."""
        if not self.files_to_convert:
            QMessageBox.warning(self, 'Hata', 'Lütfen dönüştürülecek dosyaları seçin!')
            return False
        
        if not os.path.exists(self.files_to_convert[0]['input']):
            QMessageBox.warning(self, 'Hata', 'Kaynak dosya bulunamadı!')
            return False
        
        return True

    def process_subtitle_conversion(self, lines):
        """Altyazı dönüştürme işlemini gerçekleştirir."""
        total_lines = len(lines)
        with open(self.files_to_convert[0]['output'], "w", encoding='utf-8') as outfile:
            subtitle_index = 1
            
            for current_line, line in enumerate(lines, 1):
                self.update_conversion_progress(current_line, total_lines)
                
                if subtitle := self.parse_subtitle_line(line, subtitle_index):
                    outfile.write(subtitle)
                    subtitle_index += 1

    def show_success_message(self):
        QMessageBox.information(self, 'Success', f'Conversion completed!\nFile saved as: {self.files_to_convert[0]["output"]}')

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

    def paste_clipboard_text(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        
        if not text.strip():
            QMessageBox.warning(self, 'Error', 'No text found in clipboard!')
            return
        
        output_file, _ = QFileDialog.getSaveFileName(
            self,
            'Save Output File',
            os.path.expanduser('~/Desktop/clipboard_text.srt'),
            'SRT Files (*.srt)'
        )
        
        if not output_file:
            return
        
        if not output_file.lower().endswith('.srt'):
            output_file += '.srt'
        
        for file_info in self.files_to_convert:
            if file_info['output'] == output_file:
                QMessageBox.warning(
                    self,
                    'Duplicate Output',
                    f'The output file "{os.path.basename(output_file)}" already exists in the list.\nPlease choose a different name.'
                )
                return
        
        # Dosya sisteminde aynı isimde dosya var mı kontrol et
        if os.path.exists(output_file):
            reply = QMessageBox.question(
                self,
                'Dosya Zaten Var',
                f'"{os.path.basename(output_file)}" dosyası zaten mevcut.\nÜzerine yazmak istiyor musunuz?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # Geçici dosya oluştur
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_input = os.path.join(temp_dir, 'clipboard_text.txt')
        
        try:
            with open(temp_input, 'w', encoding='utf-8') as f:
                f.write(text)
            
            file_info = {
                'input': temp_input,
                'output': output_file,
                'is_default_output': False,
                'is_clipboard': True
            }
            
            self.files_to_convert.append(file_info)
            self.update_list_item(len(self.files_to_convert) - 1)
            self.input_next_btn.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, 'Hata', f'Metin yapıştırılırken hata oluştu:\n{str(e)}')

    def safe_file_operations(func):
        """Dosya işlemleri için güvenlik dekoratörü."""
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except PermissionError:
                QMessageBox.critical(self, 'Hata', 'Dosya erişim izni reddedildi.')
            except OSError as e:
                QMessageBox.critical(self, 'Hata', f'Dosya işlemi başarısız: {e}')
            return None
        return wrapper

    @safe_file_operations
    def save_output_file(self, content, filepath):
        """Çıktı dosyasını güvenli bir şekilde kaydeder."""
        temp_file = filepath + '.tmp'
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        os.replace(temp_file, filepath)

    def process_large_file(self, input_file, output_file, chunk_size=1024*1024):
        """Büyük dosyaları chunk'lar halinde işler."""
        with open(input_file, 'r', encoding='utf-8') as infile, \
             open(output_file, 'w', encoding='utf-8') as outfile:
            
            buffer = []
            for chunk in iter(lambda: infile.read(chunk_size), ''):
                processed_chunk = self.process_chunk(chunk)
                buffer.append(processed_chunk)
                
                if len(buffer) >= 10:  # Buffer limitini kontrol et
                    outfile.write(''.join(buffer))
                    buffer.clear()
                    
            if buffer:  # Kalan buffer'ı yaz
                outfile.write(''.join(buffer))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    converter = SubtitleConverter()
    converter.show()
    sys.exit(app.exec_())