from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QComboBox, QSplitter,
    QTextEdit, QFrame, QMenu, QAction, QInputDialog, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush, QFont

from models.data_store import DataStore
from services.rule_checker import RuleChecker, FIELD_NAMES_CN


LEVEL_COLORS = {
    'error': QColor('#fadbd8'),
    'warning': QColor('#fdebd0'),
    'info': QColor('#d4e6f1'),
}

LEVEL_TEXT = {
    'error': '错误',
    'warning': '警告',
    'info': '提示',
}


class RuleCheckWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.store = DataStore()
        self.checker = RuleChecker()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        top = QHBoxLayout()
        self.btn_check = QPushButton('执行规则检查')
        self.btn_check.setMinimumHeight(40)
        self.btn_check.setStyleSheet(
            'font-size: 14px; font-weight: bold; padding: 8px 20px; '
            'background: #3498db; color: white; border-radius: 4px;'
        )
        self.btn_check.clicked.connect(self._run_check)

        self.btn_batch_mark = QPushButton('批量标记规则检查完成')
        self.btn_batch_mark.setMinimumHeight(40)
        self.btn_batch_mark.setStyleSheet(
            'font-size: 14px; font-weight: bold; padding: 8px 20px; '
            'background: #27ae60; color: white; border-radius: 4px;'
        )
        self.btn_batch_mark.clicked.connect(self._batch_mark_rule_checked)

        self.cmb_filter = QComboBox()
        self.cmb_filter.addItem('全部问题', 'all')
        self.cmb_filter.addItem('仅错误', 'error')
        self.cmb_filter.addItem('仅警告', 'warning')
        self.cmb_filter.addItem('仅未解决问题', 'unresolved')
        self.cmb_filter.addItem('社保/公积金', '社保_公积金')
        self.cmb_filter.addItem('个税', '个税')
        self.cmb_filter.addItem('计算错误', '计算')
        self.cmb_filter.currentIndexChanged.connect(self._apply_filter)

        self.lbl_summary = QLabel('尚未执行检查')
        self.lbl_summary.setStyleSheet('font-size: 14px; font-weight: bold; padding: 6px 12px;')

        self.lbl_unfinished = QLabel('未完成规则检查: 0人')
        self.lbl_unfinished.setStyleSheet('font-size: 14px; font-weight: bold; padding: 6px 12px; color: #e67e22;')

        top.addWidget(self.btn_check)
        top.addSpacing(10)
        top.addWidget(self.btn_batch_mark)
        top.addSpacing(20)
        top.addWidget(QLabel('筛选:'))
        top.addWidget(self.cmb_filter)
        top.addStretch()
        top.addWidget(self.lbl_unfinished)
        top.addSpacing(10)
        top.addWidget(self.lbl_summary)

        splitter = QSplitter(Qt.Vertical)

        emp_group = QGroupBox('问题员工列表')
        emp_layout = QVBoxLayout(emp_group)
        self.emp_table = QTableWidget()
        self.emp_table.setColumnCount(7)
        self.emp_table.setHorizontalHeaderLabels([
            '员工编号', '姓名', '部门', '问题数', '最高级别', '规则检查', '状态'
        ])
        self.emp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.emp_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.emp_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.emp_table.setAlternatingRowColors(True)
        self.emp_table.itemSelectionChanged.connect(self._on_emp_selected)
        emp_layout.addWidget(self.emp_table)

        detail_group = QGroupBox('问题明细')
        detail_layout = QVBoxLayout(detail_group)
        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(4)
        self.detail_table.setHorizontalHeaderLabels(['级别', '类别', '问题描述', '操作'])
        self.detail_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.detail_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.detail_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.detail_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.detail_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.detail_table.setAlternatingRowColors(True)
        self.detail_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.detail_table.customContextMenuRequested.connect(self._show_detail_context_menu)
        self.detail_table.cellClicked.connect(self._on_detail_cell_clicked)
        detail_layout.addWidget(self.detail_table)

        legend = QFrame()
        legend_layout = QHBoxLayout(legend)
        legend_layout.setContentsMargins(8, 4, 8, 4)
        for level in ['error', 'warning', 'info']:
            lbl = QLabel(f'■ {LEVEL_TEXT[level]}')
            lbl.setStyleSheet(f'color: {LEVEL_COLORS[level].name() if level != "info" else "#2980b9"}; font-weight: bold; padding: 2px 8px;')
            if level == 'error':
                lbl.setStyleSheet('color: #c0392b; font-weight: bold; padding: 2px 8px;')
            elif level == 'warning':
                lbl.setStyleSheet('color: #e67e22; font-weight: bold; padding: 2px 8px;')
            legend_layout.addWidget(lbl)
        legend_layout.addStretch()
        detail_layout.addWidget(legend)

        splitter.addWidget(emp_group)
        splitter.addWidget(detail_group)
        splitter.setSizes([400, 300])

        layout.addLayout(top)
        layout.addWidget(splitter, stretch=1)

        self._current_issues = {}
        self._all_issues = {}

    def _run_check(self):
        if not self.store.import_status['salary']:
            QMessageBox.warning(self, '提示', '请先导入工资表！')
            return

        self._all_issues = self.checker.check_all(refresh=True)
        self.store.mark_data_changed()
        self._current_issues = dict(self._all_issues)

        total_records = len(self.store.get_all_records())
        records_with_issues = len(self._all_issues)
        error_count = sum(
            1 for issues in self._all_issues.values()
            for i in issues if i.level == 'error'
        )
        warning_count = sum(
            1 for issues in self._all_issues.values()
            for i in issues if i.level == 'warning'
        )
        unfinished_rule = sum(
            1 for r in self.store.get_all_records()
            if not r.is_locked and not r.review_steps.rule_checked
        )

        self.lbl_summary.setText(
            f'检查完成：共{total_records}人，{records_with_issues}人有问题 '
            f'(错误{error_count}个，警告{warning_count}个)'
        )
        self.lbl_summary.setStyleSheet(
            'font-size: 14px; font-weight: bold; padding: 6px 12px; '
            f'color: {"#c0392b" if error_count > 0 else "#e67e22" if warning_count > 0 else "#27ae60"};'
        )
        self.lbl_unfinished.setText(f'未完成规则检查: {unfinished_rule}人')
        self._populate_emp_table()

    def _apply_filter(self):
        if not self._all_issues:
            return
        filter_val = self.cmb_filter.currentData()
        if filter_val == 'all':
            self._current_issues = dict(self._all_issues)
        elif filter_val == 'unresolved':
            self._current_issues = {}
            for emp_id, issues in self._all_issues.items():
                filtered = [i for i in issues if not i.resolved]
                if filtered:
                    self._current_issues[emp_id] = filtered
        elif filter_val in ['error', 'warning']:
            self._current_issues = {}
            for emp_id, issues in self._all_issues.items():
                filtered = [i for i in issues if i.level == filter_val]
                if filtered:
                    self._current_issues[emp_id] = filtered
        else:
            cats = filter_val.split('_')
            self._current_issues = {}
            for emp_id, issues in self._all_issues.items():
                filtered = [i for i in issues if i.category in cats]
                if filtered:
                    self._current_issues[emp_id] = filtered
        self._populate_emp_table()

    def _populate_emp_table(self):
        self.emp_table.setRowCount(len(self._current_issues))
        sorted_items = sorted(
            self._current_issues.items(),
            key=lambda x: (
                0 if any(i.level == 'error' for i in x[1]) else
                1 if any(i.level == 'warning' for i in x[1]) else 2,
                -len(x[1])
            )
        )
        for row, (emp_id, issues) in enumerate(sorted_items):
            record = self.store.get_record(emp_id)
            if not record:
                continue
            max_level = 'info'
            if any(i.level == 'error' for i in issues):
                max_level = 'error'
            elif any(i.level == 'warning' for i in issues):
                max_level = 'warning'

            rule_check_text = '✓已检查' if record.review_steps.rule_checked else '✗未检查'
            values = [
                emp_id, record.name, record.department,
                str(len(issues)), LEVEL_TEXT.get(max_level, max_level),
                rule_check_text, record.status.value
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                if col == 4:
                    if max_level == 'error':
                        item.setForeground(QBrush(QColor('#c0392b')))
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                    elif max_level == 'warning':
                        item.setForeground(QBrush(QColor('#e67e22')))
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                if col == 5:
                    if record.review_steps.rule_checked:
                        item.setForeground(QBrush(QColor('#27ae60')))
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                    else:
                        item.setForeground(QBrush(QColor('#e67e22')))
                if record.is_locked:
                    item.setBackground(QBrush(QColor('#d5f5e3')))
                self.emp_table.setItem(row, col, item)
            self.emp_table.item(row, 0).setData(Qt.UserRole, emp_id)

        self.detail_table.setRowCount(0)

    def _on_emp_selected(self):
        items = self.emp_table.selectedItems()
        if not items:
            return
        emp_id = self.emp_table.item(items[0].row(), 0).data(Qt.UserRole)
        if not emp_id:
            return
        issues = self._current_issues.get(emp_id, [])
        self.detail_table.setRowCount(len(issues))
        for row, issue in enumerate(issues):
            level_text = LEVEL_TEXT.get(issue.level, issue.level)
            if issue.resolved:
                level_text += ' (已解决)'
            level_item = QTableWidgetItem(level_text)
            level_item.setTextAlignment(Qt.AlignCenter)
            level_item.setData(Qt.UserRole, (emp_id, issue.issue_id))
            if issue.resolved:
                level_item.setBackground(QBrush(QColor('#d5f5e3')))
                font = level_item.font()
                font.setStrikeOut(True)
                level_item.setFont(font)
            else:
                level_item.setBackground(QBrush(LEVEL_COLORS.get(issue.level, QColor('#ffffff'))))
            font = level_item.font()
            font.setBold(True)
            level_item.setFont(font)

            cat_item = QTableWidgetItem(issue.category)
            cat_item.setTextAlignment(Qt.AlignCenter)
            cat_item.setData(Qt.UserRole, (emp_id, issue.issue_id))
            if issue.resolved:
                cat_item.setBackground(QBrush(QColor('#d5f5e3')))
                font = cat_item.font()
                font.setStrikeOut(True)
                cat_item.setFont(font)

            msg_text = issue.message
            if issue.resolved and issue.resolve_note:
                msg_text += f'\n备注: {issue.resolve_note}'
            msg_item = QTableWidgetItem(msg_text)
            msg_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            msg_item.setData(Qt.UserRole, (emp_id, issue.issue_id))
            if issue.resolved:
                msg_item.setBackground(QBrush(QColor('#d5f5e3')))
                font = msg_item.font()
                font.setStrikeOut(True)
                msg_item.setFont(font)

            btn_item = QTableWidgetItem()
            btn_item.setTextAlignment(Qt.AlignCenter)
            btn_item.setData(Qt.UserRole, (emp_id, issue.issue_id))
            if issue.resolved:
                btn_item.setText('已解决')
                btn_item.setForeground(QBrush(QColor('#27ae60')))
                btn_item.setBackground(QBrush(QColor('#d5f5e3')))
            else:
                btn_item.setText('标记已解决')
                btn_item.setForeground(QBrush(QColor('#3498db')))
                font = btn_item.font()
                font.setBold(True)
                btn_item.setFont(font)

            self.detail_table.setItem(row, 0, level_item)
            self.detail_table.setItem(row, 1, cat_item)
            self.detail_table.setItem(row, 2, msg_item)
            self.detail_table.setItem(row, 3, btn_item)

    def refresh(self):
        if self.store.import_status['salary']:
            self._all_issues = self.checker.check_all(refresh=True)
            if self._all_issues:
                self._apply_filter()
                unfinished_rule = sum(
                    1 for r in self.store.get_all_records()
                    if not r.is_locked and not r.review_steps.rule_checked
                )
                self.lbl_unfinished.setText(f'未完成规则检查: {unfinished_rule}人')

    def _batch_mark_rule_checked(self):
        if not self.store.import_status['salary']:
            QMessageBox.warning(self, '提示', '请先导入工资表！')
            return
        success, failed, errors = self.store.batch_mark_rule_checked()
        msg = f'批量标记完成：成功{success}人，失败{failed}人'
        if errors:
            msg += '\n\n失败详情：\n' + '\n'.join(errors)
        QMessageBox.information(self, '提示', msg)
        self.refresh()

    def _show_detail_context_menu(self, pos):
        item = self.detail_table.itemAt(pos)
        if not item:
            return
        data = item.data(Qt.UserRole)
        if not data:
            return
        emp_id, issue_id = data
        record = self.store.get_record(emp_id)
        if not record:
            return
        issue = None
        for i in record.issues:
            if i.issue_id == issue_id:
                issue = i
                break
        if not issue or issue.resolved:
            return

        menu = QMenu(self)
        action_resolve = QAction('标记此问题已解决', self)
        action_resolve.triggered.connect(lambda: self._mark_issue_resolved(emp_id, issue_id))
        menu.addAction(action_resolve)
        menu.exec_(self.detail_table.viewport().mapToGlobal(pos))

    def _on_detail_cell_clicked(self, row, col):
        if col != 3:
            return
        item = self.detail_table.item(row, col)
        if not item:
            return
        data = item.data(Qt.UserRole)
        if not data:
            return
        emp_id, issue_id = data
        record = self.store.get_record(emp_id)
        if not record:
            return
        issue = None
        for i in record.issues:
            if i.issue_id == issue_id:
                issue = i
                break
        if not issue or issue.resolved:
            return
        self._mark_issue_resolved(emp_id, issue_id)

    def _mark_issue_resolved(self, emp_id, issue_id):
        record = self.store.get_record(emp_id)
        if not record:
            return
        note, ok = QInputDialog.getText(
            self, '标记问题已解决',
            '请输入解决备注（可选）:',
            text=''
        )
        if not ok:
            return
        ok, msg = self.store.mark_issue_resolved(emp_id, issue_id, note)
        if ok:
            self.refresh()
            QMessageBox.information(self, '提示', msg)
        else:
            QMessageBox.warning(self, '提示', msg)
