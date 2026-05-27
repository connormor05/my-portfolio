# cards/base_card.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt

class BaseCard(QWidget):
    def __init__(self):
        super().__init__()

        # Card Specific ID
        self.setObjectName("baseCard")

        # Set up the main internal layout
        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(20) # Slightly more breathing room

        self.setLayout(self.layout)

        self.setStyleSheet("""
            QWidget#baseCard {
                background-color: white;
                border-radius: 18px;
                border: 1px solid #e5e7eb;
            }
            QLabel {
                background: transparent;
            }
        """)

    def add_widget(self, widget):
        """Helper method for child classes to quickly add elements."""
        self.layout.addWidget(widget)

    def clear_layout(self):
        """Safety method to wipe the card content if needed."""
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()