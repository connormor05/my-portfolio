# cards/feedback_card.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt

class FeedbackCard(QWidget):
    def __init__(self, correct, message, on_continue):
        super().__init__()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)

        self.setStyleSheet("""
            QWidget { background-color: #ffffff; border-radius: 20px; }
            QLabel#title { font-size: 32px; font-weight: 900; }
            QLabel#msg { font-size: 20px; color: #4b5563; margin-bottom: 20px; }
            QPushButton#primaryButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #6366f1);
                color: white; font-size: 18px; font-weight: bold;
                padding: 12px 30px; min-height: 55px; border-radius: 16px;
            }
            QPushButton#primaryButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338ca, stop:1 #4f46e5);
            }
        """)

        title_label = QLabel("Correct! 🎉" if correct else "Not Quite 🤔")
        title_label.setObjectName("title")
        title_label.setStyleSheet("color: #10B981;" if correct else "color: #EF4444;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        msg_label = QLabel(message)
        msg_label.setObjectName("msg")
        msg_label.setAlignment(Qt.AlignCenter)
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)

        btn = QPushButton("Continue")
        btn.setObjectName("primaryButton")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(on_continue)
        layout.addWidget(btn, alignment=Qt.AlignCenter)

        self.setLayout(layout)