from PyQt5.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class SummaryCard(QFrame):
    def __init__(self, title: str, value: str, subtitle: str = ""):
        super().__init__()
        self.setObjectName("card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")

        self.value_label = QLabel(value)
        self.value_label.setObjectName("cardValue")

        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("cardSubtitle")

        layout.addWidget(title_label)
        layout.addWidget(self.value_label)
        if subtitle:
            layout.addWidget(subtitle_label)


class SectionBox(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setObjectName("section")
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(18, 16, 18, 16)
        self.root_layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        self.root_layout.addWidget(title_label)

    def add_widget(self, widget: QWidget):
        self.root_layout.addWidget(widget)

    def add_layout(self, layout):
        self.root_layout.addLayout(layout)


class ChartCanvas(FigureCanvas):
    def __init__(self, width=4, height=3, dpi=100):
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.figure.add_subplot(111)
        super().__init__(self.figure)
        self.figure.patch.set_facecolor("white")

    def _empty_state(self, title="No data yet"):
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self.ax.axis("off")
        self.ax.text(0.5, 0.5, title, ha="center", va="center", fontsize=12)
        self.draw()

    def plot_pie(self, labels, values, title="Expense by Category"):
        if not values:
            self._empty_state("No expense data yet")
            return

        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self.ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        self.ax.set_title(title)
        self.figure.tight_layout()
        self.draw()

    def plot_bar(self, labels, values, title="Income vs Expense"):
        if not values or sum(values) == 0:
            self._empty_state("No income / expense data yet")
            return

        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self.ax.bar(labels, values)
        self.ax.set_title(title)
        self.ax.set_ylabel("Amount")
        self.figure.tight_layout()
        self.draw()

    def plot_line(self, labels, values, title="Expense Trend"):
        if not values:
            self._empty_state("No trend data yet")
            return

        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self.ax.plot(labels, values, marker="o")
        self.ax.set_title(title)
        self.ax.set_ylabel("Amount")
        self.ax.tick_params(axis="x", rotation=25)
        self.figure.tight_layout()
        self.draw()


def app_stylesheet():
    return """
    QMainWindow, QWidget {
        background: #f4f8fb;
        color: #223548;
        font-size: 14px;
    }

    #sidebar {
        background: white;
        border-right: 1px solid #dde6ee;
    }

    #brand {
        font-size: 26px;
        font-weight: 700;
        color: #0f7a8a;
        padding: 8px 6px 18px 6px;
    }

    #nav {
        border: none;
        background: transparent;
        outline: none;
    }

    #nav::item {
        padding: 14px 16px;
        border-radius: 14px;
        margin-bottom: 6px;
    }

    #nav::item:selected {
        background: #dff4f1;
        color: #0d6d63;
        font-weight: 600;
    }

    #topbar {
        background: white;
        border-bottom: 1px solid #dde6ee;
    }

    QPushButton {
        background: #0f7a8a;
        color: white;
        border: none;
        padding: 11px 16px;
        border-radius: 12px;
        font-weight: 600;
    }

    QPushButton:hover {
        background: #0c6875;
    }

    QLineEdit, QTextEdit, QComboBox, QDateEdit {
        background: white;
        border: 1px solid #d7e2ea;
        border-radius: 12px;
        padding: 9px 10px;
    }

    QTableWidget {
        background: white;
        border: 1px solid #d7e2ea;
        border-radius: 12px;
        gridline-color: #ecf1f5;
    }

    QHeaderView::section {
        background: #eef5f8;
        padding: 9px;
        border: none;
        border-bottom: 1px solid #d7e2ea;
        font-weight: 600;
    }

    #card, #section {
        background: white;
        border: 1px solid #dbe4ec;
        border-radius: 18px;
    }

    #cardTitle {
        color: #5c7081;
        font-size: 13px;
    }

    #cardValue {
        font-size: 30px;
        font-weight: 700;
        color: #1e3344;
    }

    #cardSubtitle {
        color: #16a34a;
        font-size: 13px;
        font-weight: 600;
    }

    #sectionTitle {
        color: #0f7a8a;
        font-size: 18px;
        font-weight: 700;
    }

    #pageTitle {
        color: #0f7a8a;
        font-size: 28px;
        font-weight: 700;
    }

    #pageSubtitle {
        color: #66798a;
        font-size: 15px;
    }

    #placeholder {
        background: #081a3a;
        border-radius: 22px;
        color: #d7e4f7;
        font-size: 16px;
        border: none;
    }

    #tipBox {
        background: #eef4ff;
        border: 1px solid #d7e4ff;
        border-radius: 16px;
        padding: 14px;
    }

    #userBubble {
        background: #0f7a8a;
        color: white;
        border-radius: 18px;
        padding: 8px 12px;
        max-width: 320px;
    }

    #aiBubble {
        background: #eef5f8;
        color: #203444;
        border-radius: 18px;
        padding: 8px 12px;
        max-width: 320px;
        border: 1px solid #d8e1e8;
    }

    QScrollArea {
        border: none;
        background: transparent;
    }
    QFormLayout QLabel {
    font-weight: 600;
    color: #334a5c;
}

QTextEdit {
    padding: 10px;
}

QComboBox {
    min-height: 22px;
}

QLineEdit {
    min-height: 22px;
}
QPushButton {
    min-width: 110px;
}

    
    """