from PyQt5.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# --- KOMPONEN LAMA (TETAP UTUH) ---

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
        if not values or sum(values) <= 0:
            self._empty_state("No expense data yet")
            return

        try:
            self.figure.clear()
            self.ax = self.figure.add_subplot(111)
            wedges, texts, autotexts = self.ax.pie(
                values, 
                autopct="%1.1f%%", 
                startangle=90, 
                pctdistance=0.85
            )
            self.ax.legend(
                wedges, 
                labels,
                title="Categories",
                loc="center left",
                bbox_to_anchor=(1, 0, 0.5, 1)
            )
            self.ax.set_title(title)
            self.figure.tight_layout()
            self.draw()
        except Exception as e:
            print(f"Chart Error: {e}")
            self._empty_state("Error rendering chart")
            
    def plot_bar(self, labels, values, title="Income vs Expense"):
        if not values or sum(values) == 0:
            self._empty_state("No income / expense data yet")
            return

        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        colors = []
        for label in labels:
            if label.lower() == 'income': colors.append('#2ecc71')
            elif label.lower() == 'expense': colors.append('#e74c3c')
            else: colors.append('#3498db')

        self.ax.bar(labels, values, color=colors)
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

# --- STYLESHEET LENGKAP (DITAMBAHKAN TANPA PANGKAS) ---

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
        min-width: 110px;
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
        border: 2px dashed #2948a2;
        border-radius: 12px;
        background-color: #f0f4f8; 
        color: #2948a2;
    }

    #previewActive {
        border: 2px solid #2948a2;
        border-radius: 12px;
        background-color: #1a1a1a; 
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

    /* --- TAMBAHAN BARU UNTUK LIVE RECEIPT --- */
    #receipt_card {
        background-color: #ebf8ff;
        border: 1px solid #bee3f8;
        border-radius: 15px;
        padding: 20px;
    }

    #receipt_content {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 15px;
        color: #4a5568;
        font-size: 13px;
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

    QComboBox, QLineEdit {
        min-height: 22px;
    }
    """