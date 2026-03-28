import sys
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication
from database import init_db
from ui.main_window import MainWindow

if __name__ == "__main__":
    init_db()
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())