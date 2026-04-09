import sys
import pyfiglet
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTextEdit, QComboBox, QLabel, QMessageBox
)
from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtCore import Qt

class AsciiArtGeneratorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Text to ASCII Art Generator")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self._create_widgets()
        self._configure_layouts()
        self._connect_signals()

    def _create_widgets(self):
        self.font_label = QLabel("ASCII Art Font:")
        self.font_combo_box = QComboBox()
        
        self.available_fonts = pyfiglet.FigletFont.getFonts()
        self.font_combo_box.addItems(self.available_fonts)
        
        default_font = "standard"
        if default_font in self.available_fonts:
            self.font_combo_box.setCurrentText(default_font)

        self.input_label = QLabel("Input Text:")
        self.input_text_edit = QLineEdit()
        self.input_text_edit.setPlaceholderText("Type Something")

        self.generate_button = QPushButton("Generate")
        self.copy_button = QPushButton("Copy to Clipboard")

        self.output_text_edit = QTextEdit()
        self.output_text_edit.setReadOnly(True)
        self.output_text_edit.setFont(QFont("Courier New", 10))
        self.output_text_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

    def _configure_layouts(self):
        options_layout = QHBoxLayout()
        options_layout.addWidget(self.font_label)
        options_layout.addWidget(self.font_combo_box)
        options_layout.addStretch()

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_label)
        input_layout.addWidget(self.input_text_edit)
        
        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.generate_button)
        actions_layout.addWidget(self.copy_button)
        
        self.main_layout.addLayout(options_layout)
        self.main_layout.addLayout(input_layout)
        self.main_layout.addWidget(self.output_text_edit, 1)
        self.main_layout.addLayout(actions_layout)

    def _connect_signals(self):
        self.generate_button.clicked.connect(self.generate_art)
        self.input_text_edit.returnPressed.connect(self.generate_art)
        self.copy_button.clicked.connect(self.copy_to_clipboard)

    def generate_art(self):
        input_text: str = self.input_text_edit.text()
        selected_font: str = self.font_combo_box.currentText()

        if not input_text:
            self.show_error("Input text cannot be empty.")
            return

        try:
            figlet_generator = pyfiglet.Figlet(font=selected_font)
            ascii_art: str = figlet_generator.renderText(input_text)
            self.output_text_edit.setPlainText(ascii_art)
        except pyfiglet.FontNotFound:
            self.show_error(f"Font '{selected_font}' not found.")
            self.output_text_edit.setPlainText("")
        except Exception as e:
            self.show_error(f"An unexpected error occurred: {e}")
            self.output_text_edit.setPlainText("")
        
    def copy_to_clipboard(self):
        clipboard = QGuiApplication.clipboard()
        text_to_copy = self.output_text_edit.toPlainText()
        if text_to_copy:
            clipboard.setText(text_to_copy)

    def show_error(self, message: str):
        error_box = QMessageBox()
        error_box.setIcon(QMessageBox.Icon.Critical)
        error_box.setText(message)
        error_box.setWindowTitle("Error")
        error_box.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AsciiArtGeneratorApp()
    window.show()
    sys.exit(app.exec())
