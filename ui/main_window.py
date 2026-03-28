from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.components import app_stylesheet
from ui.pages import (
    AdvisorPage,
    DashboardPage,
    ManualInputPage,
    ScanPage,
    TransactionsPage,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Quick Expense Tracker")
        self.resize(1400, 900)

        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # =========================
        # SIDEBAR
        # =========================
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(250)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 18, 18, 18)
        sidebar_layout.setSpacing(16)

        brand = QLabel("Quick Expense\nTracker")
        brand.setObjectName("brand")
        sidebar_layout.addWidget(brand)

        self.nav = QListWidget()
        self.nav.setObjectName("nav")

        for item in [
            "Dashboard",
            "Scan Receipt",
            "Manual Input",
            "Transactions",
            "AI Advisor",
        ]:
            QListWidgetItem(item, self.nav)

        self.nav.setCurrentRow(0)
        sidebar_layout.addWidget(self.nav)
        sidebar_layout.addStretch()

        # =========================
        # CONTENT WRAP
        # =========================
        content_wrap = QFrame()
        content_layout = QVBoxLayout(content_wrap)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # =========================
        # TOPBAR
        # =========================
        topbar = QFrame()
        topbar.setObjectName("topbar")

        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(20, 12, 20, 12)
        topbar_layout.setSpacing(12)
        topbar_layout.addStretch()

        notifications_btn = QPushButton("Notifications")
        profile_btn = QPushButton("Profile")

        topbar_layout.addWidget(notifications_btn)
        topbar_layout.addWidget(profile_btn)

        # =========================
        # PAGES
        # =========================
        self.dashboard_page = DashboardPage()
        self.scan_page = ScanPage(self.refresh_all)
        self.manual_page = ManualInputPage(self.refresh_all)
        self.transactions_page = TransactionsPage()
        self.advisor_page = AdvisorPage()

        self.pages = QStackedWidget()
        self.pages.addWidget(self.make_scroll_page(self.dashboard_page))
        self.pages.addWidget(self.make_scroll_page(self.scan_page))
        self.pages.addWidget(self.make_scroll_page(self.manual_page))
        self.pages.addWidget(self.make_scroll_page(self.transactions_page))
        self.pages.addWidget(self.make_scroll_page(self.advisor_page))

        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)

        # =========================
        # FINAL LAYOUT
        # =========================
        content_layout.addWidget(topbar)
        content_layout.addWidget(self.pages)

        root.addWidget(sidebar)
        root.addWidget(content_wrap)

        self.setStyleSheet(app_stylesheet())

    def make_scroll_page(self, widget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(widget)
        return scroll

    def refresh_all(self):
        self.dashboard_page.refresh_data()
        self.transactions_page.refresh_data()