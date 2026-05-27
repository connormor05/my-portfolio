# cards/confetti.py
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QBrush
import random
import math

class Confetti(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setParent(parent)
        
        if parent:
            self.setGeometry(0, 0, parent.width(), parent.height())
        
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Particle structure
        self.particles = []
        colors = [
            QColor("#4F46E5"), # Indigo
            QColor("#10B981"), # Emerald
            QColor("#FBBF24"), # Amber
            QColor("#EF4444"), # Red
            QColor("#3B82F6")  # Blue
        ]
        
        for _ in range(50): 
            self.particles.append([
                random.randint(0, self.width()),   # x
                random.randint(-200, -10),         # y (start above the screen)
                random.choice(colors),             # color
                random.randint(4, 8),              # fall speed
                random.uniform(0, 2 * math.pi),    # sway offset
                random.randint(6, 10)              # size
            ])

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_particles)
        self.timer.start(20)

        # Auto-destroy after 2.5 seconds
        QTimer.singleShot(2500, self.close)

    def update_particles(self):
        for p in self.particles:
            # Drop down
            p[1] += p[3] 
            p[0] += math.sin(p[1] / 20 + p[4]) * 2
            
        self.update() 

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)

        for x, y, color, speed, sway, size in self.particles:
            painter.setBrush(QBrush(color))
            # Draw as rounded rectangles/squares
            painter.drawRoundedRect(int(x), int(y), size, size, 2, 2)