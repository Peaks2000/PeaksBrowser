import sys
import os
import platform
from PyQt5.QtWidgets import (QApplication, QVBoxLayout, QHBoxLayout, QWidget,
                             QTabWidget, QLineEdit, QPushButton, QSizePolicy,
                             QMessageBox, QShortcut, QMenu, QAction, QInputDialog,
                             QComboBox, QDialog, QLabel, QDialogButtonBox, QCheckBox)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PyQt5.QtCore import QUrl, Qt

class Browser(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Peaks Browser")
        self.is_fullscreen = False
        self.manual_tab_names = {}
        self.dark_mode = False
        self.default_new_tab_url = "https://www.peaks2000.com"
        self.custom_new_tab_url = ""

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_current_tab)
        self.tabs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(self.show_tab_context_menu)

        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.url_bar.setStyleSheet("border: 1px solid #555; border-radius: 10px; padding: 5px;")

        button_size = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.new_tab_button = self.create_button("+", self.add_new_tab)
        self.refresh_button = self.create_button("↻", self.refresh_page)
        self.fullscreen_button = self.create_button("⛶", self.toggle_fullscreen)
        self.find_button = self.create_button("🔍", self.open_find_dialog)
        self.settings_button = self.create_button("⚙️", self.open_settings_dialog)

        nav_bar = QHBoxLayout()
        nav_bar.addWidget(self.url_bar)
        nav_bar.addWidget(self.new_tab_button)
        nav_bar.addWidget(self.refresh_button)
        nav_bar.addWidget(self.fullscreen_button)
        nav_bar.addWidget(self.find_button)
        nav_bar.addWidget(self.settings_button)

        layout = QVBoxLayout()
        layout.addLayout(nav_bar)
        layout.addWidget(self.tabs)
        self.setLayout(layout)

        self.add_new_tab()

        QShortcut(Qt.CTRL + Qt.Key_R, self).activated.connect(self.refresh_page)
        QShortcut(Qt.CTRL + Qt.Key_T, self).activated.connect(self.add_new_tab)
        QShortcut(Qt.CTRL + Qt.Key_W, self).activated.connect(self.close_current_tab)
        QShortcut(Qt.CTRL + Qt.Key_Tab, self).activated.connect(self.switch_to_next_tab)
        QShortcut(Qt.Key_F11, self).activated.connect(self.toggle_fullscreen)
        QShortcut(Qt.CTRL + Qt.Key_F, self).activated.connect(self.open_find_dialog)

        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 0; } /* No border around tabs */
            QTabBar::tab { 
                border: 1px solid #555; 
                border-radius: 10px; 
                margin: 5px; 
                padding: 10px;
                background-color: #f0f0f0; 
                color: black; 
            }
            QTabBar::tab:selected { 
                background-color: #c0c0c0; 
                color: black; 
            }
            QTabBar::tab:pressed { 
                background-color: #a0a0a0; 
                color: black; 
            }
            QTabBar::tab:hover { 
                background-color: #d0d0d0; 
            }
        """)

    def create_button(self, text, on_click):
        button = QPushButton(text)
        button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        button.setFixedSize(30, 30)  # Smaller button size
        button.clicked.connect(on_click)
        button.setStyleSheet("""
            background-color: transparent; 
            color: inherit;  
            border-radius: 10px; 
            font-size: 16px;  
            border: none;  
        """)
        return button

    def add_new_tab(self, url=None):
        if url is None:
            url = self.default_new_tab_url if not self.custom_new_tab_url else self.custom_new_tab_url

        if not isinstance(url, str):
            url = self.default_new_tab_url

        web_view = CustomWebEngineView(self)
        web_view.setUrl(QUrl(url))
        index = self.tabs.addTab(web_view, "New Tab")
        self.tabs.setCurrentIndex(index)

        web_view.titleChanged.connect(lambda title: self.update_tab_title(index, title))

    def update_tab_title(self, index, title):
        if index not in self.manual_tab_names:
            # Enforce character limit of 20 for tab titles
            limited_title = title if len(title) <= 20 else title[:20] + "..."
            self.tabs.setTabText(index, limited_title)

    def navigate_to_url(self):
        url = self.url_bar.text()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "http://" + url
        current_tab = self.tabs.currentWidget()
        current_tab.setUrl(QUrl(url))

    def refresh_page(self):
        current_tab = self.tabs.currentWidget()
        current_tab.reload()

    def close_current_tab(self, index=None):
        if index is None:
            index = self.tabs.currentIndex()
        if index != -1:
            if index in self.manual_tab_names:
                del self.manual_tab_names[index]
            self.tabs.removeTab(index)

    def show_tab_context_menu(self, pos):
        index = self.tabs.tabBar().tabAt(pos)
        if index != -1:
            menu = QMenu(self)
            rename_action = QAction("Rename Tab", self)
            rename_action.triggered.connect(lambda: self.rename_tab(index))
            menu.addAction(rename_action)
            menu.exec_(self.tabs.mapToGlobal(pos))

    def rename_tab(self, index):
        current_tab_name = self.tabs.tabText(index)
        new_name, ok = QInputDialog.getText(self, "Rename Tab", "New name:", text=current_tab_name)
        if ok and new_name:
            limited_name = new_name if len(new_name) <= 20 else new_name[:20] + "..."
            self.tabs.setTabText(index, limited_name)
            self.manual_tab_names[index] = limited_name

    def switch_to_next_tab(self):
        current_index = self.tabs.currentIndex()
        next_index = (current_index + 1) % self.tabs.count()
        self.tabs.setCurrentIndex(next_index)

    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal()
            self.fullscreen_button.setText("⛶")
        else:
            self.showFullScreen()
            self.fullscreen_button.setText("🞬")
        self.is_fullscreen = not self.is_fullscreen

    def open_find_dialog(self):
        current_tab = self.tabs.currentWidget()
        if isinstance(current_tab, CustomWebEngineView):
            dialog = FindDialog(self, current_tab)
            dialog.exec_()

    def open_settings_dialog(self):
        dialog = SettingsDialog(self)
        if dialog.exec_():
            self.dark_mode = dialog.dark_mode_checkbox.isChecked()
            self.custom_new_tab_url = dialog.custom_url_input.text()

            if self.dark_mode:
                self.apply_dark_mode()
            else:
                self.remove_dark_mode()

    def apply_dark_mode(self):
        dark_palette = self.palette()
        dark_palette.setColor(self.backgroundRole(), Qt.black)
        self.setPalette(dark_palette)
        self.setStyleSheet("background-color: #222; color: white;")

        button_style = """
            background-color: transparent; 
            color: white;  
            border-radius: 10px; 
            font-size: 16px;  
            border: none;  
        """
        for button in [self.new_tab_button, self.refresh_button, self.fullscreen_button, self.find_button, self.settings_button]:
            button.setStyleSheet(button_style)

    def remove_dark_mode(self):
        self.setPalette(QApplication.style().standardPalette())
        self.setStyleSheet("")

        button_style = """
            background-color: transparent; 
            color: inherit;  
            border-radius: 10px; 
            font-size: 16px;  
            border: none;  
        """
        for button in [self.new_tab_button, self.refresh_button, self.fullscreen_button, self.find_button, self.settings_button]:
            button.setStyleSheet(button_style)

class CustomWebEngineView(QWebEngineView):
    def __init__(self, browser, parent=None):
        super().__init__(parent)
        self.browser = browser
        self.setPage(CustomWebEnginePage(self))
        self.setMinimumSize(800, 600)

class CustomWebEnginePage(QWebEnginePage):
    def __init__(self, web_view):
        super().__init__(web_view)

class FindDialog(QDialog):
    def __init__(self, parent, web_view):
        super().__init__(parent)
        self.web_view = web_view
        self.setWindowTitle("Find")
        self.setFixedSize(300, 100)
        self.label = QLabel("Find:")
        self.find_input = QLineEdit()
        self.find_input.textChanged.connect(self.web_view.findText)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.find_input)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

class SettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(300, 150)
        self.dark_mode_checkbox = QCheckBox("Enable Dark Mode")
        self.custom_url_label = QLabel("Custom New Tab URL:")
        self.custom_url_input = QLineEdit(parent.custom_new_tab_url)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self.dark_mode_checkbox)
        layout.addWidget(self.custom_url_label)
        layout.addWidget(self.custom_url_input)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName("Peaks Browser")
    app.setAttribute(Qt.AA_EnableHighDpiScaling)
    browser = Browser()
    browser.show()
    sys.exit(app.exec_())
