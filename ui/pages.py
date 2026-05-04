import csv
import speech_recognition as sr

from PyQt5.QtCore import Qt, QDate, QTimer
from PyQt5.QtGui import QPixmap, QDoubleValidator
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QScrollArea,
    QFrame,
    QAbstractItemView,
    QSizePolicy,
)

from database import (
    add_transaction,
    delete_transaction,
    get_summary,
    get_transactions,
    update_transaction,
    get_expense_by_category,
    get_income_vs_expense,
    get_daily_expense_trend,
)
from services import advisor_reply, scan_receipt, suggest_category, parse_voice_transaction
from ui.components import SectionBox, SummaryCard, ChartCanvas


class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()

        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(20, 20, 20, 20)
        self.outer.setSpacing(16)

        header = QLabel("Dashboard")
        header.setObjectName("pageTitle")
        self.outer.addWidget(header)

        self.cards_layout = QGridLayout()
        self.cards_layout.setHorizontalSpacing(14)
        self.cards_layout.setVerticalSpacing(14)

        self.income_card = SummaryCard("Total Income", "₺0.00")
        self.expense_card = SummaryCard("Total Expense", "₺0.00")
        self.balance_card = SummaryCard("Balance", "₺0.00")
        self.count_card = SummaryCard("Transactions", "0")

        self.cards_layout.addWidget(self.income_card, 0, 0)
        self.cards_layout.addWidget(self.expense_card, 0, 1)
        self.cards_layout.addWidget(self.balance_card, 0, 2)
        self.cards_layout.addWidget(self.count_card, 0, 3)
        self.outer.addLayout(self.cards_layout)

        chart_row = QHBoxLayout()
        chart_row.setSpacing(16)

        pie_box = SectionBox("Expense by Category")
        self.pie_chart = ChartCanvas(width=4, height=3)
        pie_box.add_widget(self.pie_chart)

        bar_box = SectionBox("Income vs Expense")
        self.bar_chart = ChartCanvas(width=4, height=3)
        bar_box.add_widget(self.bar_chart)

        chart_row.addWidget(pie_box, 1)
        chart_row.addWidget(bar_box, 1)
        self.outer.addLayout(chart_row)

        # --- BLOCK EXPENSE TREND (Tetap Terjaga) ---
        # trend_box = SectionBox("Expense Trend")
        # self.line_chart = ChartCanvas(width=8, height=3)
        # trend_box.add_widget(self.line_chart)
        # self.outer.addWidget(trend_box)
        # ---------------------------

        recent_box = SectionBox("Recent Transactions")
        
        # Kolom disetel ke 6 untuk mengakomodasi "Note"
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Store", "Amount", "Category", "Date", "Note", "Type"])
        
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        recent_box.add_widget(self.table)
        
        self.outer.addWidget(recent_box, 1) 

        self.refresh_data()

    def refresh_data(self):
        # Memastikan data terbaru ditarik dari database setiap kali fungsi dipanggil
        summary = get_summary()
        self.income_card.value_label.setText(f"₺{summary['income']:.2f}")
        self.expense_card.value_label.setText(f"₺{summary['expense']:.2f}")
        self.balance_card.value_label.setText(f"₺{summary['balance']:.2f}")
        self.count_card.value_label.setText(str(summary["count"]))

        self.table.setAlternatingRowColors(True)

        # Ambil transaksi terbaru
        rows = get_transactions()[:10]
        self.table.setRowCount(len(rows))

        for r, row in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(str(row["store_name"])))
            self.table.setItem(r, 1, QTableWidgetItem(f"₺{row['amount']:.2f}"))
            self.table.setItem(r, 2, QTableWidgetItem(str(row["category"])))
            self.table.setItem(r, 3, QTableWidgetItem(str(row["date"])))
            
            # --- PERBAIKAN SINKRONISASI NOTE ---
            # Kita sesuaikan urutan pengecekan agar 'note' yang baru diupdate lebih diutamakan
            note_val = "-"
            keys = row.keys()
            
            # Cek 'note' dulu karena ini yang biasanya diisi di form update terbaru
            if "note" in keys and row["note"] and str(row["note"]).strip() != "":
                note_val = row["note"]
            elif "description" in keys and row["description"] and str(row["description"]).strip() != "":
                note_val = row["description"]
            
            self.table.setItem(r, 4, QTableWidgetItem(str(note_val)))
            # ----------------------------------
            
            # Kolom Type (index 5)
            type_text = str(row["type"]).capitalize()
            type_item = QTableWidgetItem(type_text)
            
            if row["type"].lower() == "income":
                type_item.setForeground(QColor("#2ecc71"))
            else:
                type_item.setForeground(QColor("#e74c3c"))
                
            self.table.setItem(r, 5, type_item)

        from PyQt5.QtWidgets import QHeaderView
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(False)

        category_rows = get_expense_by_category()
        pie_labels = [row["category"] for row in category_rows]
        pie_values = [row["total"] for row in category_rows]
        self.pie_chart.plot_pie(pie_labels, pie_values)

        compare = get_income_vs_expense()
        self.bar_chart.plot_bar(
            ["Income", "Expense"],
            [compare["income"], compare["expense"]],
        )

        # --- BLOCK LOGIC LINE CHART (Tetap Terjaga) ---
        # trend_rows = get_daily_expense_trend()
        # line_labels = [row["date"][5:] for row in trend_rows]
        # line_values = [row["total"] for row in trend_rows]
        # self.line_chart.plot_line(line_labels, line_values)
        # ------------------------------

class ScanPage(QWidget):
    def __init__(self, refresh_callback):
        super().__init__()
        self.refresh_callback = refresh_callback
        self.current_image_path = None
        
        # AKTIFKAN DRAG & DROP
        self.setAcceptDrops(True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(16)

        # Header Tetap di Atas
        title = QLabel("Upload Receipt")
        title.setObjectName("pageTitle")
        outer.addWidget(title)

        subtitle = QLabel("Upload a clear receipt image to automatically extract transaction details")
        subtitle.setObjectName("pageSubtitle")
        outer.addWidget(subtitle)

        # --- LAYOUT HORIZONTAL UTAMA (SPLIT SCREEN) ---
        main_content_layout = QHBoxLayout()
        main_content_layout.setSpacing(20)

        # --- SISI KIRI: Visual & Preview ---
        left_side = QVBoxLayout()
        
        preview_box = SectionBox("Receipt Preview")
        self.preview = QLabel("🧾\n\nUpload or Drag & Drop receipt image here")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setFixedHeight(350) # Lebih tinggi agar struk jelas
        self.preview.setObjectName("placeholder")
        self.preview.setWordWrap(True)
        preview_box.add_widget(self.preview)
        left_side.addWidget(preview_box)

        self.upload_btn = QPushButton("Upload Receipt Image")
        self.upload_btn.clicked.connect(self.handle_upload)
        left_side.addWidget(self.upload_btn)

        # Tips diletakkan di sisi kiri bawah
        tips_box = QFrame()
        tips_box.setObjectName("tipBox")
        tips_layout = QVBoxLayout(tips_box)
        tips_layout.setContentsMargins(16, 16, 16, 16)

        tips_title = QLabel("🧾 Tips for better upload")
        tips_title.setStyleSheet("font-weight: 700; color: #2948a2;")
        tips_text = QLabel(
            "• Use close-up photos\n"
            "• Ensure bright lighting\n"
            "• Crop unnecessary edges"
        )
        tips_text.setStyleSheet("color: #2948a2;")
        tips_layout.addWidget(tips_title)
        tips_layout.addWidget(tips_text)
        left_side.addWidget(tips_box)
        left_side.addStretch()

        # --- SISI KANAN: Form & OCR Text ---
        right_side = QVBoxLayout()
        right_side.setSpacing(20) # Jarak antar Box (Confirm Data vs OCR) biar lega

        form_box = SectionBox("Confirm Data")
        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(14)

        # Inisialisasi Input
        self.store_input = QLineEdit()
        self.amount_input = QLineEdit()
        self.category_combo = QComboBox()
        self.category_combo.addItems(["Grocery", "Food", "Transport", "Shopping", "Allowance", "Salary", "Other"])
        
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        
        self.note_input = QLineEdit()

        # Tambah ke Form
        form.addRow("Store Name", self.store_input)
        form.addRow("Amount", self.amount_input)
        form.addRow("Category", self.category_combo)
        form.addRow("Date", self.date_edit)
        form.addRow("Note", self.note_input)
        form_box.add_layout(form)

        # Tombol Save dengan Style Modern
        save_btn = QPushButton("Confirm & Save")
        save_btn.setCursor(Qt.PointingHandCursor) # Kursor jadi tangan saat hover
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #0d9488; 
                color: white;
                font-weight: bold;
                border-radius: 8px;
                padding: 10px 24px;
                min-width: 140px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #0f766e;
            }
            QPushButton:pressed {
                background-color: #134e4a;
            }
        """)
        save_btn.clicked.connect(self.handle_save)
        
        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(save_btn)
        form_box.add_layout(actions)
        
        right_side.addWidget(form_box)

        # OCR Text Box (Sisi kanan bawah)
        ocr_box = SectionBox("OCR Text Raw")
        self.ocr_text = QTextEdit()
        self.ocr_text.setReadOnly(True)
        self.ocr_text.setMinimumHeight(120)
        
        # Style dikit buat OCR Box biar teksnya nggak terlalu mepet border
        self.ocr_text.setStyleSheet("padding: 8px; background-color: #f9fafb;") 
        
        ocr_box.add_widget(self.ocr_text)
        right_side.addWidget(ocr_box)
        
        right_side.addStretch() # Biar konten nempel ke atas, nggak melayang di tengah

        # Gabungkan Kiri (4) dan Kanan (5)
        main_content_layout.addLayout(left_side, 4)
        main_content_layout.addLayout(right_side, 5)

        outer.addLayout(main_content_layout)

   # --- LOGIKA VISUAL & EVENT ---
    def set_preview_image(self, image_path):
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.preview.setText("❌ Failed to load image")
            return

        self.preview.setObjectName("previewActive")
        self.preview.style().unpolish(self.preview)
        self.preview.style().polish(self.preview)

        scaled = pixmap.scaled(
            self.preview.width() - 20,
            self.preview.height() - 20,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.preview.setPixmap(scaled)
        self.preview.setText("") 

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            file_path = files[0]
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                self.current_image_path = file_path
                self.set_preview_image(file_path)
                self.process_receipt(file_path)

    def handle_upload(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Receipt", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if not file_path:
            return
        self.current_image_path = file_path
        self.set_preview_image(file_path)
        self.process_receipt(file_path)

    def process_receipt(self, file_path):
        # --- 1. LOADING STATE START ---
        self.upload_btn.setEnabled(False)
        self.upload_btn.setText("Scanning Receipt... ⏳")
        self.ocr_text.setPlainText("AI is analyzing your receipt image, please wait...")
        QApplication.setOverrideCursor(Qt.WaitCursor) 
        
        try:
            # Fungsi OCR asli
            result = scan_receipt(file_path)
            
            # --- 2. HIGHLIGHT LOGIC ---
            # Style untuk menandai field yang terisi otomatis
            highlight = "background-color: #fef9c3; border: 1px solid #eab308; border-radius: 5px; padding: 5px;"
            
            # Isi data ke form & kasih highlight
            if result.get("store_name"):
                self.store_input.setText(result["store_name"])
                self.store_input.setStyleSheet(highlight)

            if result.get("amount", 0) > 0:
                self.amount_input.setText(f"{result['amount']:.2f}")
                self.amount_input.setStyleSheet(highlight)

            self.ocr_text.setPlainText(result.get("ocr_text", ""))

            qdate = QDate.fromString(result.get("date", ""), "yyyy-MM-dd")
            if qdate.isValid():
                self.date_edit.setDate(qdate)
                self.date_edit.setStyleSheet(highlight)

            idx = self.category_combo.findText(result.get("category", "Other"))
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)
                self.category_combo.setStyleSheet(highlight)

            # Timer untuk mereset warna highlight setelah 2 detik
            QTimer.singleShot(2000, self.reset_input_styles)
                
        except Exception as e:
            QMessageBox.critical(self, "OCR Error", f"Gagal membaca struk: {str(e)}")
        
        finally:
            # --- 3. LOADING STATE END ---
            self.upload_btn.setEnabled(True)
            self.upload_btn.setText("Upload Receipt Image")
            QApplication.restoreOverrideCursor()

    def reset_input_styles(self):
        """Kembalikan style input ke default (putih)"""
        default_style = "background-color: white; border: 1px solid #e2e8f0; border-radius: 5px; padding: 5px;"
        self.store_input.setStyleSheet(default_style)
        self.amount_input.setStyleSheet(default_style)
        self.date_edit.setStyleSheet(default_style)
        self.category_combo.setStyleSheet(default_style)

    def handle_save(self):
        # Definisikan style untuk error dan default
        error_style = "border: 2px solid #ef4444; background-color: #fef2f2; border-radius: 5px; padding: 5px;"
        default_style = "background-color: white; border: 1px solid #e2e8f0; border-radius: 5px; padding: 5px;"
        
        try:
            store = self.store_input.text().strip()
            amount_text = self.amount_input.text().strip()

            # --- VALIDASI & HIGHLIGHT ERROR ---
            # Reset ke style default dulu sebelum dicek
            self.store_input.setStyleSheet(default_style)
            self.amount_input.setStyleSheet(default_style)
            
            is_valid = True
            if not store:
                self.store_input.setStyleSheet(error_style)
                is_valid = False
            if not amount_text:
                self.amount_input.setStyleSheet(error_style)
                is_valid = False

            if not is_valid:
                QMessageBox.warning(self, "Warning", "Store and Amount are required.")
                return

            amount = float(amount_text)
            category = self.category_combo.currentText()
            note = self.note_input.text().strip()
            date = self.date_edit.date().toString("yyyy-MM-dd")

            # Fungsi save asli
            add_transaction(store, amount, category, note, date, "expense", self.current_image_path)
            QMessageBox.information(self, "Saved", "Transaction saved successfully.")
            self.refresh_callback()

            # Reset UI ke kondisi awal
            self.store_input.clear()
            self.amount_input.clear()
            self.note_input.clear()
            self.ocr_text.clear()
            self.category_combo.setCurrentIndex(0)
            self.date_edit.setDate(QDate.currentDate())
            self.current_image_path = None
            self.preview.clear()
            self.preview.setObjectName("placeholder")
            self.reset_input_styles() # Memastikan semua balik ke style default
            self.preview.style().unpolish(self.preview)
            self.preview.style().polish(self.preview)
            self.preview.setText("🧾\n\nUpload or Drag & Drop receipt image here")
            
        except ValueError:
            self.amount_input.setStyleSheet(error_style) # Kasih merah kalau input bukan angka
            QMessageBox.warning(self, "Warning", "Amount must be a number.")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))
            
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
                             QLineEdit, QTextEdit, QDateEdit, QPushButton, QFormLayout, 
                             QFrame, QApplication, QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QPixmap

class ManualInputPage(QWidget):
    def __init__(self, refresh_callback):
        super().__init__()
        self.refresh_callback = refresh_callback

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(16)

        title = QLabel("Manual Input")
        title.setObjectName("pageTitle")
        outer.addWidget(title)

        # POIN 1: Konsistensi Bahasa (English)
        subtitle = QLabel("Add income or expense manually, or use voice input for faster entry")
        subtitle.setObjectName("pageSubtitle")
        outer.addWidget(subtitle)

        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        # =========================
        # LEFT SIDE: FORM BOX
        # =========================
        from ui.components import SectionBox 
        form_box = SectionBox("Add Transaction")

        self.trans_type = QComboBox()
        self.trans_type.addItems(["expense", "income"])

        self.store_input = QLineEdit()
        self.store_input.setPlaceholderText("Example: Migros, Starbucks, Salary")

        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("Example: 120.50")
        
        # --- POIN 1: VALIDASI ANGKA (Tetap Ada) ---
        validator = QDoubleValidator(0.0, 999999.99, 2)
        validator.setNotation(QDoubleValidator.StandardNotation)
        self.amount_input.setValidator(validator)

        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "AUTO", "Grocery", "Food", "Transport", 
            "Shopping", "Allowance", "Salary", "Other",
        ])

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())

        self.note_input = QTextEdit()
        self.note_input.setPlaceholderText("Optional notes...")
        self.note_input.setMaximumHeight(110)

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(16)
        form.addRow("Type", self.trans_type)
        form.addRow("Store / Source", self.store_input)
        form.addRow("Amount", self.amount_input)
        form.addRow("Category", self.category_combo)
        form.addRow("Date", self.date_edit)
        form.addRow("Note", self.note_input)
        form_box.add_layout(form)

        button_row = QHBoxLayout()
        button_row.setSpacing(12)
        self.voice_btn = QPushButton("🎤 Voice Input")
        self.voice_btn.clicked.connect(self.handle_voice_input)
        
        # POIN 2: Button Priority (Styling)
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("clearBtn")
        clear_btn.clicked.connect(self.clear_form)
        clear_btn.setStyleSheet("""
            QPushButton#clearBtn {
                background-color: #f3f4f6;
                color: #4b5563;
                border: 1px solid #d1d5db;
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton#clearBtn:hover { background-color: #e5e7eb; }
        """)

        save_btn = QPushButton("Save Transaction")
        save_btn.setObjectName("saveBtn")
        save_btn.clicked.connect(self.handle_save)
        save_btn.setStyleSheet("""
            QPushButton#saveBtn {
                background-color: #0d9488;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 6px;
            }
            QPushButton#saveBtn:hover { background-color: #0f766e; }
        """)

        button_row.addWidget(self.voice_btn)
        button_row.addWidget(clear_btn)
        button_row.addStretch()
        button_row.addWidget(save_btn)
        form_box.add_layout(button_row)

        # =========================
        # RIGHT SIDE: RECEIPT PREVIEW & VOICE
        # =========================
        helper_box = SectionBox("Live Receipt Preview")

        self.receipt_card = QFrame()
        self.receipt_card.setObjectName("receipt_card")
        receipt_layout = QVBoxLayout(self.receipt_card)

        # POIN 4: Empty State Style (Bahasa Inggris & Miring)
        self.receipt_content = QLabel("Start typing to see the summary...")
        self.receipt_content.setObjectName("receipt_content")
        self.receipt_content.setWordWrap(True)
        self.receipt_content.setAlignment(Qt.AlignCenter)
        self.receipt_content.setStyleSheet("color: #a0aec0; font-style: italic;")
        receipt_layout.addWidget(self.receipt_content)

        # --- TOMBOL DOWNLOAD STRUK ---
        self.download_btn = QPushButton("💾 Download Receipt")
        self.download_btn.setObjectName("downloadBtn") 
        self.download_btn.clicked.connect(self.handle_download_receipt)

        self.voice_result = QTextEdit()
        self.voice_result.setReadOnly(True)
        # POIN 3: Placeholder Recognized Text
        self.voice_result.setPlaceholderText("Recognized voice text will appear here... Click 'Voice Input' to start.")
        self.voice_result.setMaximumHeight(120)

        helper_box.add_widget(self.receipt_card)
        helper_box.add_widget(self.download_btn) 
        
        # Pemanis Label Recognized Text
        voice_label = QLabel("🎤 Recognized Text:")
        voice_label.setStyleSheet("font-weight: bold; margin-top: 10px; color: #4a5568;")
        helper_box.add_widget(voice_label)
        helper_box.add_widget(self.voice_result)

        # Sinyal untuk Update Real-time (Tetap Ada)
        self.store_input.textChanged.connect(self.update_live_preview)
        self.amount_input.textChanged.connect(self.update_live_preview)
        self.trans_type.currentTextChanged.connect(self.update_live_preview)
        self.category_combo.currentTextChanged.connect(self.update_live_preview)
        self.date_edit.dateChanged.connect(self.update_live_preview)

        top_row.addWidget(form_box, 2)
        top_row.addWidget(helper_box, 1)
        outer.addLayout(top_row)

    def update_live_preview(self):
        # 1. RESET STYLE: Menghilangkan miring (italic) dan warna pudar saat user mulai input
        self.receipt_content.setStyleSheet("font-style: normal; color: #2D3748;")

        # 2. LOGIKA DATA (Tetap seperti aslinya)
        store = self.store_input.text().strip() or "..."
        raw_amount = self.amount_input.text().strip()
        
        try:
            # Memformat angka dengan pemisah ribuan dan 2 desimal
            amount = f"{float(raw_amount):,.2f}" if raw_amount else "0.00"
        except ValueError:
            amount = "0.00"

        trans_type = self.trans_type.currentText().upper()
        category = self.category_combo.currentText()
        date = self.date_edit.date().toString("dd MMM yyyy")

        # 3. HTML CONTENT (Bahasa Inggris & Styling Tegak)
        receipt_html = (
            f"<div style='font-family: monospace; line-height: 1.5; color: #2D3748;'>"
            f"<p style='text-align: center; border-bottom: 1px dashed #555; margin-bottom: 12px; font-weight: bold; color: #1A202C;'>"
            f"TRANSACTION SUMMARY</p>"
            f"<p style='margin: 2px 0;'>TYPE&nbsp;&nbsp;&nbsp;: {trans_type}</p>"
            f"<p style='margin: 2px 0;'>STORE&nbsp;&nbsp;: {store}</p>"
            f"<p style='margin: 2px 0;'>AMOUNT&nbsp;: ₺{amount}</p>"
            f"<p style='margin: 2px 0;'>CAT&nbsp;&nbsp;&nbsp;&nbsp;: {category}</p>"
            f"<p style='margin: 2px 0;'>DATE&nbsp;&nbsp;&nbsp;: {date}</p>"
            f"<p style='text-align: center; border-top: 1px dashed #555; margin-top: 12px; color: #718096;'>"
            f"<small>*** READY TO SAVE ***</small></p>"
            f"</div>"
        )
        self.receipt_content.setText(receipt_html)

    def handle_download_receipt(self):
        """Mengambil screenshot area receipt_card dan menyimpannya sebagai gambar."""
        # Membersihkan nama toko dari spasi agar aman untuk sistem file
        raw_store = self.store_input.text().strip() or "Receipt"
        store_name = raw_store.replace(" ", "_")
        
        # Menambahkan tanggal ke nama file otomatis (format: yyyyMMdd)
        current_date = QDate.currentDate().toString("yyyyMMdd")
        
        # Nama file default otomatis: Struk_Bim_20260504.png
        default_name = f"Struk_{store_name}_{current_date}.png"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Save Receipt Image", 
            default_name, 
            "PNG Files (*.png);;JPG Files (*.jpg)"
        )

        if file_path:
            try:
                # Grab hanya bagian frame struk (receipt_card)
                pixmap = self.receipt_card.grab()
                pixmap.save(file_path)
                QMessageBox.information(self, "Success", "Struk berhasil disimpan sebagai gambar!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal mengunduh struk: {e}")

    def handle_voice_input(self):
        import speech_recognition as sr
        from ui.utils.voice_parser import parse_voice_transaction
        recognizer = sr.Recognizer()
        try:
            self.voice_btn.setText("Listening...")
            QApplication.processEvents()

            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=7)

            text = recognizer.recognize_google(audio, language="en-US")
            self.voice_result.setPlainText(text)
            parsed = parse_voice_transaction(text)

            if parsed["type"]:
                idx = self.trans_type.findText(parsed["type"])
                if idx >= 0: self.trans_type.setCurrentIndex(idx)

            if parsed["store"]: self.store_input.setText(parsed["store"])

            if parsed["amount"] is not None:
                self.amount_input.setText(f"{parsed['amount']:.2f}")

            if parsed["category"]:
                idx = self.category_combo.findText(parsed["category"])
                if idx >= 0: self.category_combo.setCurrentIndex(idx)

            if parsed["note"]: self.note_input.setPlainText(parsed["note"])
            
            self.update_live_preview()

        except Exception as e:
            QMessageBox.warning(self, "Voice Input", str(e))
        finally:
            self.voice_btn.setText("🎤 Voice Input")

    def handle_save(self):
        import sys
        import os
        import importlib.util
        from PyQt5.QtWidgets import QMessageBox, QApplication

        # 1. SETUP PATHS
        # Mencari root path (satu level di atas folder UI)
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        db_path = os.path.join(root_path, "database.py")
        utils_path = os.path.join(root_path, "utils", "categorizer.py")

        try:
            # 2. IMPORT DATABASE (Pakai importlib biar nggak bentrok sama folder 'database/')
            spec_db = importlib.util.spec_from_file_location("database_mod", db_path)
            db_mod = importlib.util.module_from_spec(spec_db)
            spec_db.loader.exec_module(db_mod)
            add_transaction = db_mod.add_transaction

            # 3. AMBIL DATA DARI UI
            trans_type = self.trans_type.currentText().lower() # database.py biasanya minta lowercase
            store = self.store_input.text().strip() or "Unknown"
            amount_text = self.amount_input.text().strip()
            note = self.note_input.toPlainText().strip()
            category = self.category_combo.currentText()
            date = self.date_edit.date().toString("yyyy-MM-dd")

            if not amount_text:
                QMessageBox.warning(self, "Warning", "Amount is required.")
                return

            # Konversi nominal
            amount = float(amount_text.replace(',', '')) 
            
            # 4. HANDLE CATEGORIZER (AUTO)
            if category == "AUTO":
                try:
                    # Coba import categorizer pakai importlib biar aman dari error path
                    if os.path.exists(utils_path):
                        spec_util = importlib.util.spec_from_file_location("cat_mod", utils_path)
                        cat_mod = importlib.util.module_from_spec(spec_util)
                        spec_util.loader.exec_module(cat_mod)
                        category = cat_mod.suggest_category(store, note)
                    else:
                        category = "Uncategorized"
                except:
                    category = "Uncategorized"

            # 5. EKSEKUSI SIMPAN (Sesuai urutan parameter di database.py lu)
            # Parameter: store_name, amount, category, note, date, trans_type
            add_transaction(store, amount, category, note, date, trans_type)
            
            # 6. FEEDBACK VISUAL & RESET
            success_html = (
                "<div style='text-align: center; padding: 20px;'>"
                "<h2 style='color: #16a34a; margin-bottom: 5px;'>✔ SAVED</h2>"
                "<p style='color: #4a5568;'>Transaction added to database!</p>"
                "</div>"
            )
            self.receipt_content.setText(success_html)
            QApplication.processEvents()
            
            import time
            time.sleep(0.6)

            # Reset Form
            self.clear_form()
            
            # Refresh Dashboard (Jika ada fungsi callback)
            if hasattr(self, 'refresh_callback') and self.refresh_callback:
                self.refresh_callback() 
            
            # Popup Sukses (CUMA SATU KALI)
            QMessageBox.information(self, "Saved", "Transaction saved successfully.")

        except Exception as e:
            # Error hanya muncul jika ada kegagalan sistem/database
            QMessageBox.critical(self, "Error", f"Gagal simpan: {str(e)}")

    def clear_form(self):
        self.trans_type.setCurrentIndex(0)
        self.store_input.clear()
        self.amount_input.clear()
        self.category_combo.setCurrentIndex(0)
        self.date_edit.setDate(QDate.currentDate())
        self.note_input.clear()
        self.voice_result.clear()
        self.update_live_preview()

class TransactionsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_id = None
        self.rows_cache = []

        # Main Layout Utama
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(16)

        # 1. HEADER ROW (Title & Export)
        title_row = QHBoxLayout()
        title = QLabel("Transactions")
        title.setObjectName("pageTitle")

        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self.export_transactions_csv)

        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(export_btn)
        outer.addLayout(title_row)

        # 2. FILTER BOX (Dibuat lebih compact agar tidak makan tempat vertikal)
        filter_box = SectionBox("Filter & Search")
        filters = QGridLayout()

        self.type_combo = QComboBox()
        self.type_combo.addItems(["All", "expense", "income"])

        self.category_combo = QComboBox()
        self.category_combo.addItems(["All", "Grocery", "Food", "Transport", "Shopping", "Allowance", "Salary", "Other"])

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")

        filters.addWidget(QLabel("Type"), 0, 0)
        filters.addWidget(self.type_combo, 0, 1)
        filters.addWidget(QLabel("Category"), 0, 2)
        filters.addWidget(self.category_combo, 0, 3)
        filters.addWidget(QLabel("Search"), 0, 4) # Pindah ke baris yang sama
        filters.addWidget(self.search_input, 0, 5)
        
        # Tombol Filter tetap ada semua
        apply_btn = QPushButton("Apply Filter")
        reset_btn = QPushButton("Reset")
        delete_btn = QPushButton("Delete Selected")

        apply_btn.clicked.connect(self.refresh_data)
        reset_btn.clicked.connect(self.reset_filter)
        delete_btn.clicked.connect(self.delete_selected)

        filters.addWidget(apply_btn, 0, 6)
        filters.addWidget(reset_btn, 0, 7)
        filters.addWidget(delete_btn, 0, 8)
        
        filter_box.add_layout(filters)
        outer.addWidget(filter_box)

        # --- 3. MAIN CONTENT AREA (Horizontal Split: 70% Tabel, 30% Edit Form) ---
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # SISI KIRI: TABEL (Dibuat Expand)
        table_container = QVBoxLayout()
        table_box = SectionBox("All Transactions")
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["ID", "Store", "Amount", "Category", "Date", "Type"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows) # Biar pilih sebaris penuh
        self.table.itemSelectionChanged.connect(self.load_selected_into_form)
        
        # PENTING: Set policy biar tabelnya narik ke bawah maksimal
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setMinimumHeight(400) 

        table_box.add_widget(self.table)
        table_container.addWidget(table_box)

        # SISI KANAN: EDIT FORM (Sidebar style)
        edit_container = QVBoxLayout()
        edit_box = SectionBox("Edit Selected Transaction")
        edit_form = QFormLayout()

        self.edit_store = QLineEdit()
        self.edit_amount = QLineEdit()
        self.edit_category = QComboBox()
        self.edit_category.addItems(["Grocery", "Food", "Transport", "Shopping", "Allowance", "Salary", "Other"])
        self.edit_date = QDateEdit()
        self.edit_date.setCalendarPopup(True)
        self.edit_date.setDate(QDate.currentDate())
        self.edit_type = QComboBox()
        self.edit_type.addItems(["expense", "income"])
        self.edit_note = QTextEdit()
        self.edit_note.setMaximumHeight(120) # Sedikit lebih tinggi biar enak ngetik

        edit_form.addRow("Store", self.edit_store)
        edit_form.addRow("Amount", self.edit_amount)
        edit_form.addRow("Category", self.edit_category)
        edit_form.addRow("Date", self.edit_date)
        edit_form.addRow("Type", self.edit_type)
        edit_form.addRow("Note", self.edit_note)
        edit_box.add_layout(edit_form)

        # Tombol Update & Clear (Disusun Vertikal biar pas di sidebar)
        edit_btn_layout = QVBoxLayout()
        self.update_btn = QPushButton("Update Selected")
        self.clear_btn = QPushButton("Clear Edit Form")

        self.update_btn.clicked.connect(self.update_selected_transaction)
        self.clear_btn.clicked.connect(self.clear_edit_form)

        edit_btn_layout.addWidget(self.update_btn)
        edit_btn_layout.addWidget(self.clear_btn)
        edit_box.add_layout(edit_btn_layout)

        edit_container.addWidget(edit_box)
        edit_container.addStretch() # Form tetap nempel di atas, nggak melar aneh

        # Gabungkan Kiri (7) dan Kanan (3)
        content_layout.addLayout(table_container, 7)
        content_layout.addLayout(edit_container, 3)

        outer.addLayout(content_layout)

        # Load data awal
        self.refresh_data()
    def export_transactions_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Transactions",
            "transactions.csv",
            "CSV Files (*.csv)"
        )

        if not file_path:
            return

        if not file_path.endswith(".csv"):
            file_path += ".csv"

        try:
            rows = self.rows_cache

            if not rows:
                QMessageBox.warning(self, "Export CSV", "No transactions to export.")
                return

            with open(file_path, mode="w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)

                writer.writerow([
                    "ID",
                    "Store",
                    "Amount",
                    "Category",
                    "Date",
                    "Type",
                    "Note",
                    "Receipt Image"
                ])

                for row in rows:
                    keys = row.keys()

                    writer.writerow([
                        row["id"],
                        row["store_name"],
                        row["amount"],
                        row["category"],
                        row["date"],
                        row["type"],
                        row["note"] if "note" in keys and row["note"] else "",
                        row["receipt_image"] if "receipt_image" in keys and row["receipt_image"] else "",
                    ])

            QMessageBox.information(
                self,
                "Export CSV",
                "Transactions exported successfully."
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export CSV:\n{str(e)}"
            )

    def refresh_data(self):
        # 1. Ambil data (Logic asli lu tetap terjaga sepenuhnya)
        rows = get_transactions(
            search=self.search_input.text().strip(),
            trans_type=self.type_combo.currentText(),
            category=self.category_combo.currentText(),
        )

        self.rows_cache = rows
        self.table.setRowCount(len(rows))

        # 2. Isi data ke tabel
        for r, row in enumerate(rows):
            # Kolom ID, Store Tetap
            self.table.setItem(r, 0, QTableWidgetItem(str(row["id"])))
            self.table.setItem(r, 1, QTableWidgetItem(row["store_name"]))
            
            # Kolom Amount (Tetap pakai format mata uang ₺)
            self.table.setItem(r, 2, QTableWidgetItem(f"₺{row['amount']:.2f}"))
            
            # Kolom Category & Date Tetap
            self.table.setItem(r, 3, QTableWidgetItem(row["category"]))
            self.table.setItem(r, 4, QTableWidgetItem(row["date"]))
            
            # Kolom Type (Dikasih warna biar gampang bedain Income vs Expense)
            type_text = row["type"].capitalize()
            type_item = QTableWidgetItem(type_text)
            
            # Tambahan visual: Hijau untuk Income, Merah untuk Expense
            # (Pastikan sudah 'from PyQt5.QtGui import QColor')
            if row["type"].lower() == "income":
                type_item.setForeground(QColor("#2ecc71"))
            else:
                type_item.setForeground(QColor("#e74c3c"))
                
            self.table.setItem(r, 5, type_item)

        # 3. Optimasi Ukuran Kolom (Biar pas dengan layout baru)
        header = self.table.horizontalHeader()
        
        # Sesuai request: sesuaikan kolom dengan konten dulu
        self.table.resizeColumnsToContents()
        
        # Optimasi tambahan: Kolom Store (index 1) dibikin narik (Stretch)
        # biar tabelnya full memenuhi area 70% di sisi kiri
        from PyQt5.QtWidgets import QHeaderView
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        
        # Kolom ID (index 0) dibikin pas konten aja biar nggak kegedean
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
    def reset_filter(self):
        self.search_input.clear()
        self.type_combo.setCurrentIndex(0)
        self.category_combo.setCurrentIndex(0)
        self.refresh_data()

    def delete_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Select a row first.")
            return

        tx_id = int(self.table.item(row, 0).text())
        delete_transaction(tx_id)
        self.refresh_data()
        self.clear_edit_form()
        QMessageBox.information(self, "Deleted", "Transaction deleted.")

    def load_selected_into_form(self):
        # 1. Gunakan currentRow() seperti asli lu
        row = self.table.currentRow()
        
        # 2. Validasi index agar tidak out of bounds
        if row < 0 or row >= len(self.rows_cache):
            return

        # 3. Ambil data dari cache (Sesuai urutan yang ditampilkan di tabel)
        selected = self.rows_cache[row]
        self.selected_id = selected["id"]

        # 4. Set widget teks (Store & Amount)
        self.edit_store.setText(str(selected["store_name"]))
        # Pakai :.2f agar format desimalnya konsisten di form edit
        self.edit_amount.setText(f"{selected['amount']:.2f}")

        # 5. Set ComboBox Category
        cat_idx = self.edit_category.findText(selected["category"])
        if cat_idx >= 0:
            self.edit_category.setCurrentIndex(cat_idx)

        # 6. Set ComboBox Type
        type_idx = self.edit_type.findText(selected["type"])
        if type_idx >= 0:
            self.edit_type.setCurrentIndex(type_idx)

        # 7. Set Tanggal (Gunakan QDate untuk validasi)
        from PyQt5.QtCore import QDate
        qdate = QDate.fromString(selected["date"], "yyyy-MM-dd")
        if qdate.isValid():
            self.edit_date.setDate(qdate)
        else:
            self.edit_date.setDate(QDate.currentDate())

        # 8. Set Note / Description (Dibuat lebih tahan banting untuk sqlite3.Row)
        # Karena sqlite3.Row tidak punya .get(), kita akses manual dengan fallback
        note_val = ""
        
        # Cek apakah kolom 'note' ada dan tidak None
        if "note" in selected.keys() and selected["note"]:
            note_val = selected["note"]
        # Jika 'note' kosong/tidak ada, cek 'description'
        elif "description" in selected.keys() and selected["description"]:
            note_val = selected["description"]
            
        self.edit_note.setPlainText(str(note_val))
        
    def update_selected_transaction(self):
        if self.selected_id is None:
            QMessageBox.warning(self, "Warning", "Select a transaction first.")
            return

        try:
            store = self.edit_store.text().strip()
            amount = float(self.edit_amount.text().strip())
            category = self.edit_category.currentText()
            date = self.edit_date.date().toString("yyyy-MM-dd")
            trans_type = self.edit_type.currentText()
            note = self.edit_note.toPlainText().strip()

            if not store:
                QMessageBox.warning(self, "Warning", "Store name required.")
                return

            update_transaction(
                self.selected_id,
                store,
                amount,
                category,
                note,
                date,
                trans_type,
            )
            self.refresh_data()
            QMessageBox.information(self, "Updated", "Transaction updated successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Update Error", str(e))

    def clear_edit_form(self):
        self.selected_id = None
        self.edit_store.clear()
        self.edit_amount.clear()
        self.edit_category.setCurrentIndex(0)
        self.edit_type.setCurrentIndex(0)
        self.edit_date.setDate(QDate.currentDate())
        self.edit_note.clear()


class ChatBubble(QFrame):
    def __init__(self, text, is_user=False):
        super().__init__()
        self.setObjectName("userBubble" if is_user else "aiBubble")
        self.setMaximumWidth(340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(0)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("background: transparent; border: none;")
        label.setTextInteractionFlags(Qt.NoTextInteraction)
        layout.addWidget(label)


class AdvisorPage(QWidget):
    def __init__(self):
        super().__init__()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(16)

        title = QLabel("AI Financial Advisor")
        title.setObjectName("pageTitle")
        outer.addWidget(title)

        profile_box = SectionBox("Advisor Profile")
        profile_text = QLabel(
            "Hello! I'm your AI Financial Advisor. I can help you check your balance, "
            "understand your spending habits, and give simple budgeting tips."
        )
        profile_text.setWordWrap(True)
        profile_box.add_widget(profile_text)

        question_grid = QGridLayout()
        question_grid.setHorizontalSpacing(12)
        question_grid.setVerticalSpacing(12)

        questions = [
            "How is my balance?",
            "What is my biggest expense?",
            "Give me budgeting tips",
            "How much is my income?",
        ]

        for i, question in enumerate(questions):
            btn = QPushButton(question)
            btn.clicked.connect(lambda _, q=question: self.use_default_question(q))
            question_grid.addWidget(btn, i // 2, i % 2)

        profile_box.add_layout(question_grid)
        outer.addWidget(profile_box)

        chat_box = SectionBox("Chat")

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setMinimumHeight(320)
        self.scroll.setMaximumHeight(420)

        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(6, 6, 6, 6)
        self.chat_layout.setSpacing(10)
        self.chat_layout.addStretch()

        self.scroll.setWidget(self.chat_container)
        chat_box.add_widget(self.scroll)

        row = QHBoxLayout()
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("Ask about your balance, income, spending, or tips...")
        send_btn = QPushButton("Send")
        clear_btn = QPushButton("Clear")

        send_btn.clicked.connect(self.send_message)
        clear_btn.clicked.connect(self.clear_chat)

        row.addWidget(self.input_line, 1)
        row.addWidget(send_btn)
        row.addWidget(clear_btn)
        chat_box.add_layout(row)

        outer.addWidget(chat_box)

        self.add_message("Hello! Ask me about balance, income, expenses, or budget tips.", False)

    def add_message(self, text, is_user=False):
        bubble = ChatBubble(text, is_user)

        wrapper = QWidget()
        wrapper_layout = QHBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)

        if is_user:
            wrapper_layout.addStretch()
            wrapper_layout.addWidget(bubble)
        else:
            wrapper_layout.addWidget(bubble)
            wrapper_layout.addStretch()

        self.chat_layout.insertWidget(self.chat_layout.count() - 1, wrapper)

        scrollbar = self.scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def use_default_question(self, question):
        self.input_line.setText(question)
        self.send_message()

    def send_message(self):
        text = self.input_line.text().strip()
        if not text:
            return

        summary = get_summary()
        reply = advisor_reply(summary, text)

        self.add_message(text, True)
        self.add_message(reply, False)
        self.input_line.clear()

    def clear_chat(self):
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.add_message("Hello! Ask me about balance, income, expenses, or budget tips.", False)