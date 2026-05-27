# cards/ask_card.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QSizePolicy
from PyQt5.QtCore import Qt

class AskCard(QWidget):
    def __init__(self, question_text, on_submit, on_skip):
        super().__init__()

        self.on_submit = on_submit

        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(10, 10, 10, 10)

        # Forced Styling
        self.setStyleSheet("""
            QLineEdit#chatInput {
                background-color: #ffffff;
                border: 2px solid #d1d5db;
                border-radius: 14px;
                padding: 12px;
                font-size: 18px; 
            }
            QLineEdit#chatInput:focus {
                border: 2px solid #4f46e5;
            }
            QPushButton#primaryButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #6366f1);
                color: white;
                font-size: 18px; 
                font-weight: bold;
                border-radius: 20px;
            }
            QPushButton#primaryButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338ca, stop:1 #4f46e5);
            }
            QPushButton#secondaryButton {
                background-color: #ffffff;
                color: #4f46e5;
                border: 2px solid #4f46e5;
                font-size: 18px; 
                font-weight: bold;
                border-radius: 20px;
            }
            QPushButton#secondaryButton:hover {
                background-color: #eef2ff;
            }
        """)

        # AI Message Display
        self.text_box = QTextEdit()
        self.text_box.setReadOnly(True)
        self.text_box.setPlainText(question_text)
        self.text_box.setWordWrapMode(True)
        self.text_box.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.text_box.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.text_box.setStyleSheet("""
            QTextEdit {
                font-size: 20px; /* Made question text even bigger */
                font-weight: bold;
                color: #1e1e2f;
                line-height: 1.4; 
                border: none; 
                background: transparent;
            }
        """)
        self.text_box.setMinimumHeight(100)
        self.text_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.text_box)

        # User Input Box
        self.input = QLineEdit()
        self.input.setObjectName("chatInput") 
        self.input.setPlaceholderText("Type your question here...")
        self.input.setFixedHeight(55) 
        
        self.input.returnPressed.connect(self._handle_submit)
        layout.addWidget(self.input)

        # Submit Button
        self.submit_btn = QPushButton("Ask AI")
        self.submit_btn.setObjectName("primaryButton") 
        self.submit_btn.setFixedHeight(55) # Force it to be big!
        self.submit_btn.setCursor(Qt.PointingHandCursor)
        self.submit_btn.clicked.connect(self._handle_submit)
        
        self.submit_btn.setAutoDefault(False)
        self.submit_btn.setDefault(False)
        
        layout.addWidget(self.submit_btn)

        # Skip Button
        self.skip_btn = QPushButton("No, let's move on")
        self.skip_btn.setObjectName("secondaryButton") 
        self.skip_btn.setFixedHeight(55) # Force it to be big!
        self.skip_btn.setCursor(Qt.PointingHandCursor)
        self.skip_btn.clicked.connect(on_skip)
        layout.addWidget(self.skip_btn)

        self.setLayout(layout)
        
        self.input.setFocus()

    def _handle_submit(self):
        text = self.input.text().strip()

        if not text:
            return

        self.submit_btn.setEnabled(False)
        self.on_submit(text)