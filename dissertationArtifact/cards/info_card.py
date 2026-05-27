# cards/info_card.py
from PyQt5.QtWidgets import QLabel, QTextEdit, QHBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextOption, QTextBlockFormat, QTextCursor
from .base_card import BaseCard

class InfoCard(BaseCard):
    def __init__(self, text):
        super().__init__()

        # Header row with icon + title
        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignLeft)

        icon = QLabel("💡")
        icon.setStyleSheet("font-size: 28px; background: transparent;")

        title = QLabel("Key Concept")
        title.setStyleSheet("""
            QLabel {
                font-size: 22px;
                font-weight: 800;
                color: #0F766E;
                background: transparent;
            }
        """)

        header_layout.addWidget(icon)
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Explanation text box
        self.text_box = QTextEdit()
        self.text_box.setReadOnly(True)
        self.text_box.setPlainText(text)
        
        self.text_box.setWordWrapMode(QTextOption.WordWrap)
        
        self.text_box.setStyleSheet("""
            QTextEdit {
                font-size: 17px;
                color: #374151;
                background: transparent;
                border: none;
                padding: 5px;
            }
        """)
        self.text_box.setMinimumHeight(220)
        self.text_box.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        doc = self.text_box.document()
        cursor = QTextCursor(doc)
        cursor.select(QTextCursor.Document)
        
        block_format = QTextBlockFormat()
        block_format.setLineHeight(140, QTextBlockFormat.ProportionalHeight) # 1.4 line height
        cursor.setBlockFormat(block_format)

        # Add widgets to card layout
        self.layout.addLayout(header_layout)
        self.layout.addWidget(self.text_box)

        self.setWindowOpacity(0.0)