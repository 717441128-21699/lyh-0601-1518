from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QComboBox, QCheckBox,
    QSplitter
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
        self.main_table.setColumnCount(12)
        self.main_table.setHorizontalHeaderLabels([
            '员工编号', '姓名', '部门', '本月实发', '上月实发', '差异额',
            '差异率', '本月应发', '社保', '公积金', '个税', '状态'
        ])
        for i in range(12):
            if i in [0, 1, 2, 11]:
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

            values = [
                r.emp_id, r.name, r.department,
                f'{s.net_salary:.2f}', f'{last_net:.2f}' if last else '-',
                f'{diff:+.2f}' if last else '-',
                rate_str,
                f'{s.gross_salary:.2f}', f'{s.social_insurance:.2f}',
                f'{s.housing_fund:.2f}', f'{s.personal_tax:.2f}',
                r.status.value
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
