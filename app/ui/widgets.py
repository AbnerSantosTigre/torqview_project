from PyQt5.QtWidgets import QPushButton

class BotaoArredondado(QPushButton):
    def __init__(self, texto, parent=None):
        super().__init__(texto, parent)
        self.setFixedHeight(100)
        self.setMinimumWidth(200)
        self.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                border-radius: 25px;
                border: none;
                padding: 0 15px;
                font-weight: bold;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #ff4c4c;
            }
            QToolTip {
                font-size: 14px;
                background-color: #333;
                color: white;
                padding: 5px;
                border-radius: 4px;
            }
        """)