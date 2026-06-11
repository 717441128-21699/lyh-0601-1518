import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStatusBar, QMessageBox, QMenuBar, QMenu,
    QAction, QFileDialog, QInputDialog
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon

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

        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.timeout.connect(self._auto_save_check)
        self._auto_save_timer.start(30000)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)

        title_row = QHBoxLayout()
        self.title_label = QLabel('人力资源薪酬核对系统')
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet('padding: 10px; color: #2c3e50;')

        self.project_label = QLabel('')
        self.project_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.project_label.setStyleSheet('font-size: 12px; color: #7f8c8d; padding-right: 10px;')

        title_row.addWidget(self.title_label, stretch=1)
        title_row.addWidget(self.project_label, stretch=0)

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

        layout.addLayout(title_row)
        layout.addWidget(self.tabs)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _init_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu('文件(&F)')

        new_action = QAction('新建项目(&N)', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self._new_project)
        file_menu.addAction(new_action)

        open_action = QAction('打开项目(&O)...', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self._open_project)
        file_menu.addAction(open_action)

        save_action = QAction('保存项目(&S)', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self._save_project)
        file_menu.addAction(save_action)

        save_as_action = QAction('项目另存为(&A)...', self)
        save_as_action.setShortcut('Ctrl+Shift+S')
        save_as_action.triggered.connect(self._save_project_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        clear_action = QAction('清空数据', self)
        clear_action.triggered.connect(self._clear_data)
        file_menu.addAction(clear_action)

        file_menu.addSeparator()

        exit_action = QAction('退出(&X)', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu('帮助(&H)')
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
        summary = self.store.get_unfinished_review_summary()

        from models.data_models import OperationType
        adj_count = len([l for l in self.store.get_operation_logs()
                         if l.operation_type == OperationType.ADJUSTMENT])

        salary_loaded = '是' if self.store.import_status['salary'] else '否'
        attendance_loaded = '是' if self.store.import_status['attendance'] else '否'
        last_loaded = '是' if self.store.import_status['last_month'] else '否'

        msg = (f'总人数: {total} | 已确认锁定: {confirmed} | 待处理: {unfinished} '
               f'| 未规则检查: {summary["need_rule_check"]} '
               f'| 未差异核对: {summary["need_diff_check"]} '
               f'| 未调整复核: {summary["need_adjustment_review"]} '
               f'| 有未解决问题: {summary["has_unresolved_issues"]} '
               f'| 调整记录: {adj_count}')
        self.status_bar.showMessage(msg)

        if unfinished > 0 and self.tabs.currentIndex() == 4:
            self.status_bar.setStyleSheet(
                'background-color: #e74c3c; color: white; font-weight: bold;'
            )
        elif self.store.data_changed:
            self.status_bar.setStyleSheet(
                'background-color: #f39c12; color: white; font-weight: bold;'
            )
        else:
            self.status_bar.setStyleSheet(
                'background-color: #ecf0f1; color: #2c3e50;'
            )

        self._update_project_label()

    def _update_project_label(self):
        if self.store.current_project_path:
            name = os.path.basename(self.store.current_project_path)
            changed = ' *' if self.store.data_changed else ''
            self.project_label.setText(f'项目: {name}{changed}')
            self.setWindowTitle(f'人力资源薪酬核对系统 - {name}{changed}')
        else:
            changed = ' *' if self.store.data_changed else ''
            self.project_label.setText(f'未保存项目{changed}')
            self.setWindowTitle(f'人力资源薪酬核对系统 - 未保存{changed}')

    def _auto_save_check(self):
        pass

    def _check_unsaved_changes(self) -> bool:
        if not self.store.data_changed:
            return True
        reply = QMessageBox.question(
            self, '未保存的更改',
            '当前项目有未保存的更改，是否先保存？',
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Cancel:
            return False
        if reply == QMessageBox.Yes:
            return self._save_project()
        return True

    def _new_project(self):
        if not self._check_unsaved_changes():
            return
        if len(self.store.get_all_records()) > 0:
            reply = QMessageBox.question(
                self, '确认新建',
                '确定要新建项目吗？当前数据将被清空。',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        self.store.clear_all()
        self._refresh_all_windows()
        self._update_status()
        QMessageBox.information(self, '已新建', '新项目已创建，可以开始导入数据了。')

    def _open_project(self):
        if not self._check_unsaved_changes():
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, '打开项目文件', os.getcwd(),
            '薪酬核对项目 (*.salaryproj);;所有文件 (*.*)'
        )
        if not file_path:
            return
        ok, msg = self.store.load_project(file_path)
        if ok:
            self._refresh_all_windows()
            self._update_status()
            QMessageBox.information(self, '加载成功', msg)
        else:
            QMessageBox.critical(self, '加载失败', msg)

    def _save_project(self) -> bool:
        if self.store.current_project_path:
            ok, msg = self.store.save_project(self.store.current_project_path)
            if ok:
                self._update_status()
                return True
            else:
                QMessageBox.critical(self, '保存失败', msg)
                return False
        else:
            return self._save_project_as()

    def _save_project_as(self) -> bool:
        default_name = '薪酬核对项目.salaryproj'
        if self.store.current_month:
            default_name = f'{self.store.current_month}薪酬核对.salaryproj'
        file_path, _ = QFileDialog.getSaveFileName(
            self, '保存项目',
            os.path.join(os.getcwd(), default_name),
            '薪酬核对项目 (*.salaryproj)'
        )
        if not file_path:
            return False

        note, ok = QInputDialog.getText(
            self, '项目备注', '请输入项目备注（可选）:',
            text=self.store.project_meta.note if self.store.project_meta else ''
        )
        if not ok:
            note = ''

        project_name = os.path.splitext(os.path.basename(file_path))[0]
        ok, msg = self.store.save_project(file_path, project_name, note)
        if ok:
            self._update_status()
            QMessageBox.information(self, '保存成功', msg)
            return True
        else:
            QMessageBox.critical(self, '保存失败', msg)
            return False

    def _refresh_all_windows(self):
        for w in [self.import_window, self.rule_window,
                  self.diff_window, self.adjustment_window,
                  self.confirm_window]:
            w.refresh()

    def _clear_data(self):
        reply = QMessageBox.question(
            self, '确认清空',
            '确定要清空所有已导入的数据吗？此操作不可恢复。\n\n建议先保存项目。',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.store.clear_all()
            self._refresh_all_windows()
            self._update_status()
            QMessageBox.information(self, '已清空', '所有数据已清空。')

    def closeEvent(self, event):
        if not self._check_unsaved_changes():
            event.ignore()
            return
        event.accept()

    def _show_about(self):
        QMessageBox.information(
            self, '关于',
            '人力资源薪酬核对系统 v2.0\n\n'
            '核心功能：\n'
            '1. 数据导入 - 导入工资表、考勤表、上月工资（自动跳过已锁定人员）\n'
            '2. 规则检查 - 检查社保、公积金、个税等异常，支持问题标记解决\n'
            '3. 差异核对 - 部门筛选、大额波动、上月对比，标记核对完成\n'
            '4. 调整记录 - 录入调整原因，保留修改痕迹，取消锁定留痕\n'
            '5. 发薪确认 - 复核闭环检查（规则检查/差异核对/调整复核），未完成禁止锁定\n\n'
            '新增功能：\n'
            '• 项目保存/打开 - 关闭软件后可继续工作\n'
            '• 完整锁定保护 - 已确认人员禁止导入/调整/批量操作\n'
            '• 状态实时联动 - 调整后问题自动刷新，所有窗口状态一致\n'
            '• 复核步骤跟踪 - 明确显示哪些复核步骤未完成\n\n'
            '供薪酬专员在发薪前集中核对使用。'
        )
