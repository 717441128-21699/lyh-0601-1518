from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QComboBox, QLineEdit,
    QMessageBox, QSplitter, QTextEdit, QFormLayout, QDoubleSpinBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush

from models.data_store import DataStore
from services.rule_checker import FIELD_NAMES_CN


FIELD_OPTIONS = [
    ('base_salary', '基本工资'),
    ('performance_bonus', '绩效奖金'),
    ('allowance', '津贴'),
    ('social_insurance', '社保'),
    ('housing_fund', '公积金'),
    ('personal_tax', '个税'),
    ('other_deduction', '其他扣款'),
]


class AdjustmentWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.store = DataStore()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        input_group = QGroupBox('录入调整')
        input_layout = QVBoxLayout(input_group)

        form = QFormLayout()
        self.cmb_emp = QComboBox()
        self.cmb_emp.setMinimumWidth(240)
        self.cmb_emp.currentIndexChanged.connect(self._on_emp_changed)
        form.addRow('选择员工:', self.cmb_emp)

        self.cmb_field = QComboBox()
        for key, label in FIELD_OPTIONS:
            self.cmb_field.addItem(label, key)
        self.cmb_field.currentIndexChanged.connect(self._on_field_changed)
        form.addRow('调整字段:', self.cmb_field)

        self.lbl_old = QLabel('-')
        self.lbl_old.setStyleSheet(
            'font-weight: bold; color: #2980b9; font-size: 14px; padding: 4px;'
        )
        form.addRow('当前值:', self.lbl_old)

        self.sp_new = QDoubleSpinBox()
        self.sp_new.setRange(-999999, 999999)
        self.sp_new.setDecimals(2)
        self.sp_new.setSingleStep(100)
        form.addRow('新值:', self.sp_new)

        self.lbl_diff = QLabel('')
        self.lbl_diff.setStyleSheet(
            'font-weight: bold; padding: 4px; font-size: 13px;'
        )
        form.addRow('差额:', self.lbl_diff)

        self.txt_reason = QTextEdit()
        self.txt_reason.setPlaceholderText('请输入调整原因，例如：补上月加班工资、社保基数调整等...')
        self.txt_reason.setMaximumHeight(80)
        form.addRow('调整原因:', self.txt_reason)

        self.sp_new.valueChanged.connect(self._update_diff)

        input_layout.addLayout(form)

        btn_row = QHBoxLayout()
        self.btn_save = QPushButton('保存调整')
        self.btn_save.setMinimumHeight(38)
        self.btn_save.setStyleSheet(
            'font-size: 14px; font-weight: bold; padding: 6px 20px; '
            'background: #27ae60; color: white; border-radius: 4px;'
        )
        self.btn_save.clicked.connect(self._save_adjustment)

        btn_row.addStretch()
        btn_row.addWidget(self.btn_save)
        input_layout.addLayout(btn_row)

        emp_detail_group = QGroupBox('员工当前工资明细')
        emp_detail_layout = QVBoxLayout(emp_detail_group)
        self.emp_detail_table = QTableWidget()
        self.emp_detail_table.setColumnCount(2)
        self.emp_detail_table.setHorizontalHeaderLabels(['项目', '金额'])
        self.emp_detail_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.emp_detail_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.emp_detail_table.setAlternatingRowColors(True)
        self.emp_detail_table.setMaximumHeight(260)
        emp_detail_layout.addWidget(self.emp_detail_table)

        left_layout.addWidget(input_group)
        left_layout.addWidget(emp_detail_group)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        hist_group = QGroupBox('所有调整记录（修改痕迹）')
        hist_layout = QVBoxLayout(hist_group)

        filter_row = QHBoxLayout()
        self.chk_only_current = QComboBox()
        self.chk_only_current.addItem('全部员工', 'all')
        self.chk_only_current.addItem('仅选中员工', 'current')
        self.chk_only_current.currentIndexChanged.connect(self._populate_history)
        filter_row.addWidget(QLabel('筛选:'))
        filter_row.addWidget(self.chk_only_current)
        filter_row.addStretch()
        self.lbl_count = QLabel('共 0 条记录')
        self.lbl_count.setStyleSheet('font-weight: bold; padding: 4px 8px;')
        filter_row.addWidget(self.lbl_count)
        hist_layout.addLayout(filter_row)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(8)
        self.history_table.setHorizontalHeaderLabels([
            '时间', '员工编号', '姓名', '调整字段', '原值', '新值', '差额', '原因'
        ])
        for i in range(8):
            if i in [6, 7]:
                self.history_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
            else:
                self.history_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setAlternatingRowColors(True)
        hist_layout.addWidget(self.history_table)

        right_layout.addWidget(hist_group)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([480, 780])

        layout.addWidget(splitter, stretch=1)

    def refresh(self):
        self._reload_employees()
        self._populate_history()

    def _reload_employees(self):
        current = self.cmb_emp.currentData()
        self.cmb_emp.blockSignals(True)
        self.cmb_emp.clear()
        for r in self.store.get_all_records():
            label = f'{r.emp_id} - {r.name} ({r.department})'
            if r.is_locked:
                label += ' [已锁定]'
            self.cmb_emp.addItem(label, r.emp_id)
        if current:
            idx = self.cmb_emp.findData(current)
            if idx >= 0:
                self.cmb_emp.setCurrentIndex(idx)
        self.cmb_emp.blockSignals(False)
        self._on_emp_changed()

    def _on_emp_changed(self):
        emp_id = self.cmb_emp.currentData()
        if not emp_id:
            self.lbl_old.setText('-')
            self.lbl_diff.setText('')
            self.emp_detail_table.setRowCount(0)
            return
        record = self.store.get_record(emp_id)
        if record and record.is_locked:
            self.btn_save.setEnabled(False)
            self.btn_save.setText('已锁定，无法调整')
            self.btn_save.setStyleSheet(
                'font-size: 14px; font-weight: bold; padding: 6px 20px; '
                'background: #95a5a6; color: white; border-radius: 4px;'
            )
        else:
            self.btn_save.setEnabled(True)
            self.btn_save.setText('保存调整')
            self.btn_save.setStyleSheet(
                'font-size: 14px; font-weight: bold; padding: 6px 20px; '
                'background: #27ae60; color: white; border-radius: 4px;'
            )
        self._on_field_changed()
        self._show_emp_detail(emp_id)

    def _on_field_changed(self):
        emp_id = self.cmb_emp.currentData()
        field = self.cmb_field.currentData()
        if not emp_id or not field:
            self.lbl_old.setText('-')
            return
        record = self.store.get_record(emp_id)
        if not record:
            return
        old = getattr(record.salary, field, 0.0) or 0.0
        self.lbl_old.setText(f'{old:.2f} 元')
        self.sp_new.setValue(float(old))
        self._update_diff()

    def _update_diff(self):
        try:
            old = float(self.lbl_old.text().replace(' 元', ''))
        except (ValueError, AttributeError):
            old = 0.0
        new = self.sp_new.value()
        diff = round(new - old, 2)
        if abs(diff) < 0.01:
            self.lbl_diff.setText('无变化')
            self.lbl_diff.setStyleSheet(
                'font-weight: bold; padding: 4px; font-size: 13px; color: #7f8c8d;'
            )
        else:
            sign = '+' if diff > 0 else ''
            self.lbl_diff.setText(f'{sign}{diff:.2f} 元')
            self.lbl_diff.setStyleSheet(
                'font-weight: bold; padding: 4px; font-size: 13px; '
                f'color: {"#27ae60" if diff > 0 else "#c0392b"};'
            )

    def _show_emp_detail(self, emp_id: str):
        record = self.store.get_record(emp_id)
        if not record:
            self.emp_detail_table.setRowCount(0)
            return
        s = record.salary
        fields = FIELD_OPTIONS + [
            ('gross_salary', '应发工资（合计）'),
            ('net_salary', '实发工资（合计）'),
        ]
        self.emp_detail_table.setRowCount(len(fields))
        for row, (key, label) in enumerate(fields):
            val = getattr(s, key, 0.0) or 0.0
            label_item = QTableWidgetItem(label)
            val_item = QTableWidgetItem(f'{val:.2f}')
            val_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if key in ['gross_salary', 'net_salary']:
                font = label_item.font()
                font.setBold(True)
                label_item.setFont(font)
                val_item.setFont(font)
                val_item.setForeground(QBrush(QColor('#2980b9')))
            self.emp_detail_table.setItem(row, 0, label_item)
            self.emp_detail_table.setItem(row, 1, val_item)

    def _save_adjustment(self):
        emp_id = self.cmb_emp.currentData()
        field = self.cmb_field.currentData()
        if not emp_id:
            QMessageBox.warning(self, '提示', '请选择员工')
            return
        record = self.store.get_record(emp_id)
        if not record:
            return
        if record.is_locked:
            QMessageBox.warning(self, '提示', '该员工已锁定，无法调整')
            return
        reason = self.txt_reason.toPlainText().strip()
        if not reason:
            QMessageBox.warning(self, '提示', '请填写调整原因')
            return

        new_val = round(self.sp_new.value(), 2)
        old = getattr(record.salary, field, 0.0) or 0.0
        if abs(new_val - float(old)) < 0.01:
            QMessageBox.information(self, '提示', '新值与原值相同，无需调整')
            return

        ok = self.store.adjust_salary_field(emp_id, field, new_val, reason)
        if ok:
            field_label = self.cmb_field.currentText()
            QMessageBox.information(
                self, '调整成功',
                f'{record.name} 的 {field_label} 已调整:\n'
                f'{old:.2f} → {new_val:.2f} (差额 {new_val - float(old):+.2f})'
            )
            self.txt_reason.clear()
            self._on_emp_changed()
            self._populate_history()
        else:
            QMessageBox.critical(self, '错误', '调整失败，请重试')

    def _populate_history(self):
        filter_mode = self.chk_only_current.currentData()
        selected_emp = self.cmb_emp.currentData()
        adjustments = self.store.get_adjustments()

        if filter_mode == 'current' and selected_emp:
            adjustments = [a for a in adjustments if a.emp_id == selected_emp]

        adjustments = sorted(adjustments, key=lambda x: x.adjust_time, reverse=True)

        self.history_table.setRowCount(len(adjustments))
        for row, a in enumerate(adjustments):
            diff = round(a.new_value - a.old_value, 2)
            field_label = FIELD_NAMES_CN.get(a.field_name, a.field_name)
            values = [
                a.adjust_time.strftime('%Y-%m-%d %H:%M:%S'),
                a.emp_id, a.name, field_label,
                f'{a.old_value:.2f}', f'{a.new_value:.2f}',
                f'{diff:+.2f}', a.reason
            ]
            for col, v in enumerate(values):
                item = QTableWidgetItem(str(v))
                if col == 6:
                    item.setTextAlignment(Qt.AlignCenter)
                    if diff > 0:
                        item.setForeground(QBrush(QColor('#27ae60')))
                    elif diff < 0:
                        item.setForeground(QBrush(QColor('#c0392b')))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                elif col in [4, 5]:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignCenter)
                self.history_table.setItem(row, col, item)

        self.lbl_count.setText(f'共 {len(adjustments)} 条记录')
