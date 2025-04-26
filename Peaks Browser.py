import sys
import os

from PyQt5.QtWidgets import (
    QApplication,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QTabWidget,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QMenu,
    QAction,
    QInputDialog,
    QDialog,
    QLabel,
    QDialogButtonBox,
    QCheckBox,
    QFileDialog,
    QProgressBar,
    QScrollArea
)

from PyQt5.QtWebEngineWidgets import (
    QWebEngineView,
    QWebEnginePage,
    QWebEngineProfile
)

from PyQt5.QtCore import QUrl, Qt, QCoreApplication


class DownloadItemRow(QWidget):
    def __init__(self, download):
        super().__init__()
        self.download = download
        self.label = QLabel(os.path.basename(download.path()))
        self.progress = QProgressBar()
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.download.cancel)

        layout = QHBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        layout.addWidget(self.cancel_button)
        self.setLayout(layout)

        download.downloadProgress.connect(self.on_progress)
        download.finished.connect(self.on_finished)

    def on_progress(self, received, total):
        if total > 0:
            self.progress.setValue(int(received * 100 / total))

    def on_finished(self):
        self.cancel_button.setDisabled(True)


class DownloadManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Downloads")
        self.resize(600, 300)

        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.container_layout = QVBoxLayout(container)
        scroll.setWidget(container)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)

    def add_download(self, download):
        row = DownloadItemRow(download)
        self.container_layout.addWidget(row)


class Browser(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Peaks Browser")
        self.is_fullscreen = False
        self.manual_tab_names = {}
        self.dark_mode = False
        self.default_new_tab_url = "https://www.peaks2000.com"
        self.custom_new_tab_url = ""
        self.download_dialog = DownloadManagerDialog(self)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_current_tab)
        self.tabs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(self.show_tab_context_menu)

        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.url_bar.setStyleSheet(
            "border: 1px solid #555; border-radius: 10px; padding: 5px;"
        )

        self.new_tab_button = self.create_button("+", self.add_new_tab)
        self.refresh_button = self.create_button("↻", self.refresh_page)
        self.fullscreen_button = self.create_button("⛶", self.toggle_fullscreen)
        self.find_button = self.create_button("🔍", self.open_find_dialog)
        self.download_button = self.create_button("⬇️", self.open_downloads_dialog)
        self.settings_button = self.create_button("⚙️", self.open_settings_dialog)

        nav_bar = QHBoxLayout()
        nav_bar.addWidget(self.url_bar)
        nav_bar.addWidget(self.new_tab_button)
        nav_bar.addWidget(self.refresh_button)
        nav_bar.addWidget(self.fullscreen_button)
        nav_bar.addWidget(self.find_button)
        nav_bar.addWidget(self.download_button)
        nav_bar.addWidget(self.settings_button)

        layout = QVBoxLayout()
        layout.addLayout(nav_bar)
        layout.addWidget(self.tabs)
        self.setLayout(layout)

        self.add_new_tab()
        profile = QWebEngineProfile.defaultProfile()
        profile.downloadRequested.connect(self.handle_download)

    def create_button(self, text, on_click):
        btn = QPushButton(text)
        btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        btn.setFixedSize(30, 30)
        btn.clicked.connect(on_click)
        btn.setStyleSheet(
            "background-color: transparent; color: inherit; border-radius: 10px; font-size: 16px; border: none;"
        )
        return btn

    def add_new_tab(self, url=None):
        if url is None:
            url = self.default_new_tab_url if not self.custom_new_tab_url else self.custom_new_tab_url
        view = CustomWebEngineView(self)
        view.setUrl(QUrl(url))
        idx = self.tabs.addTab(view, "New Tab")
        self.tabs.setCurrentIndex(idx)
        view.titleChanged.connect(lambda title, i=idx: self.update_tab_title(i, title))

    def update_tab_title(self, idx, title):
        if idx not in self.manual_tab_names:
            short = title if len(title) <= 20 else title[:20] + "..."
            self.tabs.setTabText(idx, short)

    def navigate_to_url(self):
        url = self.url_bar.text()
        if not url.startswith(("http://", "https://")):
            url = "http://" + url
        self.tabs.currentWidget().setUrl(QUrl(url))

    def refresh_page(self):
        self.tabs.currentWidget().reload()

    def close_current_tab(self, index=None):
        if index is None:
            index = self.tabs.currentIndex()
        if index != -1:
            self.manual_tab_names.pop(index, None)
            self.tabs.removeTab(index)

    def show_tab_context_menu(self, pos):
        idx = self.tabs.tabBar().tabAt(pos)
        if idx != -1:
            menu = QMenu(self)
            act = QAction("Rename Tab", self)
            act.triggered.connect(lambda: self.rename_tab(idx))
            menu.addAction(act)
            menu.exec_(self.tabs.mapToGlobal(pos))

    def rename_tab(self, idx):
        curr = self.tabs.tabText(idx)
        new, ok = QInputDialog.getText(self, "Rename Tab", "New name:", text=curr)
        if ok and new:
            short = new if len(new) <= 20 else new[:20] + "..."
            self.tabs.setTabText(idx, short)
            self.manual_tab_names[idx] = short

    def switch_to_next_tab(self):
        nxt = (self.tabs.currentIndex() + 1) % self.tabs.count()
        self.tabs.setCurrentIndex(nxt)

    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal(); self.fullscreen_button.setText("⛶")
        else:
            self.showFullScreen(); self.fullscreen_button.setText("🞬")
        self.is_fullscreen = not self.is_fullscreen

    def open_find_dialog(self):
        cur = self.tabs.currentWidget()
        if isinstance(cur, CustomWebEngineView):
            FindDialog(self, cur).exec_()

    def open_settings_dialog(self):
        SettingsDialog(self).exec_()

    def open_downloads_dialog(self):
        self.download_dialog.show()

    def handle_download(self, download):
        suggested = os.path.basename(download.url().path())
        path, _ = QFileDialog.getSaveFileName(self, "Save File", suggested)
        if path:
            download.setPath(path)
            download.accept()
            self.download_dialog.add_download(download)
            self.download_dialog.show()


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
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    app.setApplicationName("Peaks Browser")
    browser = Browser()
    browser.show()
    sys.exit(app.exec_())
