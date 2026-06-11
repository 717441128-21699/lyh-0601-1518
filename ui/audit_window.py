from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QComboBox, QDateEdit,
    QMessageBox, QFrame, QSplitter, QTabWidget, QTextEdit,
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QBrush, QFont
import pandas as pd
from datetime import datetime, time

from models.data_store import DataStore
from models.data_models import OperationType, ImportFileType


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

IMPORT_TYPE_LABELS = {
    ImportFileType.SALARY: '工资表',
    ImportFileType.ATTENDANCE: '考勤表',
    ImportFileType.LAST_MONTH: '上月工资表',
}

BATCH_OP_TYPES = {
    OperationType.SALARY_IMPORTED, OperationType.ATTENDANCE_IMPORTED,
    OperationType.LASTMONTH_IMPORTED, OperationType.BATCH_RULE_CHECK,
    OperationType.BATCH_DIFF_CHECK, OperationType.PROJECT_SAVED,
    OperationType.PROJECT_LOADED,
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
        filter_layout.setSpacing(12)

        filter_layout.addWidget(QLabel('部门:'))
        self.cmb_department = QComboBox()
        self.cmb_department.addItem('全部部门', 'all')
        self.cmb_department.setMinimumWidth(130)
        self.cmb_department.currentIndexChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.cmb_department)

        filter_layout.addWidget(QLabel('人员:'))
        self.cmb_employee = QComboBox()
        self.cmb_employee.addItem('全部人员', 'all')
        self.cmb_employee.setMinimumWidth(130)
        self.cmb_employee.currentIndexChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.cmb_employee)

        filter_layout.addWidget(QLabel('操作类型:'))
        self.cmb_op_type = QComboBox()
        self.cmb_op_type.addItem('全部类型', 'all')
        for op_type in OperationType:
            self.cmb_op_type.addItem(op_type.value, op_type.name)
        self.cmb_op_type.setMinimumWidth(140)
        self.cmb_op_type.currentIndexChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.cmb_op_type)

        filter_layout.addWidget(QLabel('开始:'))
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(QDate.currentDate().addDays(-30))
        self.date_start.setDisplayFormat('yyyy-MM-dd')
        self.date_start.dateChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.date_start)

        filter_layout.addWidget(QLabel('结束:'))
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
            'padding: 0 16px; font-weight: bold;'
        )
        btn_export.clicked.connect(self._export_audit)
        filter_layout.addWidget(btn_export)

        layout.addWidget(filter_group)

        stat_group = QGroupBox('统计汇总')
        stat_layout = QHBoxLayout(stat_group)
        stat_layout.setSpacing(16)

        self.lbl_total_ops = QLabel('总操作: 0')
        self.lbl_total_ops.setStyleSheet('font-size: 13px; font-weight: bold; padding: 6px 12px; background: #f8f9f9; border-radius: 4px;')
        stat_layout.addWidget(self.lbl_total_ops)
        self.lbl_adjust_count = QLabel('调整: 0')
        self.lbl_adjust_count.setStyleSheet('font-size: 13px; font-weight: bold; padding: 6px 12px; background: #e8f6f3; color: #16a085; border-radius: 4px;')
        stat_layout.addWidget(self.lbl_adjust_count)
        self.lbl_lock_count = QLabel('锁定: 0')
        self.lbl_lock_count.setStyleSheet('font-size: 13px; font-weight: bold; padding: 6px 12px; background: #fadbd8; color: #c0392b; border-radius: 4px;')
        stat_layout.addWidget(self.lbl_lock_count)
        self.lbl_unlock_count = QLabel('解锁: 0')
        self.lbl_unlock_count.setStyleSheet('font-size: 13px; font-weight: bold; padding: 6px 12px; background: #fdebd0; color: #e67e22; border-radius: 4px;')
        stat_layout.addWidget(self.lbl_unlock_count)
        self.lbl_review_count = QLabel('复核: 0')
        self.lbl_review_count.setStyleSheet('font-size: 13px; font-weight: bold; padding: 6px 12px; background: #d4e6f1; color: #2980b9; border-radius: 4px;')
        stat_layout.addWidget(self.lbl_review_count)
        self.lbl_import_count = QLabel('导入: 0')
        self.lbl_import_count.setStyleSheet('font-size: 13px; font-weight: bold; padding: 6px 12px; background: #fef9e7; color: #8e6d00; border-radius: 4px;')
        stat_layout.addWidget(self.lbl_import_count)
        stat_layout.addStretch()
        layout.addWidget(stat_group)

        splitter = QSplitter(Qt.Vertical)

        ops_group = QGroupBox('操作记录')
        ops_layout = QVBoxLayout(ops_group)
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            '操作时间', '操作类型', '范围', '员工编号', '姓名', '部门', '操作详情', '操作人'
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        ops_layout.addWidget(self.table)
        splitter.addWidget(ops_group)

        batch_group = QGroupBox('导入批次追踪')
        batch_layout = QVBoxLayout(batch_group)
        self.batch_table = QTableWidget()
        self.batch_table.setColumnCount(8)
        self.batch_table.setHorizontalHeaderLabels([
            '批次ID', '导入类型', '文件名', '导入时间', '更新人数', '新增人数', '跳过锁定', '操作人'
        ])
        self.batch_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.batch_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.batch_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.batch_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.batch_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.batch_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.batch_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.batch_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.batch_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.batch_table.setAlternatingRowColors(True)
        self.batch_table.verticalHeader().setVisible(False)
        self.batch_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.batch_table.itemSelectionChanged.connect(self._on_batch_selected)
        batch_layout.addWidget(self.batch_table)

        self.batch_detail_label = QLabel('选择上方批次查看具体人员明细')
        self.batch_detail_label.setStyleSheet('font-size: 12px; color: #7f8c8d; padding: 4px;')
        batch_layout.addWidget(self.batch_detail_label)

        self.batch_detail = QTextEdit()
        self.batch_detail.setReadOnly(True)
        self.batch_detail.setMaximumHeight(120)
        self.batch_detail.setStyleSheet(
            'background: #fefefe; border: 1px solid #ddd; border-radius: 4px; '
            'font-family: "Microsoft YaHei", monospace; font-size: 12px; padding: 6px;'
        )
        batch_layout.addWidget(self.batch_detail)

        splitter.addWidget(batch_group)
        splitter.setSizes([400, 250])
        layout.addWidget(splitter, stretch=1)

        self._all_logs = []
        self._filtered_logs = []

    def refresh(self):
        self._refresh_filters()
        self._all_logs = sorted(self.store.get_operation_logs(),
                                 key=lambda x: x.operate_time, reverse=True)
        self._apply_filter()
        self._populate_batches()

    def _refresh_filters(self):
        curr_dept = self.cmb_department.currentData()
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
            self.cmb_employee.addItem(f'{emp_id} - {name}', emp_id)
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

            is_batch = log.emp_id == 'BATCH' or log.operation_type in BATCH_OP_TYPES

            if dept_filter != 'all':
                if is_batch:
                    continue
                record = self.store.get_record(log.emp_id)
                if record and record.department != dept_filter:
                    continue

            self._filtered_logs.append(log)

        self._populate_table()
        self._update_stats()

    def _populate_table(self):
        self.table.setRowCount(len(self._filtered_logs))
        for row, log in enumerate(self._filtered_logs):
            is_batch = log.emp_id == 'BATCH' or log.operation_type in BATCH_OP_TYPES
            scope = '全局' if is_batch else '个人'
            record = self.store.get_record(log.emp_id)
            dept = record.department if record and not is_batch else '-'

            values = [
                log.operate_time.strftime('%Y-%m-%d %H:%M:%S'),
                log.operation_type.value,
                scope,
                log.emp_id if not is_batch else '-',
                log.name if not is_batch else '-',
                dept,
                log.detail,
                log.operator,
            ]

            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                if col != 6:
                    item.setTextAlignment(Qt.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

                color = OP_TYPE_COLORS.get(log.operation_type)
                if color:
                    item.setBackground(QBrush(color))

                if col == 2 and is_batch:
                    item.setForeground(QBrush(QColor('#8e44ad')))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)

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
        import_types = {
            OperationType.SALARY_IMPORTED, OperationType.ATTENDANCE_IMPORTED,
            OperationType.LASTMONTH_IMPORTED,
        }
        imports = sum(1 for l in self._filtered_logs if l.operation_type in import_types)

        self.lbl_total_ops.setText(f'总操作: {total}')
        self.lbl_adjust_count.setText(f'调整: {adjust}')
        self.lbl_lock_count.setText(f'锁定: {lock}')
        self.lbl_unlock_count.setText(f'解锁: {unlock}')
        self.lbl_review_count.setText(f'复核: {review}')
        self.lbl_import_count.setText(f'导入: {imports}')

    def _populate_batches(self):
        batches = self.store.get_import_batches()
        self.batch_table.setRowCount(len(batches))
        for row, batch in enumerate(batches):
            type_label = IMPORT_TYPE_LABELS.get(batch.file_type, batch.file_type.value)
            values = [
                batch.batch_id,
                type_label,
                batch.file_name,
                batch.import_time.strftime('%Y-%m-%d %H:%M'),
                str(batch.updated_count),
                str(batch.new_count),
                str(batch.skipped_locked_count),
                batch.operator,
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                if batch.skipped_locked_count > 0 and col == 6:
                    item.setForeground(QBrush(QColor('#e67e22')))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.batch_table.setItem(row, col, item)
            self.batch_table.item(row, 0).setData(Qt.UserRole, batch.batch_id)

        if batches:
            self.batch_detail_label.setText(f'共 {len(batches)} 次导入批次，选择批次查看人员明细')
        else:
            self.batch_detail_label.setText('暂无导入批次记录')
            self.batch_detail.clear()

    def _on_batch_selected(self):
        items = self.batch_table.selectedItems()
        if not items:
            return
        batch_id = self.batch_table.item(items[0].row(), 0).data(Qt.UserRole)
        if not batch_id:
            return

        batches = self.store.get_import_batches()
        batch = None
        for b in batches:
            if b.batch_id == batch_id:
                batch = b
                break
        if not batch:
            return

        lines = []
        type_label = IMPORT_TYPE_LABELS.get(batch.file_type, batch.file_type.value)
        lines.append(f'【{type_label}】{batch.file_name}  导入时间: {batch.import_time.strftime("%Y-%m-%d %H:%M")}  操作人: {batch.operator}')
        lines.append(f'总计 {batch.total_count} 条 | 更新 {batch.updated_count} | 新增 {batch.new_count} | 跳过锁定 {batch.skipped_locked_count}')
        lines.append('')

        if batch.updated_employees:
            names = []
            for eid in batch.updated_employees:
                r = self.store.get_record(eid)
                names.append(f'{r.name}({eid})' if r else eid)
            lines.append(f'✅ 更新人员 ({len(batch.updated_employees)}): {", ".join(names[:30])}')
            if len(batch.updated_employees) > 30:
                lines.append(f'   ... 还有 {len(batch.updated_employees) - 30} 人')

        if batch.new_employees:
            names = []
            for eid in batch.new_employees:
                r = self.store.get_record(eid)
                names.append(f'{r.name}({eid})' if r else eid)
            lines.append(f'🆕 新增人员 ({len(batch.new_employees)}): {", ".join(names[:30])}')
            if len(batch.new_employees) > 30:
                lines.append(f'   ... 还有 {len(batch.new_employees) - 30} 人')

        if batch.skipped_employees:
            names = []
            for eid in batch.skipped_employees:
                r = self.store.get_record(eid)
                names.append(f'{r.name}({eid})' if r else eid)
            lines.append(f'🔒 跳过(已锁定) ({len(batch.skipped_employees)}): {", ".join(names[:30])}')
            if len(batch.skipped_employees) > 30:
                lines.append(f'   ... 还有 {len(batch.skipped_employees) - 30} 人')

        self.batch_detail.setPlainText('\n'.join(lines))

    def _export_audit(self):
        if not self._filtered_logs and not self.store.get_import_batches():
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
            op_data = []
            for log in self._filtered_logs:
                is_batch = log.emp_id == 'BATCH' or log.operation_type in BATCH_OP_TYPES
                record = self.store.get_record(log.emp_id) if not is_batch else None
                dept = record.department if record else '-'
                op_data.append({
                    '操作时间': log.operate_time.strftime('%Y-%m-%d %H:%M:%S'),
                    '操作类型': log.operation_type.value,
                    '范围': '全局' if is_batch else '个人',
                    '员工编号': log.emp_id if not is_batch else '-',
                    '姓名': log.name if not is_batch else '-',
                    '部门': dept,
                    '操作详情': log.detail,
                    '操作人': log.operator,
                    '调整字段': log.field_name if log.field_name else '-',
                    '原值': log.old_value if log.operation_type == OperationType.ADJUSTMENT else '-',
                    '新值': log.new_value if log.operation_type == OperationType.ADJUSTMENT else '-',
                })

            batch_data = []
            for batch in self.store.get_import_batches():
                type_label = IMPORT_TYPE_LABELS.get(batch.file_type, batch.file_type.value)
                updated_names = []
                for eid in batch.updated_employees:
                    r = self.store.get_record(eid)
                    updated_names.append(f'{r.name}({eid})' if r else eid)
                new_names = []
                for eid in batch.new_employees:
                    r = self.store.get_record(eid)
                    new_names.append(f'{r.name}({eid})' if r else eid)
                skipped_names = []
                for eid in batch.skipped_employees:
                    r = self.store.get_record(eid)
                    skipped_names.append(f'{r.name}({eid})' if r else eid)

                batch_data.append({
                    '批次ID': batch.batch_id,
                    '导入类型': type_label,
                    '文件名': batch.file_name,
                    '导入时间': batch.import_time.strftime('%Y-%m-%d %H:%M:%S'),
                    '总条数': batch.total_count,
                    '更新人数': batch.updated_count,
                    '新增人数': batch.new_count,
                    '跳过锁定人数': batch.skipped_locked_count,
                    '操作人': batch.operator,
                    '更新人员': ', '.join(updated_names) if updated_names else '-',
                    '新增人员': ', '.join(new_names) if new_names else '-',
                    '跳过人员(已锁定)': ', '.join(skipped_names) if skipped_names else '-',
                })

            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                if op_data:
                    pd.DataFrame(op_data).to_excel(writer, index=False, sheet_name='操作记录')
                if batch_data:
                    pd.DataFrame(batch_data).to_excel(writer, index=False, sheet_name='导入批次明细')

            total = len(op_data) + len(batch_data)
            QMessageBox.information(self, '提示', f'成功导出 {len(op_data)} 条操作记录 + {len(batch_data)} 条导入批次明细')
        except Exception as e:
            QMessageBox.warning(self, '导出失败', f'导出失败: {str(e)}')
