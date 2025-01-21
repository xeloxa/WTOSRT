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
        
        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addWidget(start_btn, alignment=Qt.AlignCenter)
        
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
        
        title = QLabel('Select Files to Convert')
        title.setStyleSheet('font-size: 24px; font-weight: bold; margin-bottom: 20px; color: #ffffff;')
        title.setAlignment(Qt.AlignCenter)
        
        top_layout.addWidget(back_btn, alignment=Qt.AlignLeft)
        top_layout.addWidget(title)
        top_layout.addStretch()
        
        layout.addLayout(top_layout)
        
        # File list
        self.file_list = QListWidget()
        self.file_list.setStyleSheet("""
            QListWidget {
                background-color: #2a2a2a;
                border: 1px solid #333333;
                border-radius: 5px;
                color: #ffffff;
                padding: 5px;
                min-height: 200px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #333333;
            }
            QListWidget::item:selected {
                background-color: #2d5af5;
            }
        """)
        self.file_list.itemDoubleClicked.connect(self.change_output_location)
        
        # Info label
        info_label = QLabel('Tip: Double click a file in the list to change its output location')
        info_label.setStyleSheet('color: #999999; font-size: 12px; font-style: italic;')
        info_label.setAlignment(Qt.AlignCenter)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        select_btn = QPushButton('Add Files')
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
            'Text Files (*.txt)'
        )
        
        if files:
            for input_file in files:
                output_file = input_file.rsplit('.', 1)[0] + '.srt'
                file_info = {
                    'input': input_file,
                    'output': output_file,
                    'is_default_output': True
                }
                self.files_to_convert.append(file_info)
                self.update_list_item(len(self.files_to_convert) - 1)
            
            self.input_next_btn.setEnabled(True)

    def update_list_item(self, index):
        file_info = self.files_to_convert[index]
        input_name = os.path.basename(file_info['input'])
        output_name = os.path.basename(file_info['output'])
        
        if file_info['is_default_output']:
            text = f"{input_name} → {output_name} (Default Location)"
            color = '#2d5af5'
        else:
            text = f"{input_name} → {output_name} (Custom Location)"
            color = '#999999'
            
        if index < self.file_list.count():
            item = self.file_list.item(index)
            item.setText(text)
            item.setForeground(Qt.GlobalColor.white)
        else:
            item = QListWidgetItem(text)
            item.setForeground(Qt.GlobalColor.white)
            self.file_list.addItem(item)

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