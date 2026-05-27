# cards/loading_card.py
from PyQt5.QtWidgets import QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer
from .base_card import BaseCard

class LoadingCard(BaseCard):
    def __init__(self, text="Thinking"):
        super().__init__()

        self.layout.setAlignment(Qt.AlignCenter)

        self.base_text = text
        self.dot_count = 0

        # The Loading Label
        self.label = QLabel(self.base_text)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                font-size: 22px;
                font-weight: 600;
                color: #4F46E5; /* Your Indigo theme color */
                background: transparent;
            }
        """)

        self.layout.addWidget(self.label)

        # Timer for the "pulsing dots" animation
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_dots)
        self.timer.start(500) 

    def update_dots(self):
        """Creates the 'Thinking...' animation effect."""
        self.dot_count = (self.dot_count + 1) % 4
        dots = "." * self.dot_count
        self.label.setText(f"{self.base_text}{dots}")

    def stop_animation(self):
        """Cleanup timer when card is destroyed."""
        self.timer.stop()