import cv2
import speech_recognition as sr

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QPixmap
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

        trend_box = SectionBox("Expense Trend")
        self.line_chart = ChartCanvas(width=8, height=3)
        trend_box.add_widget(self.line_chart)
        self.outer.addWidget(trend_box)

        recent_box = SectionBox("Recent Transactions")
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Store", "Amount", "Category", "Date", "Type"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        recent_box.add_widget(self.table)
        self.outer.addWidget(recent_box)

        self.refresh_data()

    def refresh_data(self):
        summary = get_summary()
        self.income_card.value_label.setText(f"₺{summary['income']:.2f}")
        self.expense_card.value_label.setText(f"₺{summary['expense']:.2f}")
        self.balance_card.value_label.setText(f"₺{summary['balance']:.2f}")
        self.count_card.value_label.setText(str(summary["count"]))

        rows = get_transactions()[:5]
        self.table.setRowCount(len(rows))

        for r, row in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(row["store_name"]))
            self.table.setItem(r, 1, QTableWidgetItem(f"₺{row['amount']:.2f}"))
            self.table.setItem(r, 2, QTableWidgetItem(row["category"]))
            self.table.setItem(r, 3, QTableWidgetItem(row["date"]))
            self.table.setItem(r, 4, QTableWidgetItem(row["type"]))

        self.table.resizeColumnsToContents()

        category_rows = get_expense_by_category()
        pie_labels = [row["category"] for row in category_rows]
        pie_values = [row["total"] for row in category_rows]
        self.pie_chart.plot_pie(pie_labels, pie_values)

        compare = get_income_vs_expense()
        self.bar_chart.plot_bar(
            ["Income", "Expense"],
            [compare["income"], compare["expense"]],
        )

        trend_rows = get_daily_expense_trend()
        line_labels = [row["date"][5:] for row in trend_rows]
        line_values = [row["total"] for row in trend_rows]
        self.line_chart.plot_line(line_labels, line_values)


class ScanPage(QWidget):
    def __init__(self, refresh_callback):
        super().__init__()
        self.refresh_callback = refresh_callback
        self.current_image_path = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(16)

        title = QLabel("Scan Receipt")
        title.setObjectName("pageTitle")
        outer.addWidget(title)

        subtitle = QLabel("Use OCR to automatically extract transaction details")
        subtitle.setObjectName("pageSubtitle")
        outer.addWidget(subtitle)

        preview_box = SectionBox("Receipt Preview")
        self.preview = QLabel("📷\n\nPosition your receipt within the frame")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setFixedHeight(260)
        self.preview.setObjectName("placeholder")
        preview_box.add_widget(self.preview)
        outer.addWidget(preview_box)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.camera_btn = QPushButton("Scan Receipt")
        self.upload_btn = QPushButton("Upload Image")

        self.camera_btn.clicked.connect(self.handle_camera_scan)
        self.upload_btn.clicked.connect(self.handle_upload)

        btn_row.addWidget(self.camera_btn)
        btn_row.addWidget(self.upload_btn)
        outer.addLayout(btn_row)

        tips_box = QFrame()
        tips_box.setObjectName("tipBox")
        tips_layout = QVBoxLayout(tips_box)
        tips_layout.setContentsMargins(16, 16, 16, 16)

        tips_title = QLabel("📸 Tips for better scanning")
        tips_title.setStyleSheet("font-weight: 700; color: #2948a2;")

        tips_text = QLabel(
            "• Make sure the receipt is well-lit and clearly visible\n"
            "• Avoid shadows and glare on the receipt\n"
            "• Keep the receipt flat and within the frame\n"
            "• Ensure text is readable and not blurry"
        )
        tips_text.setStyleSheet("color: #2948a2;")
        tips_text.setWordWrap(True)

        tips_layout.addWidget(tips_title)
        tips_layout.addWidget(tips_text)
        outer.addWidget(tips_box)

        form_box = SectionBox("Confirm Data")
        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(14)

        self.store_input = QLineEdit()
        self.amount_input = QLineEdit()

        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "Grocery", "Food", "Transport", "Shopping", "Allowance", "Salary", "Other"
        ])

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())

        self.note_input = QLineEdit()

        form.addRow("Store Name", self.store_input)
        form.addRow("Amount", self.amount_input)
        form.addRow("Category", self.category_combo)
        form.addRow("Date", self.date_edit)
        form.addRow("Note", self.note_input)
        form_box.add_layout(form)

        save_btn = QPushButton("Confirm & Save")
        save_btn.clicked.connect(self.handle_save)

        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(save_btn)
        form_box.add_layout(actions)

        outer.addWidget(form_box)

        ocr_box = SectionBox("OCR Text")
        self.ocr_text = QTextEdit()
        self.ocr_text.setReadOnly(True)
        self.ocr_text.setMinimumHeight(160)
        ocr_box.add_widget(self.ocr_text)
        outer.addWidget(ocr_box)

    def set_preview_image(self, image_path):
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.preview.setText(image_path)
            return

        scaled = pixmap.scaled(
            self.preview.width(),
            self.preview.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.preview.setPixmap(scaled)

    def handle_camera_scan(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            QMessageBox.warning(self, "Camera Error", "Camera could not be opened.")
            return

        QMessageBox.information(
            self,
            "Camera",
            "Press SPACE to capture receipt.\nPress ESC to cancel.",
        )

        captured_frame = None

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            cv2.imshow("Receipt Camera Scan", frame)
            key = cv2.waitKey(1)

            if key == 32:
                captured_frame = frame
                break
            if key == 27:
                break

        cap.release()
        cv2.destroyAllWindows()

        if captured_frame is None:
            return

        temp_path = "captured_receipt.jpg"
        cv2.imwrite(temp_path, captured_frame)
        self.current_image_path = temp_path
        self.set_preview_image(temp_path)
        self.process_receipt(temp_path)

    def handle_upload(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Receipt",
            "",
            "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if not file_path:
            return

        self.current_image_path = file_path
        self.set_preview_image(file_path)
        self.process_receipt(file_path)

    def process_receipt(self, file_path):
        try:
            result = scan_receipt(file_path)
            self.store_input.setText(result["store_name"])
            self.amount_input.setText(f"{result['amount']:.2f}")
            self.note_input.setText("")
            self.ocr_text.setPlainText(result["ocr_text"])

            qdate = QDate.fromString(result["date"], "yyyy-MM-dd")
            if qdate.isValid():
                self.date_edit.setDate(qdate)

            idx = self.category_combo.findText(result["category"])
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)
        except Exception as e:
            QMessageBox.critical(self, "OCR Error", str(e))

    def handle_save(self):
        try:
            store = self.store_input.text().strip()
            amount_text = self.amount_input.text().strip()

            if not store:
                QMessageBox.warning(self, "Warning", "Store name required.")
                return
            if not amount_text:
                QMessageBox.warning(self, "Warning", "Amount required.")
                return

            amount = float(amount_text)
            category = self.category_combo.currentText()
            note = self.note_input.text().strip()
            date = self.date_edit.date().toString("yyyy-MM-dd")

            add_transaction(store, amount, category, note, date, "expense", self.current_image_path)
            QMessageBox.information(self, "Saved", "Receipt transaction saved.")
            self.refresh_callback()

            self.store_input.clear()
            self.amount_input.clear()
            self.note_input.clear()
            self.ocr_text.clear()
            self.category_combo.setCurrentIndex(0)
            self.date_edit.setDate(QDate.currentDate())
            self.current_image_path = None
            self.preview.clear()
            self.preview.setText("📷\n\nPosition your receipt within the frame")
        except ValueError:
            QMessageBox.warning(self, "Warning", "Amount must be a valid number.")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))


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

        subtitle = QLabel("Add income or expense manually, or use voice input for faster entry")
        subtitle.setObjectName("pageSubtitle")
        outer.addWidget(subtitle)

        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        form_box = SectionBox("Add Transaction")

        self.trans_type = QComboBox()
        self.trans_type.addItems(["expense", "income"])

        self.store_input = QLineEdit()
        self.store_input.setPlaceholderText("Example: Migros, Starbucks, Salary")

        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("Example: 120.50")

        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "AUTO",
            "Grocery",
            "Food",
            "Transport",
            "Shopping",
            "Allowance",
            "Salary",
            "Other",
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

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_form)

        save_btn = QPushButton("Save Transaction")
        save_btn.clicked.connect(self.handle_save)

        button_row.addWidget(self.voice_btn)
        button_row.addWidget(clear_btn)
        button_row.addStretch()
        button_row.addWidget(save_btn)
        form_box.add_layout(button_row)

        helper_box = SectionBox("Quick Tips")

        helper_text = QLabel(
            "You can enter transactions manually or use voice.\n\n"
            "Example voice commands:\n"
            "• expense 120 lira for coffee at Starbucks\n"
            "• income 5000 salary\n"
            "• 85 lira grocery from Migros"
        )
        helper_text.setWordWrap(True)
        helper_text.setStyleSheet("color: #516677;")

        self.voice_result = QTextEdit()
        self.voice_result.setReadOnly(True)
        self.voice_result.setPlaceholderText("Recognized voice text will appear here...")
        self.voice_result.setMaximumHeight(180)

        helper_box.add_widget(helper_text)
        helper_box.add_widget(self.voice_result)

        top_row.addWidget(form_box, 2)
        top_row.addWidget(helper_box, 1)

        outer.addLayout(top_row)

    def handle_voice_input(self):
        recognizer = sr.Recognizer()

    try:
        self.voice_btn.setText("Listening...")
        QApplication.processEvents()

        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=7)

    try:
        text = recognizer.recognize_google(audio, language="en-US")
            except sr.UnknownValueError:
            QMessageBox.warning(self, "Voice Input", "Tidak bisa mengenali suara 😢")
            return
        except sr.RequestError:
            QMessageBox.critical(self, "Voice Input", "Koneksi ke Google Speech gagal 🌐")
            return

        self.voice_result.setPlainText(text)

        parsed = parse_voice_transaction(text)

        if parsed["type"]:
            idx = self.trans_type.findText(parsed["type"])
            if idx >= 0:
                self.trans_type.setCurrentIndex(idx)

        if parsed["store"]:
            self.store_input.setText(parsed["store"])

        if parsed["amount"] is not None:
            self.amount_input.setText(f"{parsed['amount']:.2f}")

        if parsed["category"]:
            idx = self.category_combo.findText(parsed["category"])
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)

        if parsed["note"]:
            self.note_input.setPlainText(parsed["note"])

        QMessageBox.information(self, "Success", f"Detected:\n{text}")

    except sr.WaitTimeoutError:
        QMessageBox.warning(self, "Voice Input", "Kamu nggak ngomong 😭")
    except OSError:
        QMessageBox.critical(self, "Voice Input", "Microphone tidak ditemukan 🎤❌")
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Unexpected error:\n{str(e)}")
    finally:
        self.voice_btn.setText("🎤 Voice Input")
    def handle_save(self):
        try:
            trans_type = self.trans_type.currentText()
            store = self.store_input.text().strip() or "Unknown"
            amount_text = self.amount_input.text().strip()
            note = self.note_input.toPlainText().strip()
            category = self.category_combo.currentText()
            date = self.date_edit.date().toString("yyyy-MM-dd")

            if not amount_text:
                QMessageBox.warning(self, "Warning", "Amount is required.")
                return

            amount = float(amount_text)

            if category == "AUTO":
                category = suggest_category(store, note)

            add_transaction(store, amount, category, note, date, trans_type)
            QMessageBox.information(self, "Saved", "Transaction saved successfully.")
            self.clear_form()
            self.refresh_callback()

        except ValueError:
            QMessageBox.warning(self, "Warning", "Amount must be a valid number.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def clear_form(self):
        self.trans_type.setCurrentIndex(0)
        self.store_input.clear()
        self.amount_input.clear()
        self.category_combo.setCurrentIndex(0)
        self.date_edit.setDate(QDate.currentDate())
        self.note_input.clear()
        self.voice_result.clear()


class TransactionsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_id = None
        self.rows_cache = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(16)

        title = QLabel("Transactions")
        title.setObjectName("pageTitle")
        outer.addWidget(title)

        filter_box = SectionBox("Filter & Search")
        filters = QGridLayout()

        self.type_combo = QComboBox()
        self.type_combo.addItems(["All", "expense", "income"])

        self.category_combo = QComboBox()
        self.category_combo.addItems(["All", "Grocery", "Food", "Transport", "Shopping", "Allowance", "Salary", "Other"])

        self.search_input = QLineEdit()

        filters.addWidget(QLabel("Type"), 0, 0)
        filters.addWidget(self.type_combo, 0, 1)
        filters.addWidget(QLabel("Category"), 0, 2)
        filters.addWidget(self.category_combo, 0, 3)
        filters.addWidget(QLabel("Search"), 1, 0)
        filters.addWidget(self.search_input, 1, 1, 1, 3)
        filter_box.add_layout(filters)

        btn_row = QHBoxLayout()
        apply_btn = QPushButton("Apply Filter")
        reset_btn = QPushButton("Reset")
        delete_btn = QPushButton("Delete Selected")

        apply_btn.clicked.connect(self.refresh_data)
        reset_btn.clicked.connect(self.reset_filter)
        delete_btn.clicked.connect(self.delete_selected)

        btn_row.addWidget(apply_btn)
        btn_row.addWidget(reset_btn)
        btn_row.addWidget(delete_btn)
        filter_box.add_layout(btn_row)

        outer.addWidget(filter_box)

        table_box = SectionBox("All Transactions")
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["ID", "Store", "Amount", "Category", "Date", "Type"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.load_selected_into_form)
        table_box.add_widget(self.table)
        outer.addWidget(table_box)

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
        self.edit_note.setMaximumHeight(90)

        edit_form.addRow("Store", self.edit_store)
        edit_form.addRow("Amount", self.edit_amount)
        edit_form.addRow("Category", self.edit_category)
        edit_form.addRow("Date", self.edit_date)
        edit_form.addRow("Type", self.edit_type)
        edit_form.addRow("Note", self.edit_note)
        edit_box.add_layout(edit_form)

        edit_btn_row = QHBoxLayout()
        self.update_btn = QPushButton("Update Selected")
        self.clear_btn = QPushButton("Clear Edit Form")

        self.update_btn.clicked.connect(self.update_selected_transaction)
        self.clear_btn.clicked.connect(self.clear_edit_form)

        edit_btn_row.addWidget(self.update_btn)
        edit_btn_row.addWidget(self.clear_btn)
        edit_box.add_layout(edit_btn_row)

        outer.addWidget(edit_box)

        self.refresh_data()

    def refresh_data(self):
        rows = get_transactions(
            search=self.search_input.text().strip(),
            trans_type=self.type_combo.currentText(),
            category=self.category_combo.currentText(),
        )

        self.rows_cache = rows
        self.table.setRowCount(len(rows))

        for r, row in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(str(row["id"])))
            self.table.setItem(r, 1, QTableWidgetItem(row["store_name"]))
            self.table.setItem(r, 2, QTableWidgetItem(f"₺{row['amount']:.2f}"))
            self.table.setItem(r, 3, QTableWidgetItem(row["category"]))
            self.table.setItem(r, 4, QTableWidgetItem(row["date"]))
            self.table.setItem(r, 5, QTableWidgetItem(row["type"]))

        self.table.resizeColumnsToContents()

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
        row = self.table.currentRow()
        if row < 0 or row >= len(self.rows_cache):
            return

        selected = self.rows_cache[row]
        self.selected_id = selected["id"]

        self.edit_store.setText(selected["store_name"])
        self.edit_amount.setText(f"{selected['amount']:.2f}")

        cat_idx = self.edit_category.findText(selected["category"])
        if cat_idx >= 0:
            self.edit_category.setCurrentIndex(cat_idx)

        type_idx = self.edit_type.findText(selected["type"])
        if type_idx >= 0:
            self.edit_type.setCurrentIndex(type_idx)

        qdate = QDate.fromString(selected["date"], "yyyy-MM-dd")
        if qdate.isValid():
            self.edit_date.setDate(qdate)

        self.edit_note.setPlainText(selected["note"] if selected["note"] else "")

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