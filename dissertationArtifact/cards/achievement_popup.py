# achievement_popup.py

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation

class AchievementPopup(QWidget):
    def __init__(self, text, parent=None):
        # We pass 'parent' so the popup knows which window it belongs to
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        # Added a little medal emoji and matched your app's achievement styling
        self.label = QLabel(f"🏅 {text}")
        self.label.setStyleSheet("""
            background-color: #FFF8E1;
            color: #B45309;
            padding: 12px 20px;
            border-radius: 12px;
            border: 2px solid #FBBF24;
            font-size: 16px;
            font-weight: bold;
        """)

        layout.addWidget(self.label)
        self.setLayout(layout)

        # Set initial opacity to 0 (invisible)
        self.setWindowOpacity(0.0)

        # -------------------------
        # Positioning Logic
        # -------------------------
        # This forces the widget to calculate its actual size before we move it
        self.adjustSize() 
        
        if parent:
            # Center the popup horizontally over the parent window, and drop it down slightly
            parent_geo = parent.geometry()
            x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
            y = parent_geo.y() + 80  # Adjust this number to move it higher or lower
            self.move(x, y)

        # -------------------------
        # Animations
        # -------------------------
        self.fade_in = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in.setDuration(300)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)

        self.fade_out = QPropertyAnimation(self, b"windowOpacity")
        self.fade_out.setDuration(300)
        self.fade_out.setStartValue(1.0)
        self.fade_out.setEndValue(0.0)
        
        # When fade out finishes, securely close the widget
        self.fade_out.finished.connect(self.close)

        # Start the fade-in instantly
        self.fade_in.start()

        # Wait 2.3 seconds (300ms fade + 2000ms read time) then start fade-out
        QTimer.singleShot(2300, self.fade_out.start)