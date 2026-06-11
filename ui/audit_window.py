from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QComboBox, QDateEdit,
    QMessageBox, QFrame
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QBrush, QFont
import pandas as pd
from datetime import datetime, time

from models.data_store import DataStore
from models.data_models import OperationType


OP_TYPE_COLORS = {
    OperationType.ADJUSTMENT: QColor('#e8f6f3'),
    OperationType.LOCK: QColor('#fadbd8'),
    OperationType.UNLOCK: QColor('#fdebd0'),
    OperationType.RULE_CHECKED: QColor('#d4e6f1'),
    OperationType.DIFF_CHECKED: QColor('#e8daef'),
    OperationType.ADJUSTMENT_REVIEWED: QColor('#d5f5e3'),
    OperationType.SALARY_IMPORTED: QColor('#fef9e7'),
    OperationType.ATTENDANCE_IMPORTED: QColor('#fef9e7'),
    OperationType.LASTMONTH_IMPORTED: QColor('#fef9e7'),
    OperationType.ISSUE_RESOLVED: QColor('#d5f5e3'),
    OperationType.BATCH_RULE_CHECK: QColor('#d4e6f1'),
    OperationType.BATCH_DIFF_CHECK: QColor('#e8daef'),
    OperationType.PROJECT_SAVED: QColor('#eaecee'),
    OperationType.PROJECT_LOADED: QColor('#eaecee'),
}


class AuditWindow(QWidget):
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
        filter_layout.setSpacing(16)

        filter_layout.addWidget(QLabel('部门:'))
        self.cmb_department = QComboBox()
        self.cmb_department.addItem('全部部门', 'all')
        self.cmb_department.setMinimumWidth(140)
        self.cmb_department.currentIndexChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.cmb_department)

        filter_layout.addWidget(QLabel('人员:'))
        self.cmb_employee = QComboBox()
        self.cmb_employee.addItem('全部人员', 'all')
        self.cmb_employee.setMinimumWidth(140)
        self.cmb_employee.currentIndexChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.cmb_employee)

        filter_layout.addWidget(QLabel('操作类型:'))
        self.cmb_op_type = QComboBox()
        self.cmb_op_type.addItem('全部类型', 'all')
        for op_type in OperationType:
            self.cmb_op_type.addItem(op_type.value, op_type.name)
        self.cmb_op_type.setMinimumWidth(150)
        self.cmb_op_type.currentIndexChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.cmb_op_type)

        filter_layout.addWidget(QLabel('开始日期:'))
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(QDate.currentDate().addDays(-30))
        self.date_start.setDisplayFormat('yyyy-MM-dd')
        self.date_start.dateChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.date_start)

        filter_layout.addWidget(QLabel('结束日期:'))
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDate(QDate.currentDate())
        self.date_end.setDisplayFormat('yyyy-MM-dd')
        self.date_end.dateChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.date_end)

        filter_layout.addStretch()

        btn_export = QPushButton('导出审计明细')
        btn_export.setMinimumHeight(36)
        btn_export.setStyleSheet(
            'background: #27ae60; color: white; border-radius: 4px; '
            'padding: 0 20px; font-weight: bold;'
        )
        btn_export.clicked.connect(self._export_audit)
        filter_layout.addWidget(btn_export)

        layout.addWidget(filter_group)

        stat_group = QGroupBox('统计汇总')
        stat_layout = QHBoxLayout(stat_group)
        stat_layout.setSpacing(20)

        self.lbl_total_ops = QLabel('总操作数: 0')
        self.lbl_total_ops.setStyleSheet('font-size: 14px; font-weight: bold; padding: 8px 16px; '
                                          'background: #f8f9f9; border-radius: 4px;')
        stat_layout.addWidget(self.lbl_total_ops)

        self.lbl_adjust_count = QLabel('金额调整: 0')
        self.lbl_adjust_count.setStyleSheet('font-size: 14px; font-weight: bold; padding: 8px 16px; '
                                             'background: #e8f6f3; color: #16a085; border-radius: 4px;')
        stat_layout.addWidget(self.lbl_adjust_count)

        self.lbl_lock_count = QLabel('锁定确认: 0')
        self.lbl_lock_count.setStyleSheet('font-size: 14px; font-weight: bold; padding: 8px 16px; '
                                           'background: #fadbd8; color: #c0392b; border-radius: 4px;')
        stat_layout.addWidget(self.lbl_lock_count)

        self.lbl_unlock_count = QLabel('取消锁定: 0')
        self.lbl_unlock_count.setStyleSheet('font-size: 14px; font-weight: bold; padding: 8px 16px; '
                                             'background: #fdebd0; color: #e67e22; border-radius: 4px;')
        stat_layout.addWidget(self.lbl_unlock_count)

        self.lbl_review_count = QLabel('复核操作: 0')
        self.lbl_review_count.setStyleSheet('font-size: 14px; font-weight: bold; padding: 8px 16px; '
                                             'background: #d4e6f1; color: #2980b9; border-radius: 4px;')
        stat_layout.addWidget(self.lbl_review_count)

        stat_layout.addStretch()
        layout.addWidget(stat_group)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            '操作时间', '操作类型', '员工编号', '姓名', '部门', '操作详情', '操作人'
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, stretch=1)

        self._all_logs = []
        self._filtered_logs = []

    def refresh(self):
        self._refresh_filters()
        self._all_logs = sorted(self.store.get_operation_logs(),
                                 key=lambda x: x.operate_time, reverse=True)
        self._apply_filter()

    def _refresh_filters(self):
        curr_dept = self.cmb_department.currentData()
        curr_emp = self.cmb_employee.currentData()

        departments = set()
        for record in self.store.get_all_records():
            if record.department:
                departments.add(record.department)

        self.cmb_department.blockSignals(True)
        self.cmb_department.clear()
        self.cmb_department.addItem('全部部门', 'all')
        for dept in sorted(departments):
            self.cmb_department.addItem(dept, dept)
        idx = self.cmb_department.findData(curr_dept)
        if idx >= 0:
            self.cmb_department.setCurrentIndex(idx)
        self.cmb_department.blockSignals(False)

        self._refresh_employee_filter()

    def _refresh_employee_filter(self):
        curr_emp = self.cmb_employee.currentData()
        dept_filter = self.cmb_department.currentData()

        employees = []
        for record in self.store.get_all_records():
            if dept_filter == 'all' or record.department == dept_filter:
                employees.append((record.emp_id, record.name, record.department))

        self.cmb_employee.blockSignals(True)
        self.cmb_employee.clear()
        self.cmb_employee.addItem('全部人员', 'all')
        for emp_id, name, dept in sorted(employees, key=lambda x: x[0]):
            label = f'{emp_id} - {name}'
            self.cmb_employee.addItem(label, emp_id)
        idx = self.cmb_employee.findData(curr_emp)
        if idx >= 0:
            self.cmb_employee.setCurrentIndex(idx)
        self.cmb_employee.blockSignals(False)

    def _apply_filter(self):
        if self.cmb_department.count() == 0:
            return

        dept_filter = self.cmb_department.currentData()
        emp_filter = self.cmb_employee.currentData()
        op_filter = self.cmb_op_type.currentData()
        start_date = self.date_start.date().toPyDate()
        end_date = self.date_end.date().toPyDate()

        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time.max)

        if self.sender() == self.cmb_department:
            self._refresh_employee_filter()

        self._filtered_logs = []
        for log in self._all_logs:
            if log.operate_time < start_dt or log.operate_time > end_dt:
                continue

            if op_filter != 'all' and log.operation_type.name != op_filter:
                continue

            if emp_filter != 'all' and log.emp_id != emp_filter:
                continue

            if dept_filter != 'all':
                record = self.store.get_record(log.emp_id)
                if record and record.department != dept_filter:
                    continue

            self._filtered_logs.append(log)

        self._populate_table()
        self._update_stats()

    def _populate_table(self):
        self.table.setRowCount(len(self._filtered_logs))

        for row, log in enumerate(self._filtered_logs):
            record = self.store.get_record(log.emp_id)
            dept = record.department if record else '-'

            values = [
                log.operate_time.strftime('%Y-%m-%d %H:%M:%S'),
                log.operation_type.value,
                log.emp_id if log.emp_id != 'BATCH' else '-',
                log.name,
                dept,
                log.detail,
                log.operator,
            ]

            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                if col == 0 or col == 2 or col == 3 or col == 4 or col == 6:
                    item.setTextAlignment(Qt.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

                color = OP_TYPE_COLORS.get(log.operation_type)
                if color:
                    item.setBackground(QBrush(color))

                self.table.setItem(row, col, item)

    def _update_stats(self):
        total = len(self._filtered_logs)
        adjust = sum(1 for l in self._filtered_logs if l.operation_type == OperationType.ADJUSTMENT)
        lock = sum(1 for l in self._filtered_logs if l.operation_type == OperationType.LOCK)
        unlock = sum(1 for l in self._filtered_logs if l.operation_type == OperationType.UNLOCK)
        review_types = {
            OperationType.RULE_CHECKED, OperationType.DIFF_CHECKED,
            OperationType.ADJUSTMENT_REVIEWED, OperationType.BATCH_RULE_CHECK,
            OperationType.BATCH_DIFF_CHECK,
        }
        review = sum(1 for l in self._filtered_logs if l.operation_type in review_types)

        self.lbl_total_ops.setText(f'总操作数: {total}')
        self.lbl_adjust_count.setText(f'金额调整: {adjust}')
        self.lbl_lock_count.setText(f'锁定确认: {lock}')
        self.lbl_unlock_count.setText(f'取消锁定: {unlock}')
        self.lbl_review_count.setText(f'复核操作: {review}')

    def _export_audit(self):
        if not self._filtered_logs:
            QMessageBox.warning(self, '提示', '没有可导出的审计记录！')
            return

        from PyQt5.QtWidgets import QFileDialog
        default_name = f'审计明细_{datetime.now().strftime("%Y%m%d")}.xlsx'
        file_path, _ = QFileDialog.getSaveFileName(
            self, '导出审计明细', default_name, 'Excel文件 (*.xlsx)'
        )
        if not file_path:
            return

        try:
            data = []
            for log in self._filtered_logs:
                record = self.store.get_record(log.emp_id)
                dept = record.department if record else '-'
                data.append({
                    '操作时间': log.operate_time.strftime('%Y-%m-%d %H:%M:%S'),
                    '操作类型': log.operation_type.value,
                    '员工编号': log.emp_id if log.emp_id != 'BATCH' else '-',
                    '姓名': log.name,
                    '部门': dept,
                    '操作详情': log.detail,
                    '操作人': log.operator,
                    '调整字段': log.field_name if log.field_name else '-',
                    '原值': log.old_value if log.operation_type == OperationType.ADJUSTMENT else '-',
                    '新值': log.new_value if log.operation_type == OperationType.ADJUSTMENT else '-',
                })

            df = pd.DataFrame(data)
            df.to_excel(file_path, index=False, sheet_name='审计明细')
            QMessageBox.information(self, '提示', f'成功导出 {len(data)} 条审计记录')
        except Exception as e:
            QMessageBox.warning(self, '导出失败', f'导出失败: {str(e)}')
