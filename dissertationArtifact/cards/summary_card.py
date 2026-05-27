# cards/summary_card.py
from PyQt5.QtWidgets import QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QFrame, QWidget
from .base_card import BaseCard
from PyQt5.QtCore import Qt

class SummaryCard(BaseCard):
    def __init__(self, xp_gained, achievements, on_next_lesson, on_home):
        super().__init__()

        self.layout.setAlignment(Qt.AlignCenter)
        self.layout.setSpacing(15)

        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
            }
            QLabel#headerTitle {
                font-size: 36px; 
                font-weight: 900; 
                color: #1f2937;
            }
            QFrame#achContainer {
                background-color: #f9fafb;
                border: 2px solid #e5e7eb;
                border-radius: 20px;
                padding: 20px;
                margin: 10px 0px;
            }
            QLabel#sectionTitle {
                font-size: 20px; 
                font-weight: 800; 
                color: #4b5563; 
                margin-bottom: 5px;
            }
            QLabel#achievementItem {
                font-size: 18px; 
                color: #d97706; 
                font-weight: bold; 
                margin: 4px 0px;
            }
            QPushButton#primaryButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #6366f1);
                color: white; 
                font-size: 18px; 
                font-weight: bold;
                padding: 12px; 
                min-height: 55px; 
                border-radius: 16px;
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
                padding: 12px; 
                min-height: 55px; 
                border-radius: 16px;
            }
            QPushButton#secondaryButton:hover {
                background-color: #eef2ff;
            }
        """)

        # Title
        self.title = QLabel("Lesson Complete! 🎉")
        self.title.setObjectName("headerTitle")
        self.title.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.title)

        # XP Gained (The Big Highlight)
        self.xp_display = QLabel(f"+{xp_gained} XP")
        self.xp_display.setAlignment(Qt.AlignCenter)
        self.xp_display.setStyleSheet("""
            font-size: 48px;
            font-weight: 900;
            color: #10B981;
            margin-bottom: 10px;
        """)
        self.layout.addWidget(self.xp_display)

        # Achievements Section
        if achievements:
            ach_container = QFrame()
            ach_container.setObjectName("achContainer") 
            ach_vbox = QVBoxLayout(ach_container)
            ach_vbox.setAlignment(Qt.AlignCenter)
            
            ach_title = QLabel("New Achievements:")
            ach_title.setObjectName("sectionTitle")
            ach_title.setAlignment(Qt.AlignCenter)
            ach_vbox.addWidget(ach_title)

            for ach in achievements:
                lbl = QLabel(f"🏅 {ach}")
                lbl.setObjectName("achievementItem")
                lbl.setAlignment(Qt.AlignCenter)
                ach_vbox.addWidget(lbl)
            
            self.layout.addWidget(ach_container)

        # Buttons Row
        self.layout.addSpacing(10)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        # Next Lesson
        self.next_btn = QPushButton("Next Lesson")
        self.next_btn.setObjectName("primaryButton")
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.clicked.connect(on_next_lesson)
        btn_layout.addWidget(self.next_btn)

        # Home
        self.home_btn = QPushButton("Return Home")
        self.home_btn.setObjectName("secondaryButton")
        self.home_btn.setCursor(Qt.PointingHandCursor)
        self.home_btn.clicked.connect(on_home)
        btn_layout.addWidget(self.home_btn)

        self.layout.addLayout(btn_layout)
        
        self.next_btn.setFocus()