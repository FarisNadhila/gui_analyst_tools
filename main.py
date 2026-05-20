import sys
import os
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFileDialog, QLineEdit, QStackedWidget,
    QProgressBar, QFrame, QPlainTextEdit, QTabWidget, QDateEdit,
    QComboBox, QRadioButton, QButtonGroup, QScrollArea, QSpinBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QIcon
from dotenv import load_dotenv, set_key

from services.auto_topic import run_auto_topic
from services.auto_report import generate_whatsapp_report
from services.auto_report_topic import generate_laporan_from_excel
from services.ai_helper2 import get_gemini_categories, test_gemini_connection # Import test_gemini_connection
from services.pull_data import pull_data
from services.remastered_report import generate_remastered_report

load_dotenv()

# --- Configuration Paths ---
DB_DIR = "db"
CATEGORIES_FILE = os.path.join(DB_DIR, "categories.json")
WHITELIST_FILE = os.path.join(DB_DIR, "whitelist.txt")
REPORT_FORMATS_FILE = os.path.join(DB_DIR, "report_formats.json")

# --- Custom Widgets for Remastered Report ---

class SectionWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setLineWidth(1)
        self.setStyleSheet("SectionWidget { border: 1px solid black; margin-bottom: 5px; padding: 5px; }")
        
        self.layout = QVBoxLayout(self)
        
        # Type selection
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Section Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Summary/Counts", "Sentiment", "Topic", "Media Type"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        header_layout.addWidget(self.type_combo)
        
        self.remove_btn = QPushButton("Remove Section")
        self.remove_btn.setFixedSize(120, 24)
        self.remove_btn.setStyleSheet("border: 1px solid black; min-height: 24px; font-size: 10px;")
        self.remove_btn.clicked.connect(self.deleteLater)
        header_layout.addWidget(self.remove_btn)
        
        self.layout.addLayout(header_layout)
        
        # Container for dynamic config
        self.config_container = QWidget()
        self.config_layout = QVBoxLayout(self.config_container)
        self.config_layout.setContentsMargins(0, 5, 0, 0)
        self.layout.addWidget(self.config_container)
        
        self.on_type_changed(self.type_combo.currentText())

    def on_type_changed(self, text):
        # Clear config layout safely
        while self.config_layout.count():
            item = self.config_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            
        if text == "Topic":
            # Simplified Topic: No manual groups needed as per user request
            self.config_layout.addWidget(QLabel("Automatic Topic Grouping:"))
            self.config_layout.addWidget(QLabel("- Reads 'Topik' column"))
            self.config_layout.addWidget(QLabel("- Sorts by article count (desc)"))
            
        elif text == "Sentiment" or text == "Summary/Counts":
            self.order_input = QLineEdit("Positive, Neutral, Negative")
            self.config_layout.addWidget(QLabel("Order (comma separated):"))
            self.config_layout.addWidget(self.order_input)
            
        elif text == "Media Type":
            self.order_input = QLineEdit("media tv, media cetak, media online")
            self.config_layout.addWidget(QLabel("Order (comma separated):"))
            self.config_layout.addWidget(self.order_input)

    def get_config(self):
        config = {"type": self.type_combo.currentText()}
        if config["type"] == "Topic":
            # Simplified: No extra config fields needed for automatic grouping
            pass
        elif config["type"] in ["Sentiment", "Summary/Counts", "Media Type"]:
            config["order"] = [o.strip() for o in self.order_input.text().split(",") if o.strip()]
        return config

    def set_config(self, config):
        self.type_combo.setCurrentText(config.get("type", "Summary/Counts"))
        if config.get("type") == "Topic":
            # Simplified: Nothing to set for automatic grouping
            pass
        elif "order" in config:
            self.order_input.setText(", ".join(config.get("order", [])))

# --- Retro Stylesheet ---
RETRO_STYLE = """
QMainWindow { background-color: #f0f0f0; }
QWidget {
    background-color: #FFFFFF;
    color: #000000;
    font-family: 'Geneva', 'Verdana', sans-serif;
    font-size: 14px;
}
QFrame#Desktop { background-color: #999999; }
QFrame#WindowFrame { border: 2px solid #000000; background-color: #FFFFFF; }
QFrame#TitleBar { background-color: #FFFFFF; border-bottom: 2px solid #000000; min-height: 20px; }
QLabel#TitleLabel { font-weight: bold; font-size: 12px; padding-left: 8px; }
QPushButton {
    border: 2px solid #000000;
    background-color: #FFFFFF;
    padding: 2px 8px;
    min-height: 40px;
    border-radius: 0px;
    font-weight: bold;
}
QPushButton:pressed { background-color: #000000; color: #FFFFFF; }
QLineEdit, QPlainTextEdit {
    border: 1px solid #000000;
    padding: 2px;
    background-color: #FFFFFF;
    selection-background-color: #000000;
    font-family: 'Courier New', monospace;
}
QProgressBar { border: 1px solid #000000; text-align: center; background-color: #FFFFFF; }
QProgressBar::chunk { background-color: #000000; }
QLabel#Header { font-weight: bold; font-size: 13px; margin-bottom: 3px; }
QTabWidget::pane { border: 1px solid #000000; top: -1px; }
QTabBar::tab {
    border: 1px solid #000000;
    border-bottom: none;
    padding: 3px 6px;
    background: #f0f0f0;
}
QTabBar::tab:selected { background: #FFFFFF; font-weight: bold; }
"""

class RetroButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Digivla Analyst Tools")
        
        # Set Window Icon
        icon_path = os.path.join("assets", "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # --- Allow resizing and set minimum size ---
        self.setMinimumSize(480, 640) 
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Fake Menu Bar
        self.menu_bar = QFrame()
        self.menu_bar.setFixedHeight(20)
        self.menu_bar.setStyleSheet("background-color: #FFFFFF; border-bottom: 1px solid #000000;")
        menu_layout = QHBoxLayout(self.menu_bar)
        menu_layout.setContentsMargins(10, 0, 10, 0)
        apple_icon = QLabel("")
        apple_icon.setStyleSheet("font-size: 16px; font-weight: bold;")
        menu_layout.addWidget(apple_icon)
        menu_layout.addWidget(QLabel("File"))
        menu_layout.addWidget(QLabel("Edit"))

        # View Menu with Toggle Fullscreen
        view_menu = QLabel("View")
        view_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        # Using a simple mouse press event for the fake menu
        view_menu.mousePressEvent = lambda e: self.toggle_fullscreen()
        menu_layout.addWidget(view_menu)

        menu_layout.addWidget(QLabel("Special"))
        menu_layout.addStretch()
        self.main_layout.addWidget(self.menu_bar)
        
        # Desktop area
        self.desktop = QFrame()
        self.desktop.setObjectName("Desktop")
        self.desktop_layout = QVBoxLayout(self.desktop)
        self.desktop_layout.setContentsMargins(15, 15, 15, 15)
        
        # App window
        self.app_window = QFrame()
        self.app_window.setObjectName("WindowFrame")
        self.window_layout = QVBoxLayout(self.app_window)
        self.window_layout.setContentsMargins(0, 0, 0, 0)
        self.window_layout.setSpacing(0)
        
        # Title Bar
        self.app_title_bar = QFrame()
        self.app_title_bar.setObjectName("TitleBar")
        self.app_title_bar.setFixedHeight(20)
        title_layout = QHBoxLayout(self.app_title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)
        close_box = QFrame()
        close_box.setFixedSize(12, 12)
        close_box.setStyleSheet("border: 1px solid #000000;")
        title_layout.addWidget(close_box)
        self.title_label = QLabel("Digivla Analyst Tools")
        self.title_label.setObjectName("TitleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(self.title_label)
        title_layout.addSpacing(24)
        self.window_layout.addWidget(self.app_title_bar)
        
        self.pages = QStackedWidget()
        self.window_layout.addWidget(self.pages)
        
        self.init_menu_page()
        self.init_topic_page()
        self.init_report_generator_page()
        self.init_settings_page()
        self.init_pull_data_page()
        
        self.desktop_layout.addWidget(self.app_window)
        self.main_layout.addWidget(self.desktop)
        
        self.setStyleSheet(RETRO_STYLE)

    def init_menu_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(15, 10, 15, 10)
        logo = QLabel("Main Menu")
        logo.setStyleSheet("font-size: 48px; font-weight: bold; letter-spacing: 4px;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)
        line = QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setStyleSheet("color: black; border: 1px solid black;")
        layout.addWidget(line)
        layout.addSpacing(15)
        
        menu_items = [
            ("Pull Data", 4),
            ("Auto Topic Analysis", 1),
            ("Report Generator", 2),
            ("Configure Tools...", 3)
        ]
        
        for name, idx in menu_items:
            btn = RetroButton(name)
            btn.setFixedSize(400, 35)
            btn.clicked.connect(lambda checked, i=idx: self.switch_page(i))
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
            layout.addSpacing(8)
            
        layout.addStretch()
        layout.addWidget(QLabel("Beta v0.6.0"), alignment=Qt.AlignmentFlag.AlignCenter)
        self.pages.addWidget(page)

    def switch_page(self, index):
        if index == 3: self.load_settings_data()
        if index == 2: self.load_report_formats()
        self.pages.setCurrentIndex(index)

    def init_topic_page(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(15, 10, 15, 10)
        layout.addWidget(QLabel("Auto Topic Analysis", objectName="Header"))
        
        layout.addWidget(QLabel("Input Excel File:"))
        h1 = QHBoxLayout(); self.topic_input = QLineEdit(); self.topic_input.setReadOnly(True)
        btn1 = RetroButton("Select..."); btn1.clicked.connect(self.browse_topic_input)
        h1.addWidget(self.topic_input); h1.addWidget(btn1); layout.addLayout(h1)
        
        layout.addWidget(QLabel("Output Directory:"))
        h2 = QHBoxLayout(); self.topic_output = QLineEdit(); self.topic_output.setReadOnly(True)
        btn2 = RetroButton("Select..."); btn2.clicked.connect(self.browse_topic_output)
        h2.addWidget(self.topic_output); h2.addWidget(btn2); layout.addLayout(h2)
        
        self.topic_status = QLabel("Status: Idle"); 
        self.topic_status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse) # Make selectable
        layout.addWidget(self.topic_status)
        self.topic_progress = QProgressBar(); self.topic_progress.setFixedHeight(12); self.topic_progress.setVisible(False)
        layout.addWidget(self.topic_progress)
        
        layout.addStretch(); b_layout = QHBoxLayout()
        btn_back = RetroButton("Back"); btn_back.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        btn_run = RetroButton("OK"); btn_run.clicked.connect(self.run_topic_analysis)
        b_layout.addWidget(btn_back); b_layout.addStretch(); b_layout.addWidget(btn_run); layout.addLayout(b_layout)
        self.pages.addWidget(page)

    def init_report_generator_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(15, 10, 15, 10)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        self.report_layout = QVBoxLayout(scroll_content)
        self.report_layout.setContentsMargins(0, 0, 10, 0)
        
        self.report_layout.addWidget(QLabel("Auto Report", objectName="Header"))
        
        # --- Format Section ---
        format_group = QFrame()
        format_group.setStyleSheet("border: 1px solid black; padding: 5px;")
        format_layout = QVBoxLayout(format_group)
        
        format_layout.addWidget(QLabel("Format Setup", objectName="Header"))
        
        # Client selection
        h_client = QHBoxLayout()
        h_client.addWidget(QLabel("Select Client:"))
        self.report_client_combo = QComboBox()
        self.report_client_combo.setEditable(True)
        self.report_client_combo.currentTextChanged.connect(self.on_report_client_changed)
        h_client.addWidget(self.report_client_combo, 1)
        format_layout.addLayout(h_client)
        
        # Header Format
        format_layout.addWidget(QLabel("Header Format:"))
        self.report_header_edit = QPlainTextEdit()
        self.report_header_edit.setPlaceholderText("Laporan Media Monitoring\n{client_name}\n{date}\n...")
        self.report_header_edit.setFixedHeight(100)
        format_layout.addWidget(self.report_header_edit)
        
        # Data Sections
        format_layout.addWidget(QLabel("Data Sections:"))
        self.sections_container = QWidget()
        self.sections_layout = QVBoxLayout(self.sections_container)
        self.sections_layout.setContentsMargins(0, 0, 0, 0)
        format_layout.addWidget(self.sections_container)
        
        h_sec_btns = QHBoxLayout()
        btn_add_sec = QPushButton("+ Add Section")
        btn_add_sec.setStyleSheet("border: 1px solid black; min-height: 30px;")
        btn_add_sec.clicked.connect(self.add_report_section)
        btn_save_fmt = QPushButton("Save Format")
        btn_save_fmt.setStyleSheet("border: 1px solid black; min-height: 30px; background-color: #f0f0f0;")
        btn_save_fmt.clicked.connect(self.save_report_format)
        h_sec_btns.addWidget(btn_add_sec)
        h_sec_btns.addWidget(btn_save_fmt)
        format_layout.addLayout(h_sec_btns)
        
        self.report_layout.addWidget(format_group)
        self.report_layout.addSpacing(15)
        
        # --- Process Section ---
        process_group = QFrame()
        process_group.setStyleSheet("border: 1px solid black; padding: 5px;")
        process_layout = QVBoxLayout(process_group)
        
        process_layout.addWidget(QLabel("Process Report", objectName="Header"))
        
        process_layout.addWidget(QLabel("Input Excel File:"))
        h1 = QHBoxLayout()
        self.report_input = QLineEdit(); self.report_input.setReadOnly(True)
        btn1 = RetroButton("Select..."); btn1.clicked.connect(self.browse_report_input)
        h1.addWidget(self.report_input); h1.addWidget(btn1)
        process_layout.addLayout(h1)
        
        process_layout.addWidget(QLabel("Export Folder:"))
        h2 = QHBoxLayout()
        self.report_output = QLineEdit()
        self.report_output.setText(os.path.join(os.getcwd(), "output"))
        btn2 = RetroButton("Select..."); btn2.clicked.connect(self.browse_report_output)
        h2.addWidget(self.report_output); h2.addWidget(btn2)
        process_layout.addLayout(h2)
        
        self.report_status = QLabel("Status: Idle")
        self.report_status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        process_layout.addWidget(self.report_status)
        
        self.report_layout.addWidget(process_group)
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        b_layout = QHBoxLayout()
        btn_back = RetroButton("Back"); btn_back.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        btn_run = RetroButton("Process"); btn_run.clicked.connect(self.run_report_generator)
        b_layout.addWidget(btn_back); b_layout.addStretch(); b_layout.addWidget(btn_run); layout.addLayout(b_layout)
        
        self.pages.addWidget(page)

    def add_report_section(self, config=None):
        widget = SectionWidget()
        if config:
            widget.set_config(config)
        self.sections_layout.addWidget(widget)

    def load_report_formats(self):
        self.report_client_combo.blockSignals(True)
        self.report_client_combo.clear()
        if os.path.exists(REPORT_FORMATS_FILE):
            try:
                with open(REPORT_FORMATS_FILE, 'r') as f:
                    self.report_formats = json.load(f)
                    self.report_client_combo.addItems(sorted(self.report_formats.keys()))
            except:
                self.report_formats = {}
        else:
            self.report_formats = {}
        self.report_client_combo.blockSignals(False)
        if self.report_client_combo.count() > 0:
            self.on_report_client_changed(self.report_client_combo.currentText())

    def on_report_client_changed(self, client_name):
        # Clear sections
        for i in reversed(range(self.sections_layout.count())):
            self.sections_layout.itemAt(i).widget().setParent(None)
            
        config = self.report_formats.get(client_name)
        if config:
            self.report_header_edit.setPlainText(config.get("header", ""))
            for sec_cfg in config.get("sections", []):
                self.add_report_section(sec_cfg)
        else:
            self.report_header_edit.setPlainText("")

    def save_report_format(self):
        client_name = self.report_client_combo.currentText().strip()
        if not client_name:
            self.report_status.setText("Status: Client name required"); return
            
        sections = []
        for i in range(self.sections_layout.count()):
            w = self.sections_layout.itemAt(i).widget()
            if isinstance(w, SectionWidget):
                sections.append(w.get_config())
                
        self.report_formats[client_name] = {
            "header": self.report_header_edit.toPlainText(),
            "sections": sections
        }
        
        try:
            with open(REPORT_FORMATS_FILE, 'w') as f:
                json.dump(self.report_formats, f, indent=4)
            self.report_status.setText(f"Status: Format for '{client_name}' saved!")
            # Refresh combo if new
            if self.report_client_combo.findText(client_name) == -1:
                self.report_client_combo.addItem(client_name)
        except Exception as e:
            self.report_status.setText(f"Status: Save Error - {str(e)}")

    def browse_report_input(self):
        file, _ = QFileDialog.getOpenFileName(self, "Open Excel", "", "Excel Files (*.xlsx *.xls)")
        if file: self.report_input.setText(file)

    def browse_report_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder: self.report_output.setText(folder)

    def run_report_generator(self):
        client_name = self.report_client_combo.currentText().strip()
        excel_path = self.report_input.text()
        output_dir = self.report_output.text()
        
        if not client_name or not excel_path or not output_dir:
            self.report_status.setText("Status: Missing info"); return

        config = self.report_formats.get(client_name)
        if not config:
            # Try to build config from current UI state without saving
            sections = []
            for i in range(self.sections_layout.count()):
                w = self.sections_layout.itemAt(i).widget()
                if isinstance(w, SectionWidget):
                    sections.append(w.get_config())
            config = {
                "client_name": client_name,
                "header": self.report_header_edit.toPlainText(),
                "sections": sections
            }
        else:
            config["client_name"] = client_name

        self.report_status.setText("Status: Processing..."); QApplication.processEvents()
        success, msg = generate_remastered_report(excel_path, config, output_dir)
        self.report_status.setText(f"Status: {'Done' if success else 'Error - ' + str(msg)}")

    def init_settings_page(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(QLabel("Configuration Editor", objectName="Header"))
        
        self.tabs = QTabWidget() 
        
        # Tab 1: Categories + AI
        self.tab_cat = QWidget(); cat_layout = QVBoxLayout(self.tab_cat); cat_layout.setContentsMargins(5, 5, 5, 5)
        
        ai_layout = QHBoxLayout()
        self.ai_prompt = QLineEdit(); self.ai_prompt.setPlaceholderText("AI Prompt: e.g. update for latest Prabowo issues")
        self.btn_ai = RetroButton("AI Generate"); self.btn_ai.clicked.connect(self.run_ai_gen)
        ai_layout.addWidget(self.ai_prompt); ai_layout.addWidget(self.btn_ai)
        cat_layout.addLayout(ai_layout)
        
        self.cat_editor = QPlainTextEdit(); cat_layout.addWidget(self.cat_editor) 
        self.tabs.addTab(self.tab_cat, "Categories")
        
        # Tab 2: Whitelist
        self.tab_white = QWidget(); white_layout = QVBoxLayout(self.tab_white); white_layout.setContentsMargins(5, 5, 5, 5)
        self.white_editor = QPlainTextEdit(); white_layout.addWidget(self.white_editor) 
        self.tabs.addTab(self.tab_white, "Whitelist")
        
        # Tab 3: API Keys
        self.tab_api = QWidget(); api_layout = QVBoxLayout(self.tab_api); api_layout.setContentsMargins(5, 5, 5, 5)
        api_layout.addWidget(QLabel("Gemini API Key:"))
        key_layout = QHBoxLayout()
        self.api_key_input = QLineEdit(); self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setText(os.getenv("GOOGLE_API_KEY", "")) # Changed to GOOGLE_API_KEY
        self.btn_test_api = RetroButton("Test"); self.btn_test_api.clicked.connect(self.test_api_connection) # Test Button
        key_layout.addWidget(self.api_key_input); key_layout.addWidget(self.btn_test_api)
        api_layout.addLayout(key_layout)
        api_layout.addStretch()
        self.tabs.addTab(self.tab_api, "API Keys")
        
        layout.addWidget(self.tabs)
        self.settings_status = QLabel("Status: Idle"); 
        self.settings_status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse) # Make selectable
        layout.addWidget(self.settings_status)
        
        b_layout = QHBoxLayout()
        btn_back = RetroButton("Back"); btn_back.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        btn_save = RetroButton("Save All"); btn_save.clicked.connect(self.save_settings)
        b_layout.addWidget(btn_back); b_layout.addStretch(); b_layout.addWidget(btn_save); layout.addLayout(b_layout)
        self.pages.addWidget(page)

    def init_pull_data_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(15, 10, 15, 10)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 10, 0)
        
        scroll_layout.addWidget(QLabel("Pull Data", objectName="Header"))
        
        # Token
        scroll_layout.addWidget(QLabel("API Token:"))
        self.pull_token = QLineEdit()
        self.pull_token.setPlaceholderText("Paste your token here...")
        scroll_layout.addWidget(self.pull_token)
        
        # Dates
        h_dates = QHBoxLayout()
        v_sdate = QVBoxLayout()
        v_sdate.addWidget(QLabel("Start Date (sdate):"))
        self.pull_sdate = QDateEdit(QDate.currentDate())
        self.pull_sdate.setCalendarPopup(True)
        self.pull_sdate.setDisplayFormat("yyyy-MM-dd")
        v_sdate.addWidget(self.pull_sdate)
        
        v_edate = QVBoxLayout()
        v_edate.addWidget(QLabel("End Date (edate):"))
        self.pull_edate = QDateEdit(QDate.currentDate())
        self.pull_edate.setCalendarPopup(True)
        self.pull_edate.setDisplayFormat("yyyy-MM-dd")
        v_edate.addWidget(self.pull_edate)
        
        h_dates.addLayout(v_sdate)
        h_dates.addLayout(v_edate)
        scroll_layout.addLayout(h_dates)
        
        # mcat (Category)
        scroll_layout.addWidget(QLabel("Media Category (mcat):"))
        self.pull_mcat = QComboBox()
        self.pull_mcat.addItems(["all", "media_cetak", "media_online", "media_tv", "media_radio"])
        scroll_layout.addWidget(self.pull_mcat)
        
        # field (Radio Buttons)
        scroll_layout.addWidget(QLabel("Search Field:"))
        self.field_group = QButtonGroup(self)
        h_field = QHBoxLayout()
        self.radio_title = QRadioButton("Title")
        self.radio_title.setChecked(True)
        self.radio_content = QRadioButton("Content")
        self.field_group.addButton(self.radio_title)
        self.field_group.addButton(self.radio_content)
        h_field.addWidget(self.radio_title)
        h_field.addWidget(self.radio_content)
        scroll_layout.addLayout(h_field)
        
        # Terms
        scroll_layout.addWidget(QLabel("Search Terms:"))
        self.pull_terms = QLineEdit()
        self.pull_terms.setPlaceholderText("e.g. mbg")
        scroll_layout.addWidget(self.pull_terms)
        
        # Max Size
        scroll_layout.addWidget(QLabel("Max Data Size (maxsize):"))
        self.pull_maxsize = QSpinBox()
        self.pull_maxsize.setRange(1, 10000)
        self.pull_maxsize.setValue(10)
        scroll_layout.addWidget(self.pull_maxsize)
        
        # Output folder
        scroll_layout.addWidget(QLabel("Output Folder:"))
        h_out = QHBoxLayout()
        self.pull_output = QLineEdit()
        self.pull_output.setReadOnly(True)
        self.pull_output.setText(os.path.join(os.getcwd(), "output"))
        btn_out = RetroButton("Select...")
        btn_out.clicked.connect(self.browse_pull_output)
        h_out.addWidget(self.pull_output)
        h_out.addWidget(btn_out)
        scroll_layout.addLayout(h_out)
        
        self.pull_status = QLabel("Status: Idle")
        self.pull_status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        scroll_layout.addWidget(self.pull_status)
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        b_layout = QHBoxLayout()
        btn_back = RetroButton("Back")
        btn_back.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        btn_run = RetroButton("OK")
        btn_run.clicked.connect(self.run_pull_data)
        b_layout.addWidget(btn_back)
        b_layout.addStretch()
        b_layout.addWidget(btn_run)
        layout.addLayout(b_layout)
        
        self.pages.addWidget(page)

    def browse_pull_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder: self.pull_output.setText(folder)

    def run_pull_data(self):
        token = self.pull_token.text().strip()
        if not token:
            self.pull_status.setText("Status: Token is required"); return
        
        sdate = self.pull_sdate.date().toString("yyyy-MM-dd")
        edate = self.pull_edate.date().toString("yyyy-MM-dd")
        mcat = self.pull_mcat.currentText()
        field = "title" if self.radio_title.isChecked() else "content"
        terms = self.pull_terms.text().strip()
        maxsize = self.pull_maxsize.value()
        output_folder = self.pull_output.text()
        
        if not terms:
            self.pull_status.setText("Status: Terms are required"); return
        if not output_folder:
            self.pull_status.setText("Status: Output folder is required"); return

        self.pull_status.setText("Status: Pulling data..."); QApplication.processEvents()
        
        success, result = pull_data(token, sdate, edate, mcat, field, terms, maxsize, output_folder)
        
        if success:
            self.pull_status.setText(f"Status: Success! Saved to {result}")
        else:
            self.pull_status.setText(f"Status: Error - {result}")

    def browse_report_topic_input(self):
        file, _ = QFileDialog.getOpenFileName(self, "Open Excel", "", "Excel Files (*.xlsx *.xls)")
        if file: self.report_topic_input.setText(file)

    def browse_report_topic_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder: self.report_topic_output.setText(folder)

    def run_report_topic(self):
        i, d, o = self.report_topic_input.text(), self.report_topic_date.text(), self.report_topic_output.text()
        if not i or not o: self.report_topic_status.setText("Status: Missing paths"); return
        
        if not d: d = "XX - XX"
        
        # Determine output filename
        base_name = os.path.splitext(os.path.basename(i))[0]
        tanggal_now = datetime.now().strftime("%Y%m%d")
        default_nama = f"laporan_harian_{base_name}_{tanggal_now}.txt"
        output_path = os.path.join(o, default_nama)

        self.report_topic_status.setText("Status: Processing..."); QApplication.processEvents()
        try:
            hasil = generate_laporan_from_excel(i, output_path, d)
            if hasil:
                self.report_topic_status.setText(f"Status: Success! Saved to {default_nama}")
            else:
                self.report_topic_status.setText("Status: Error during generation")
        except Exception as e:
            self.report_topic_status.setText(f"Status: Error - {str(e)}")

    def load_settings_data(self):
        try:
            with open(CATEGORIES_FILE, "r") as f: self.cat_editor.setPlainText(f.read())
        except: self.cat_editor.setPlainText("{}")
        try:
            with open(WHITELIST_FILE, "r") as f: self.white_editor.setPlainText(f.read())
        except: self.white_editor.setPlainText("")

    def save_settings(self):
        cat_text = self.cat_editor.toPlainText()
        try:
            json.loads(cat_text); 
            if not os.path.exists(DB_DIR): os.makedirs(DB_DIR)
            with open(CATEGORIES_FILE, "w") as f: f.write(cat_text)
        except Exception as e:
            self.settings_status.setText(f"Status: JSON Error - {str(e)}"); return
        
        if not os.path.exists(DB_DIR): os.makedirs(DB_DIR)
        with open(WHITELIST_FILE, "w") as f: f.write(self.white_editor.toPlainText())
        
        api_key = self.api_key_input.text()
        if api_key:
            with open(".env", "a") as f: pass # Ensure exists
            set_key(".env", "GOOGLE_API_KEY", api_key) # Changed to GOOGLE_API_KEY
            os.environ["GOOGLE_API_KEY"] = api_key # Changed to GOOGLE_API_KEY
            
        self.settings_status.setText("Status: Saved!"); self.pages.setCurrentIndex(0)

    def test_api_connection(self):
        api_key = self.api_key_input.text()
        if not api_key:
            self.settings_status.setText("Status: API Key is empty."); return
        
        self.settings_status.setText("Status: Testing connection...")
        self.btn_test_api.setEnabled(False)
        QApplication.processEvents()
        
        success, message = test_gemini_connection(api_key)
        
        self.btn_test_api.setEnabled(True)
        self.settings_status.setText(f"Status: {message}")

    def run_ai_gen(self):
        prompt = self.ai_prompt.text()
        api_key = self.api_key_input.text()
        if not prompt or not api_key:
            self.settings_status.setText("Status: Missing Prompt or API Key"); return
        
        self.settings_status.setText("Status: AI is thinking (using Search)...")
        self.btn_ai.setEnabled(False)
        QApplication.processEvents()
        
        current_categories = self.cat_editor.toPlainText()
        updated_json, error = get_gemini_categories(prompt, current_categories, api_key)
        
        self.btn_ai.setEnabled(True)
        if error:
            self.settings_status.setText(f"Status: AI Error - {error}")
        else:
            self.cat_editor.setPlainText(json.dumps(updated_json, indent=4))
            self.settings_status.setText("Status: AI Update Complete!")

    def browse_topic_input(self):
        file, _ = QFileDialog.getOpenFileName(self, "Open Excel", "", "Excel Files (*.xlsx)")
        if file: self.topic_input.setText(file)

    def browse_topic_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder: self.topic_output.setText(folder)

    def browse_bulog_input(self):
        file, _ = QFileDialog.getOpenFileName(self, "Open Excel", "", "Excel Files (*.xlsx)")
        if file: self.bulog_input.setText(file)

    def browse_bulog_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder: self.bulog_output.setText(folder)

    def run_topic_analysis(self):
        i, o = self.topic_input.text(), self.topic_output.text()
        if not i or not o: self.topic_status.setText("Status: Missing paths"); return
        self.topic_status.setText("Status: Processing..."); self.topic_progress.setVisible(True)
        self.topic_progress.setRange(0, 0); QApplication.processEvents()
        try:
            run_auto_topic(i, o, categories=None, whitelist_path=WHITELIST_FILE, categories_path=CATEGORIES_FILE)
            self.topic_status.setText("Status: Success!")
        except Exception as e: self.topic_status.setText(f"Status: Error - {str(e)}")
        finally: self.topic_progress.setVisible(False)

    def run_bulog_analysis(self):
        i, c, o = self.bulog_input.text(), self.bulog_client.text(), self.bulog_output.text()
        if not i or not c: self.bulog_status.setText("Status: Missing info"); return
        self.bulog_status.setText("Status: Processing..."); QApplication.processEvents()
        s, r = generate_whatsapp_report(i, c, o)
        self.bulog_status.setText(f"Status: {'Done' if s else 'Error'}")

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F11:
            self.toggle_fullscreen()
        super().keyPressEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv); window = MainWindow(); window.show(); sys.exit(app.exec())
