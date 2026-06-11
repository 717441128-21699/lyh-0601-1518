from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStatusBar, QMessageBox, QMenuBar, QMenu,
    QAction
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from models.data_store import DataStore
from ui.import_window import ImportWindow
from ui.rule_check_window import RuleCheckWindow
from ui.diff_check_window import DiffCheckWindow
from ui.adjustment_window import AdjustmentWindow
from ui.confirm_window import ConfirmWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.store = DataStore()
        self.setWindowTitle('人力资源薪酬核对系统')
        self.setMinimumSize(1280, 780)
        self.resize(1400, 850)
        self._init_ui()
        self._init_menu()
        self._update_status()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel('人力资源薪酬核对系统')
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('padding: 10px; color: #2c3e50;')

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet('''
            QTabBar::tab {
                padding: 10px 24px;
                font-size: 14px;
                min-width: 120px;
            }
            QTabBar::tab:selected {
                background: #3498db;
                color: white;
                font-weight: bold;
            }
        ''')

        self.import_window = ImportWindow()
        self.rule_window = RuleCheckWindow()
        self.diff_window = DiffCheckWindow()
        self.adjustment_window = AdjustmentWindow()
        self.confirm_window = ConfirmWindow()

        self.tabs.addTab(self.import_window, '1. 数据导入')
        self.tabs.addTab(self.rule_window, '2. 规则检查')
        self.tabs.addTab(self.diff_window, '3. 差异核对')
        self.tabs.addTab(self.adjustment_window, '4. 调整记录')
        self.tabs.addTab(self.confirm_window, '5. 发薪确认')

        self.tabs.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(title)
        layout.addWidget(self.tabs)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _init_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu('文件')
        clear_action = QAction('清空数据', self)
        clear_action.triggered.connect(self._clear_data)
        file_menu.addAction(clear_action)

        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu('帮助')
        about_action = QAction('关于', self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _on_tab_changed(self, index: int):
        if index == 1:
            self.rule_window.refresh()
        elif index == 2:
            self.diff_window.refresh()
        elif index == 3:
            self.adjustment_window.refresh()
        elif index == 4:
            self.confirm_window.refresh()
        self._update_status()

    def _update_status(self):
        total = len(self.store.get_all_records())
        confirmed = self.store.get_confirmed_count()
        unfinished = self.store.get_unfinished_count()
        adj_count = len(self.store.get_adjustments())

        salary_loaded = '是' if self.store.import_status['salary'] else '否'
        attendance_loaded = '是' if self.store.import_status['attendance'] else '否'
        last_loaded = '是' if self.store.import_status['last_month'] else '否'

        msg = (f'总人数: {total} | 已确认: {confirmed} | 待处理: {unfinished} '
               f'| 调整记录: {adj_count} | '
               f'工资表: {salary_loaded} | 考勤表: {attendance_loaded} | 上月数据: {last_loaded}')
        self.status_bar.showMessage(msg)

        if unfinished > 0 and self.tabs.currentIndex() == 4:
            self.status_bar.setStyleSheet('background-color: #e74c3c; color: white; font-weight: bold;')
        else:
            self.status_bar.setStyleSheet('background-color: #ecf0f1; color: #2c3e50;')

    def _clear_data(self):
        reply = QMessageBox.question(
            self, '确认清空', '确定要清空所有已导入的数据吗？此操作不可恢复。',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.store.clear_all()
            for w in [self.import_window, self.rule_window,
                      self.diff_window, self.adjustment_window,
                      self.confirm_window]:
                w.refresh()
            self._update_status()
            QMessageBox.information(self, '已清空', '所有数据已清空。')

    def _show_about(self):
        QMessageBox.information(
            self, '关于',
            '人力资源薪酬核对系统\n\n'
            '功能：\n'
            '1. 数据导入 - 导入工资表、考勤表、上月工资\n'
            '2. 规则检查 - 检查社保、公积金、个税等异常\n'
            '3. 差异核对 - 部门筛选、大额波动、上月对比\n'
            '4. 调整记录 - 录入调整原因，保留修改痕迹\n'
            '5. 发薪确认 - 生成复核清单，锁定人员，导出最终表\n\n'
            '供薪酬专员在发薪前集中核对使用。'
        )
