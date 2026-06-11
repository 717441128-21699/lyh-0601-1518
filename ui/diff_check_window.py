from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QComboBox, QCheckBox,
    QSplitter, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush

from models.data_store import DataStore


class DiffCheckWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.store = DataStore()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        action_group = QGroupBox('操作')
        action_layout = QHBoxLayout(action_group)

        self.btn_batch_mark = QPushButton('批量标记差异核对完成')
        self.btn_batch_mark.setMinimumHeight(36)
        self.btn_batch_mark.setStyleSheet(
            'font-size: 13px; font-weight: bold; padding: 6px 16px; '
            'background: #27ae60; color: white; border-radius: 4px;'
        )
        self.btn_batch_mark.clicked.connect(self._batch_mark_diff_checked)
        action_layout.addWidget(self.btn_batch_mark)

        self.btn_mark_selected = QPushButton('标记选中人员差异核对完成')
        self.btn_mark_selected.setMinimumHeight(36)
        self.btn_mark_selected.setStyleSheet(
            'font-size: 13px; font-weight: bold; padding: 6px 16px; '
            'background: #3498db; color: white; border-radius: 4px;'
        )
        self.btn_mark_selected.clicked.connect(self._mark_selected_diff_checked)
        action_layout.addWidget(self.btn_mark_selected)

        self.lbl_unfinished_diff = QLabel('')
        self.lbl_unfinished_diff.setStyleSheet(
            'font-size: 13px; font-weight: bold; padding: 4px 12px; '
            'color: #c0392b; background: #fadbd8; border-radius: 4px;'
        )
        action_layout.addStretch()
        action_layout.addWidget(self.lbl_unfinished_diff)

        filter_group = QGroupBox('筛选条件')
        filter_layout = QHBoxLayout(filter_group)

        filter_layout.addWidget(QLabel('部门:'))
        self.cmb_dept = QComboBox()
        self.cmb_dept.setMinimumWidth(160)
        self.cmb_dept.currentIndexChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.cmb_dept)

        self.chk_only_diff = QCheckBox('仅显示有差异/波动')
        self.chk_only_diff.stateChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.chk_only_diff)

        self.chk_only_issue = QCheckBox('仅显示有问题')
        self.chk_only_issue.stateChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.chk_only_issue)

        self.chk_only_unlocked = QCheckBox('仅显示未锁定')
        self.chk_only_unlocked.stateChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.chk_only_unlocked)

        self.lbl_stat = QLabel('')
        self.lbl_stat.setStyleSheet('font-weight: bold; padding: 4px 12px;')
        filter_layout.addStretch()
        filter_layout.addWidget(self.lbl_stat)

        splitter = QSplitter(Qt.Vertical)

        list_group = QGroupBox('员工工资列表')
        list_layout = QVBoxLayout(list_group)
        self.main_table = QTableWidget()
        self.main_table.setColumnCount(16)
        self.main_table.setHorizontalHeaderLabels([
            '员工编号', '姓名', '部门', '本月实发', '上月实发', '差异额',
            '差异率', '本月应发', '社保', '公积金', '个税', '状态',
            '差异核对', '规则检查', '调整复核', '未解决问题数'
        ])
        for i in range(16):
            if i in [0, 1, 2, 11, 12, 13, 14, 15]:
                self.main_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
            else:
                self.main_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
        self.main_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.main_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.main_table.setAlternatingRowColors(True)
        self.main_table.itemSelectionChanged.connect(self._on_row_selected)
        list_layout.addWidget(self.main_table)

        detail_group = QGroupBox('详细对比（选中员工）')
        detail_layout = QVBoxLayout(detail_group)
        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(5)
        self.detail_table.setHorizontalHeaderLabels([
            '项目', '本月金额', '上月金额', '差异额', '差异率'
        ])
        self.detail_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.detail_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.detail_table.setAlternatingRowColors(True)
        detail_layout.addWidget(self.detail_table)

        splitter.addWidget(list_group)
        splitter.addWidget(detail_group)
        splitter.setSizes([420, 260])

        layout.addWidget(action_group)
        layout.addWidget(filter_group)
        layout.addWidget(splitter, stretch=1)

        self._field_labels = [
            ('base_salary', '基本工资'),
            ('performance_bonus', '绩效奖金'),
            ('allowance', '津贴'),
            ('gross_salary', '应发工资'),
            ('social_insurance', '社保'),
            ('housing_fund', '公积金'),
            ('personal_tax', '个税'),
            ('other_deduction', '其他扣款'),
            ('net_salary', '实发工资'),
        ]

    def _apply_filter(self):
        self._populate_table()

    def refresh(self):
        self._reload_depts()
        self._populate_table()
        self._update_unfinished_stat()

    def _reload_depts(self):
        current = self.cmb_dept.currentText()
        self.cmb_dept.blockSignals(True)
        self.cmb_dept.clear()
        self.cmb_dept.addItem('全部', '全部')
        for dept in self.store.get_departments():
            self.cmb_dept.addItem(dept, dept)
        idx = self.cmb_dept.findText(current)
        if idx >= 0:
            self.cmb_dept.setCurrentIndex(idx)
        self.cmb_dept.blockSignals(False)

    def _populate_table(self):
        dept = self.cmb_dept.currentData() or '全部'
        records = self.store.get_records_by_department(dept)
        threshold = self.store.fluctuation_threshold

        filtered = []
        for r in records:
            if self.chk_only_unlocked.isChecked() and r.is_locked:
                continue
            if self.chk_only_issue.isChecked() and not r.issues:
                continue
            if self.chk_only_diff.isChecked():
                if not r.last_month_salary:
                    continue
                diff = r.salary.net_salary - r.last_month_salary.net_salary
                if r.last_month_salary.net_salary > 0:
                    rate = abs(diff) / r.last_month_salary.net_salary
                    if rate <= threshold:
                        continue
                elif abs(diff) <= 0.01:
                    continue
            filtered.append(r)

        self.main_table.setRowCount(len(filtered))
        large_count = 0

        for row, r in enumerate(filtered):
            s = r.salary
            last = r.last_month_salary
            last_net = last.net_salary if last else 0.0
            diff = round(s.net_salary - last_net, 2)
            rate_str = '-'
            highlight = False
            if last and last_net > 0:
                rate = diff / last_net
                rate_str = f'{rate*100:+.1f}%'
                if abs(rate) > threshold:
                    highlight = True
                    large_count += 1

            unresolved_count = len([i for i in r.issues if not i.resolved])
            steps = r.review_steps
            diff_checked = steps.diff_checked
            rule_checked = steps.rule_checked
            adjustment_reviewed = steps.adjustment_reviewed

            values = [
                r.emp_id, r.name, r.department,
                f'{s.net_salary:.2f}', f'{last_net:.2f}' if last else '-',
                f'{diff:+.2f}' if last else '-',
                rate_str,
                f'{s.gross_salary:.2f}', f'{s.social_insurance:.2f}',
                f'{s.housing_fund:.2f}', f'{s.personal_tax:.2f}',
                r.status.value,
                '✓' if diff_checked else '✗',
                '✓' if rule_checked else '✗',
                '✓' if adjustment_reviewed else '✗',
                str(unresolved_count)
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                if r.is_locked:
                    item.setBackground(QBrush(QColor('#d5f5e3')))
                if highlight and col in [5, 6]:
                    item.setBackground(QBrush(QColor('#fadbd8')))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                if r.issues and not r.is_locked:
                    if col == 11:
                        item.setForeground(QBrush(QColor('#c0392b')))
                if col in [12, 13, 14]:
                    if val == '✓':
                        item.setForeground(QBrush(QColor('#27ae60')))
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                    else:
                        item.setForeground(QBrush(QColor('#c0392b')))
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                if col == 15 and unresolved_count > 0:
                    item.setForeground(QBrush(QColor('#c0392b')))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.main_table.setItem(row, col, item)
            self.main_table.item(row, 0).setData(Qt.UserRole, r.emp_id)

        total = len(filtered)
        self.lbl_stat.setText(
            f'共 {total} 人 | 大额波动: {large_count} 人'
            + (f' (阈值±{threshold*100:.0f}%)' if large_count else '')
        )
        if large_count > 0:
            self.lbl_stat.setStyleSheet(
                'font-weight: bold; padding: 4px 12px; color: #c0392b;'
            )
        else:
            self.lbl_stat.setStyleSheet(
                'font-weight: bold; padding: 4px 12px; color: #27ae60;'
            )

        self.detail_table.setRowCount(0)

    def _on_row_selected(self):
        items = self.main_table.selectedItems()
        if not items:
            return
        emp_id = self.main_table.item(items[0].row(), 0).data(Qt.UserRole)
        record = self.store.get_record(emp_id)
        if not record:
            return

        self.detail_table.setRowCount(len(self._field_labels))
        s = record.salary
        last = record.last_month_salary

        for row, (field, label) in enumerate(self._field_labels):
            curr_val = getattr(s, field, 0.0) or 0.0
            last_val = getattr(last, field, 0.0) if last else 0.0
            diff = round(curr_val - last_val, 2)
            rate_str = '-'
            if last and last_val > 0:
                rate = diff / last_val
                rate_str = f'{rate*100:+.1f}%'

            vals = [label, f'{curr_val:.2f}',
                    f'{last_val:.2f}' if last else '-',
                    f'{diff:+.2f}' if last else '-', rate_str]
            for col, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setTextAlignment(Qt.AlignCenter)
                if col >= 3 and last and abs(diff) > 0.01:
                    color = '#fadbd8' if diff < 0 else '#d5f5e3'
                    item.setBackground(QBrush(QColor(color)))
                self.detail_table.setItem(row, col, item)

    def _update_unfinished_stat(self):
        summary = self.store.get_unfinished_review_summary()
        need_diff = summary['need_diff_check']
        if need_diff > 0:
            self.lbl_unfinished_diff.setText(f'未完成差异核对: {need_diff} 人')
            self.lbl_unfinished_diff.setStyleSheet(
                'font-size: 13px; font-weight: bold; padding: 4px 12px; '
                'color: #c0392b; background: #fadbd8; border-radius: 4px;'
            )
        else:
            self.lbl_unfinished_diff.setText('差异核对已全部完成 ✓')
            self.lbl_unfinished_diff.setStyleSheet(
                'font-size: 13px; font-weight: bold; padding: 4px 12px; '
                'color: #27ae60; background: #d5f5e3; border-radius: 4px;'
            )

    def _batch_mark_diff_checked(self):
        reply = QMessageBox.question(
            self, '确认批量标记',
            '确定要将所有未锁定人员标记为差异核对完成吗？',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        success, failed, errors = self.store.batch_mark_diff_checked()
        self.refresh()
        msg = f'批量标记完成：成功 {success} 人'
        if failed > 0:
            msg += f'，失败 {failed} 人'
            if errors:
                msg += '\n\n失败详情：\n' + '\n'.join(errors[:5])
                if len(errors) > 5:
                    msg += f'\n... 共 {failed} 条错误'
        QMessageBox.information(self, '完成', msg)

    def _mark_selected_diff_checked(self):
        items = self.main_table.selectedItems()
        if not items:
            QMessageBox.warning(self, '提示', '请先选择要标记的员工！')
            return
        emp_id = self.main_table.item(items[0].row(), 0).data(Qt.UserRole)
        record = self.store.get_record(emp_id)
        if not record:
            QMessageBox.warning(self, '提示', '未找到该员工记录！')
            return
        if record.is_locked:
            QMessageBox.warning(self, '提示', f'员工 {record.name} 已锁定，无法标记。')
            return
        reply = QMessageBox.question(
            self, '确认标记',
            f'确定要将员工 {record.name} ({record.emp_id}) 标记为差异核对完成吗？',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        ok, msg = self.store.mark_diff_checked(emp_id)
        self.refresh()
        if ok:
            QMessageBox.information(self, '完成', msg)
        else:
            QMessageBox.warning(self, '失败', msg)
