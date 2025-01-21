import re
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QLabel, QFileDialog, QMessageBox, QFrame, QStyle,
                            QProgressBar)
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QFont, QPalette, QColor

class DragDropArea(QFrame):
    def __init__(self, parent=None, placeholder_text="", on_click=None):
        super().__init__(parent)
        self.on_click = on_click
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.Box | QFrame.Sunken)
        self.setStyleSheet("""
            QFrame {
                background-color: #2C2C2C;
                border: 2px dashed #555;
                border-radius: 12px;
                min-height: 120px;
            }
            QFrame:hover {
                border-color: #00FF00;
                background-color: #353535;
            }
        """)
        
        layout = QVBoxLayout(self)
        self.label = QLabel(placeholder_text)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: #DDD; font-size: 14px; font-weight: bold;")
        layout.addWidget(self.label)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.on_click:
            self.on_click(self)
            
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QFrame {
                    background-color: #2C2C2C;
                    border: 2px dashed #00FF00;
                    border-radius: 12px;
                    min-height: 120px;
                }
            """)
            
    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            QFrame {
                background-color: #2C2C2C;
                border: 2px dashed #555;
                border-radius: 12px;
                min-height: 120px;
            }
            QFrame:hover {
                border-color: #00FF00;
                background-color: #353535;
            }
        """)
            
    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.parent().handle_dropped_file(file_path, self)
        self.setStyleSheet("""
            QFrame {
                background-color: #2C2C2C;
                border: 2px dashed #555;
                border-radius: 12px;
                min-height: 120px;
            }
            QFrame:hover {
                border-color: #00FF00;
                background-color: #353535;
            }
        """)

class SubtitleConverter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Altyazı Dönüştürücü')
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1E1E1E;
            }
            QPushButton {
                background-color: #444;
                color: #FFF;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                min-width: 150px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QPushButton:pressed {
                background-color: #333;
            }
            QLabel {
                color: #DDD;
                font-size: 14px;
            }
            QProgressBar {
                border: 2px solid #555;
                border-radius: 5px;
                text-align: center;
                background-color: #2C2C2C;
            }
            QProgressBar::chunk {
                background-color: #2D5A27;
                border-radius: 3px;
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(30)
        main_layout.setContentsMargins(40, 40, 40, 40)
        
        # Başlık
        title_label = QLabel('Altyazı Dönüştürücü')
        title_font = QFont()
        title_font.setPointSize(32)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet('color: #FFF; margin-bottom: 20px;')
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Sürükle-Bırak Alanları
        self.input_drop_area = DragDropArea(
            self, 
            "TXT dosyasını buraya sürükleyin veya tıklayın",
            on_click=self.select_for_area
        )
        self.output_drop_area = DragDropArea(
            self, 
            "SRT dosyasını buraya sürükleyin veya tıklayın",
            on_click=self.select_for_area
        )
        
        self.input_label = QLabel('Giriş dosyası seçilmedi')
        self.input_label.setStyleSheet('color: #AAA;')
        self.output_label = QLabel('Çıkış dosyası seçilmedi')
        self.output_label.setStyleSheet('color: #AAA;')
        
        # İlerleme Çubuğu
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setTextVisible(True)
        
        # Butonlar
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)
        
        select_input_btn = QPushButton('Giriş Dosyası Seç')
        select_output_btn = QPushButton('Çıkış Dosyası Seç')
        convert_btn = QPushButton('Dönüştür')
        convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #2D5A27;
                font-weight: bold;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #367A2F;
            }
            QPushButton:pressed {
                background-color: #1F3D1B;
            }
        """)
        
        select_input_btn.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        select_output_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        convert_btn.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        
        select_input_btn.clicked.connect(lambda: self.select_input_file())
        select_output_btn.clicked.connect(lambda: self.select_output_file())
        convert_btn.clicked.connect(self.convert_subtitles)
        
        main_layout.addWidget(self.input_drop_area)
        main_layout.addWidget(self.input_label)
        main_layout.addWidget(self.output_drop_area)
        main_layout.addWidget(self.output_label)
        main_layout.addWidget(self.progress_bar)
        
        button_layout.addStretch()
        button_layout.addWidget(select_input_btn)
        button_layout.addWidget(select_output_btn)
        button_layout.addWidget(convert_btn)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        self.input_file = ''
        self.output_file = ''
        
    def select_for_area(self, area):
        if area == self.input_drop_area:
            self.select_input_file()
        else:
            self.select_output_file()
            
    def handle_dropped_file(self, file_path, area):
        if area == self.input_drop_area and file_path.lower().endswith('.txt'):
            self.input_file = file_path
            self.input_label.setText(f'Giriş: {file_path}')
            self.input_label.setStyleSheet('color: #00FF00;')
        elif area == self.output_drop_area and file_path.lower().endswith('.srt'):
            self.output_file = file_path
            self.output_label.setText(f'Çıkış: {file_path}')
            self.output_label.setStyleSheet('color: #00FF00;')
        else:
            QMessageBox.warning(self, 'Hata', 'Geçersiz dosya formatı!')

    def select_input_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, 
            'Giriş Dosyası Seç',
            '',
            'Metin Dosyaları (*.txt)'
        )
        if file_name:
            self.input_file = file_name
            self.input_label.setText(f'Giriş: {file_name}')
            self.input_label.setStyleSheet('color: #00FF00;')

    def select_output_file(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            'Çıkış Dosyası Seç',
            '',
            'SRT Dosyaları (*.srt)'
        )
        if file_name:
            if not file_name.lower().endswith('.srt'):
                file_name += '.srt'
            self.output_file = file_name
            self.output_label.setText(f'Çıkış: {file_name}')
            self.output_label.setStyleSheet('color: #00FF00;')

    def convert_subtitles(self):
        if not self.input_file or not self.output_file:
            QMessageBox.warning(self, 'Hata', 'Lütfen giriş ve çıkış dosyalarını seçin!')
            return
            
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            with open(self.input_file, "r", encoding='utf-8') as infile:
                lines = infile.readlines()
                total_lines = len(lines)
                
            with open(self.input_file, "r", encoding='utf-8') as infile, \
                 open(self.output_file, "w", encoding='utf-8') as outfile:
                
                subtitle_index = 1
                current_line = 0
                
                for line in lines:
                    current_line += 1
                    progress = int((current_line / total_lines) * 100)
                    self.progress_bar.setValue(progress)
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
                
            self.progress_bar.setValue(100)
            QMessageBox.information(self, 'Başarılı', f'Dönüştürme tamamlandı!\nDosya kaydedildi: {self.output_file}')
            
        except Exception as e:
            QMessageBox.critical(self, 'Hata', f'Dönüştürme sırasında bir hata oluştu:\n{str(e)}')
        finally:
            self.progress_bar.setVisible(False)

    def time_to_seconds(self, timestamp):
        try:
            m, s = map(float, timestamp.split(':'))
            return max(0, m * 60 + s)
        except:
            return 0

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