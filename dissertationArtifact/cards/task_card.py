# cards/task_card.py
from PyQt5.QtWidgets import QVBoxLayout, QTextEdit, QPushButton, QLineEdit, QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QTextOption
from .base_card import BaseCard

class TaskCard(BaseCard):
    def __init__(self, task, on_answer):
            super().__init__()
            
            self.setObjectName("taskFrame")

            self.setStyleSheet("""
            QWidget#taskFrame {
                background-color: #ffffff;
                border: 2px solid #e5e7eb;
                border-radius: 24px;
                padding: 30px; /* More breathing room */
            }
            QLabel#statLabel {
                font-size: 14px;
                color: #6b7280;
                font-weight: bold;
                margin-bottom: 10px;
            }
            QTextEdit#taskQuestion {
                font-size: 20px; 
                font-weight: 800;
                color: #1f2937;
                background: transparent;
                border: none;
                margin-bottom: 10px;
            }
            }
            QLineEdit#chatInput {
                background-color: #f9fafb;
                border: 2px solid #d1d5db;
                border-radius: 16px;
                padding: 15px;
                font-size: 18px; 
                min-height: 50px;
                margin-top: 20px;
                color: #1f2937;
            }
            QLineEdit#chatInput:focus {
                border: 2px solid #4f46e5;
                background-color: #ffffff;
            }
            QPushButton#taskButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #6366f1);
                color: white;
                font-size: 18px; 
                font-weight: 800;
                padding: 12px;
                min-height: 50px;
                border-radius: 16px;
                margin-top: 15px;
            }
            QPushButton#taskButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338ca, stop:1 #4f46e5);
            }
            QPushButton#secondaryButton {
                background-color: #ffffff;
                color: #4f46e5;
                border: 2px solid #e5e7eb; /* Subtle light border by default */
                border-radius: 16px;
                padding: 12px 20px;
                min-height: 40px; /* Much shorter but still clickable */
                font-size: 16px; 
                font-weight: 600;
                margin: 4px 0px;
                text-align: left; /* Modern MCQ look often uses left-align */
                padding-left: 20px;
            }
            QPushButton#secondaryButton:hover {
                background-color: #f5f3ff;
                border: 2px solid #c7d2fe;
                color: #4338ca;
            }
            """)

            # Data Normalisation
            task_type = task.get("task_type") or task.get("task")
            if task_type in ["fill_blank", "multiple_choice", "true_false", "predict_output", "debug_code", "code_output"]:
                task["type"] = task_type

            if task.get("type") == "fill_blank" and isinstance(task.get("options"), dict):
                task["options"] = task["options"].get("options", [])

            self.task = task
            self.on_answer = on_answer

            # Feedback System 
            self.base_style = self.styleSheet()
            
            def flash_feedback(correct: bool):
                color = "#d1fae5" if correct else "#fee2e2"
                self.setStyleSheet(self.base_style + f" QWidget#taskFrame {{ background-color: {color}; }}")
                QTimer.singleShot(250, lambda: self.setStyleSheet(self.base_style))
                
            self.flash_feedback = flash_feedback

            # Header: Task Stage
            stage_names = ["Recall", "Apply", "Reason"]
            stage_index = min(task.get("taskStage", 0), len(stage_names) - 1)
            self.stage_label = QLabel(f"Stage: {stage_names[stage_index]}")
            self.stage_label.setObjectName("statLabel")
            self.layout.addWidget(self.stage_label)

            # Question Display
            question_text = task.get("question") or task.get("prompt") or ""
            self.question_box = QTextEdit()
            self.question_box.setReadOnly(True)
            self.question_box.setPlainText(question_text)
            self.question_box.setObjectName("taskQuestion")
            self.question_box.setWordWrapMode(QTextOption.WordWrap)
            
            self.question_box.setMinimumHeight(80)
            self.question_box.setMaximumHeight(150)
            self.layout.addWidget(self.question_box)

            # Code block
            if "code" in task and task["code"]:
                code_label = QLabel(task["code"])
                code_label.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; border-radius: 8px; padding: 12px; font-family: monospace; font-size: 13px;")
                code_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                self.layout.addWidget(code_label)

            # Interaction Logic
            t_type = task.get("type")

            if t_type == "fill_blank":
                self.render_fill_blank()
            elif t_type == "true_false":
                self.render_true_false(task)
            else:
                # multiple_choice, predict_output, debug_code, code_output
                self.add_option_buttons(task.get("options", []))

    def render_fill_blank(self):
        self.input = QLineEdit()
        self.input.setObjectName("chatInput") 
        self.input.setPlaceholderText("Complete the code...")
        self.input.returnPressed.connect(self._on_text_submit)
        self.layout.addWidget(self.input)

        submit = QPushButton("Submit Answer")
        submit.setObjectName("taskButton") 
        submit.clicked.connect(self._on_text_submit)
        self.layout.addWidget(submit)
        self.input.setFocus()

    def render_true_false(self, task):
        if "statement" in task and task["statement"] != task.get("question"):
            stmt = QLabel(task["statement"])
            stmt.setWordWrap(True)
            stmt.setStyleSheet("font-style: italic; color: #4b5563; margin-bottom: 10px;")
            self.layout.addWidget(stmt)

        for btn_text, val in [("True", True), ("False", False)]:
            btn = QPushButton(btn_text)
            btn.setObjectName("secondaryButton") # Matches your outlined CSS
            btn.clicked.connect(lambda _, v=val: self.on_answer(v))
            self.layout.addWidget(btn)

    def add_option_buttons(self, options):
        for i, option in enumerate(options):
            text = option["text"] if isinstance(option, dict) else str(option)
            btn = QPushButton(text)
            btn.setObjectName("secondaryButton")
            btn.clicked.connect(lambda _, idx=i: self.on_answer(idx))
            self.layout.addWidget(btn)

    def _on_text_submit(self):
        val = self.input.text().strip()
        if val:
            self.on_answer(val)