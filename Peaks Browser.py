import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLineEdit,
    QPushButton, QSizePolicy, QMenu, QAction, QInputDialog, QDialog,
    QLabel, QDialogButtonBox, QCheckBox, QFileDialog, QProgressBar,
    QScrollArea
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile
from PyQt5.QtCore import QUrl, Qt, QCoreApplication, QSettings

QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)

class DownloadItemRow(QWidget):
    def __init__(self, download):
        super().__init__()
        self.download = download
        self.label = QLabel(os.path.basename(download.path()))
        self.progress = QProgressBar()
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_download)
        layout = QHBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        layout.addWidget(self.cancel_button)
        self.setLayout(layout)
        download.downloadProgress.connect(self.update_progress)
        download.finished.connect(self.finish_download)

    def update_progress(self, received, total):
        if total > 0:
            self.progress.setValue(int(received * 100 / total))

    def finish_download(self):
        self.cancel_button.setDisabled(True)

    def cancel_download(self):
        self.download.cancel()
        path = self.download.path()
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
        self.setParent(None)
        self.deleteLater()

class DownloadManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Downloads")
        self.resize(600, 300)
        self.layout = QVBoxLayout(self)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        container = QWidget()
        self.container_layout = QVBoxLayout(container)
        self.scroll.setWidget(container)
        self.layout.addWidget(self.scroll)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Close)
        self.button_box.rejected.connect(self.close)
        self.layout.addWidget(self.button_box)

    def add_download(self, download):
        row = DownloadItemRow(download)
        self.container_layout.addWidget(row)

class Browser(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Peaks Browser")
        self.settings = QSettings("Peaks2000", "PeaksBrowser")
        self.dark_mode = self.settings.value("dark_mode", False, type=bool)
        self.custom_url = self.settings.value("custom_new_tab_url", "", type=str)
        self.download_dialog = DownloadManagerDialog(self)
        self.init_profile()
        self.init_ui()
        if self.dark_mode:
            self.apply_dark_mode()

    def init_profile(self):
        profile = QWebEngineProfile.defaultProfile()
        profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
        storage = os.path.join(os.getcwd(), "web_profile")
        os.makedirs(storage, exist_ok=True)
        profile.setPersistentStoragePath(storage)
        profile.setCachePath(storage)
        profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
        profile.downloadRequested.connect(self.handle_download)

    def init_ui(self):
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(self.show_tab_menu)
        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.load_url)
        self.url_bar.setStyleSheet("border:1px solid #555; border-radius:10px; padding:5px;")
        self.new_tab_btn = self.make_button("+", self.add_tab)
        self.refresh_btn = self.make_button("↻", self.refresh)
        self.fullscreen_btn = self.make_button("⛶", self.toggle_fullscreen)
        self.find_btn = self.make_button("🔍", self.find_text)
        self.download_btn = self.make_button("⬇️", self.open_downloads)
        self.settings_btn = self.make_button("⚙️", self.open_settings)
        nav = QHBoxLayout()
        nav.addWidget(self.url_bar)
        for btn in [self.new_tab_btn, self.refresh_btn, self.fullscreen_btn, self.find_btn, self.download_btn, self.settings_btn]:
            nav.addWidget(btn)
        layout = QVBoxLayout()
        layout.addLayout(nav)
        layout.addWidget(self.tabs)
        self.setLayout(layout)
        self.add_tab()

    def make_button(self, text, handler):
        btn = QPushButton(text)
        btn.setFixedSize(30, 30)
        btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        btn.clicked.connect(handler)
        btn.setStyleSheet("background:transparent; border:none; font-size:16px;")
        return btn

    def add_tab(self, url=None):
        if url is None:
            url = self.custom_url or "https://www.peaks2000.com"
        if not isinstance(url, str):
            url = str(url)
        view = QWebEngineView()
        view.setUrl(QUrl(url))
        idx = self.tabs.addTab(view, "New Tab")
        self.tabs.setCurrentIndex(idx)
        view.titleChanged.connect(lambda title: self.tabs.setTabText(idx, title[:20] + '...' if len(title) > 20 else title))

    def close_tab(self, idx):
        self.tabs.removeTab(idx)

    def show_tab_menu(self, pos):
        idx = self.tabs.tabBar().tabAt(pos)
        if idx == -1:
            return
        menu = QMenu(self)
        rename = QAction("Rename Tab", self)
        rename.triggered.connect(lambda: self.rename_tab(idx))
        menu.addAction(rename)
        menu.exec_(self.tabs.mapToGlobal(pos))

    def rename_tab(self, idx):
        current = self.tabs.tabText(idx)
        text, ok = QInputDialog.getText(self, "Rename Tab", "Tab name:", text=current)
        if ok:
            name = text[:20] + '...' if len(text) > 20 else text
            self.tabs.setTabText(idx, name)

    def load_url(self):
        url = self.url_bar.text()
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        self.tabs.currentWidget().setUrl(QUrl(url))

    def refresh(self):
        current_widget = self.tabs.currentWidget()
        if isinstance(current_widget, QWebEngineView):
            current_widget.reload()

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def find_text(self):
        text, ok = QInputDialog.getText(self, "Find", "Find:")
        if ok:
            self.tabs.currentWidget().findText(text)

    def open_downloads(self):
        self.download_dialog.show()

    def handle_download(self, download):
        fname = os.path.basename(download.url().path())
        path, _ = QFileDialog.getSaveFileName(self, "Save File", fname)
        if path:
            download.setPath(path)
            download.accept()
            self.download_dialog.add_download(download)
            self.download_dialog.show()

    def open_settings(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Settings")
        dlg.setFixedSize(300, 150)
        layout = QVBoxLayout(dlg)
        dark_cb = QCheckBox("Enable Dark Mode")
        dark_cb.setChecked(self.dark_mode)
        url_label = QLabel("Custom New Tab URL:")
        url_input = QLineEdit(self.custom_url)
        box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        box.accepted.connect(dlg.accept)
        box.rejected.connect(dlg.reject)
        layout.addWidget(dark_cb)
        layout.addWidget(url_label)
        layout.addWidget(url_input)
        layout.addWidget(box)
        if dlg.exec_():
            self.dark_mode = dark_cb.isChecked()
            self.custom_url = url_input.text()
            self.settings.setValue("dark_mode", self.dark_mode)
            self.settings.setValue("custom_new_tab_url", self.custom_url)
            if self.dark_mode:
                self.apply_dark_mode()
            else:
                self.remove_dark_mode()

    def apply_dark_mode(self):
        self.setStyleSheet("background-color:#222; color:white;")
        self.url_bar.setStyleSheet("border:1px solid #555; border-radius:10px; padding:5px; color:white; background:#333;")
        for btn in [self.new_tab_btn, self.refresh_btn, self.fullscreen_btn, self.find_btn, self.download_btn, self.settings_btn]:
            btn.setStyleSheet("background:transparent; border:none; font-size:16px; color:white;")
        self.tabs.setStyleSheet(
            "QTabWidget::pane{border:0;}"
            "QTabBar::tab{border:1px solid #555; border-radius:10px; margin:5px; padding:10px; background:#444; color:white;}"
            "QTabBar::tab:selected{background:#666; color:white;}"
            "QTabBar::tab:hover{background:#555;}"
        )

    def remove_dark_mode(self):
        self.setStyleSheet("")
        self.url_bar.setStyleSheet("border:1px solid #555; border-radius:10px; padding:5px; color:black; background:white;")
        for btn in [self.new_tab_btn, self.refresh_btn, self.fullscreen_btn, self.find_btn, self.download_btn, self.settings_btn]:
            btn.setStyleSheet("background:transparent; border:none; font-size:16px; color:inherit;")
        self.tabs.setStyleSheet(
            "QTabWidget::pane{border:0;}"
            "QTabBar::tab{border:1px solid #555; border-radius:10px; margin:5px; padding:10px; background:#f0f0f0; color:black;}"
            "QTabBar::tab:selected{background:#c0c0c0; color:black;}"
            "QTabBar::tab:hover{background:#d0d0d0;}"
        )

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName("Peaks Browser")
    browser = Browser()
    browser.show()
    sys.exit(app.exec_())
