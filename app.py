import re
import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QLabel, QFileDialog, QMessageBox, QStackedWidget,
                            QListWidget, QProgressBar, QListWidgetItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

class ConversionWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, input_files):
        super().__init__()
        self.input_files = input_files

    def run(self):
        total = len(self.input_files)
        for i, file_info in enumerate(self.input_files):
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
                
                progress = int(((i + 1) / total) * 100)
                self.progress.emit(progress, os.path.basename(input_file))
            except Exception as e:
                self.error.emit(f"{os.path.basename(input_file)}: {str(e)}")
                continue
        self.finished.emit()

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
        self.files_to_convert = []
        self.initUI()
        
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
        
        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Create stack widget
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        
        # Create pages
        self.create_welcome_page()
        self.create_input_page()
        self.create_output_page()
        self.create_complete_page()
        
    def create_welcome_page(self):
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
        
        links_container = QWidget()
        links_layout = QHBoxLayout(links_container)
        links_layout.setSpacing(20)  # Space between links
        
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
        
        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addWidget(start_btn, alignment=Qt.AlignCenter)
        layout.addWidget(links_container)
        
        self.stack.addWidget(page)
        
    def create_input_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        
        # Top layout
        top_layout = QHBoxLayout()
        
        # Back button
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
        
        # Title and subtitle container
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
        
        # File list
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
            QPushButton#removeButton {
                background-color: #FF4757;
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 500;
                min-width: 70px;
            }
            QPushButton#removeButton:hover {
                background-color: #FF6B81;
                transition: background-color 0.3s;
            }
        """)
        self.file_list.itemDoubleClicked.connect(self.change_output_location)
        
        # Info label
        info_label = QLabel('Tip: Double click on a file in the list to change output location\nOnly .txt files are supported.')
        info_label.setStyleSheet('color: #999999; font-size: 12px; font-style: italic;')
        info_label.setAlignment(Qt.AlignCenter)
        
        # Buttons
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
        
        # Progress bar
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
                # Dosyanın zaten listede olup olmadığını kontrol et
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
            
            # Yeni dosyaları listeye ekle
            for file_info in new_files:
                self.files_to_convert.append(file_info)
                self.update_list_item(len(self.files_to_convert) - 1)
            
            # Eğer yeni dosya eklendiyse butonu aktif et
            if new_files:
                self.input_next_btn.setEnabled(True)
            
            # Eğer tekrar eden dosyalar varsa kullanıcıya bildir
            if duplicate_files:
                files_str = "\n".join(duplicate_files)
                QMessageBox.warning(
                    self,
                    'Tekrar Eden Dosyalar',
                    f'Aşağıdaki dosyalar zaten listede olduğu için eklenmedi:\n\n{files_str}'
                )

    def update_list_item(self, index):
        file_info = self.files_to_convert[index]
        input_name = os.path.basename(file_info['input'])
        output_name = os.path.basename(file_info['output'])
        
        # Create widget for list item
        item_widget = QWidget()
        layout = QHBoxLayout(item_widget)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(15)
        
        # File info container
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 10, 0, 10)
        info_layout.setSpacing(2)
        
        # File name label
        file_label = QLabel(input_name)
        file_label.setStyleSheet("""
            color: white;
            font-size: 14px;
            font-weight: 500;
        """)
        
        # Output path label
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
        
        # Remove button container
        button_container = QWidget()
        button_layout = QVBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setAlignment(Qt.AlignCenter)
        
        # Remove button
        remove_btn = QPushButton("Remove")
        remove_btn.setObjectName("removeButton")
        remove_btn.setCursor(Qt.PointingHandCursor)
        remove_btn.clicked.connect(lambda: self.remove_file(index))
        remove_btn.setFixedWidth(80)
        remove_btn.setFixedHeight(32)
        
        button_layout.addWidget(remove_btn)
        
        layout.addWidget(info_container, stretch=1)
        layout.addWidget(button_container)
        
        # Create and set list item
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
            
            # Update indices for remaining items
            for i in range(index, self.file_list.count()):
                item_widget = self.file_list.itemWidget(self.file_list.item(i))
                for child in item_widget.children():
                    if isinstance(child, QPushButton):
                        child.clicked.disconnect()
                        child.clicked.connect(lambda checked, idx=i: self.remove_file(idx))
            
            # Disable Start Conversion button if list is empty
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
        self.file_list.clear()
        self.files_to_convert.clear()
        self.input_next_btn.setEnabled(False)
        self.progress_bar.hide()
        self.progress_label.hide()

    def start_batch_conversion(self):
        if not self.files_to_convert:
            QMessageBox.warning(self, 'Error', 'Please select files to convert!')
            return
            
        # Check for existing files
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
        
        # File access check
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
        if not self.files_to_convert:
            QMessageBox.warning(self, 'Error', 'Please select files to convert!')
            return
            
        try:
            with open(self.files_to_convert[0]['input'], "r", encoding='utf-8') as infile:
                lines = infile.readlines()
                total_lines = len(lines)
                
            with open(self.files_to_convert[0]['input'], "r", encoding='utf-8') as infile, \
                 open(self.files_to_convert[0]['output'], "w", encoding='utf-8') as outfile:
                
                subtitle_index = 1
                current_line = 0
                
                for line in lines:
                    current_line += 1
                    progress = int((current_line / total_lines) * 100)
                    QApplication.processEvents()
                    
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
                
            QMessageBox.information(self, 'Success', f'Conversion completed!\nFile saved as: {self.files_to_convert[0]["output"]}')
            
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'An error occurred during conversion:\n{str(e)}')

    def format_time(self, seconds):
        milliseconds = int((seconds - int(seconds)) * 1000)
        seconds = int(seconds)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    converter = SubtitleConverter()
    converter.show()
    sys.exit(app.exec_())