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
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        filter_group = QGroupBox('筛选条件')
        filter_layout = QHBoxLayout(filter_group)
        filter_layout.setSpacing(10)

        filter_layout.addWidget(QLabel('部门:'))
        self.cmb_department = QComboBox()
        self.cmb_department.addItem('全部部门', 'all')
        self.cmb_department.setMinimumWidth(120)
        self.cmb_department.currentIndexChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.cmb_department)

        filter_layout.addWidget(QLabel('人员:'))
        self.cmb_employee = QComboBox()
        self.cmb_employee.addItem('全部人员', 'all')
        self.cmb_employee.setMinimumWidth(120)
        self.cmb_employee.currentIndexChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.cmb_employee)

        filter_layout.addWidget(QLabel('操作类型:'))
        self.cmb_op_type = QComboBox()
        self.cmb_op_type.addItem('全部类型', 'all')
        for op_type in OperationType:
            self.cmb_op_type.addItem(op_type.value, op_type.name)
        self.cmb_op_type.setMinimumWidth(130)
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
        btn_export.setMinimumHeight(34)
        btn_export.setStyleSheet(
            'background: #27ae60; color: white; border-radius: 4px; '
            'padding: 0 14px; font-weight: bold;'
        )
        btn_export.clicked.connect(self._export_audit)
        filter_layout.addWidget(btn_export)

        layout.addWidget(filter_group)

        stat_group = QGroupBox('统计汇总')
        stat_layout = QHBoxLayout(stat_group)
        stat_layout.setSpacing(12)

        self.lbl_total_ops = QLabel('总操作: 0')
        self.lbl_total_ops.setStyleSheet('font-size: 12px; font-weight: bold; padding: 5px 10px; background: #f8f9f9; border-radius: 4px;')
        stat_layout.addWidget(self.lbl_total_ops)
        self.lbl_adjust_count = QLabel('调整: 0')
        self.lbl_adjust_count.setStyleSheet('font-size: 12px; font-weight: bold; padding: 5px 10px; background: #e8f6f3; color: #16a085; border-radius: 4px;')
        stat_layout.addWidget(self.lbl_adjust_count)
        self.lbl_lock_count = QLabel('锁定: 0')
        self.lbl_lock_count.setStyleSheet('font-size: 12px; font-weight: bold; padding: 5px 10px; background: #fadbd8; color: #c0392b; border-radius: 4px;')
        stat_layout.addWidget(self.lbl_lock_count)
        self.lbl_unlock_count = QLabel('解锁: 0')
        self.lbl_unlock_count.setStyleSheet('font-size: 12px; font-weight: bold; padding: 5px 10px; background: #fdebd0; color: #e67e22; border-radius: 4px;')
        stat_layout.addWidget(self.lbl_unlock_count)
        self.lbl_review_count = QLabel('复核: 0')
        self.lbl_review_count.setStyleSheet('font-size: 12px; font-weight: bold; padding: 5px 10px; background: #d4e6f1; color: #2980b9; border-radius: 4px;')
        stat_layout.addWidget(self.lbl_review_count)
        self.lbl_import_count = QLabel('导入: 0')
        self.lbl_import_count.setStyleSheet('font-size: 12px; font-weight: bold; padding: 5px 10px; background: #fef9e7; color: #8e6d00; border-radius: 4px;')
        stat_layout.addWidget(self.lbl_import_count)
        stat_layout.addStretch()
        layout.addWidget(stat_group)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, stretch=1)

        self._init_ops_tab()
        self._init_import_tab()

        self._all_logs = []
        self._filtered_logs = []

    def _init_ops_tab(self):
        ops_tab = QWidget()
        ops_layout = QVBoxLayout(ops_tab)
        ops_layout.setContentsMargins(0, 4, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            '操作时间', '操作类型', '范围', '员工编号', '姓名', '部门', '操作详情', '操作人'
        ])
        for i in range(8):
            if i != 6:
                self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        ops_layout.addWidget(self.table)

        self.tabs.addTab(ops_tab, '操作记录')

    def _init_import_tab(self):
        import_tab = QWidget()
        import_layout = QVBoxLayout(import_tab)
        import_layout.setContentsMargins(0, 4, 0, 0)
        import_layout.setSpacing(8)

        splitter = QSplitter(Qt.Horizontal)

        left_box = QGroupBox('导入批次列表')
        left_layout = QVBoxLayout(left_box)
        self.batch_table = QTableWidget()
        self.batch_table.setColumnCount(7)
        self.batch_table.setHorizontalHeaderLabels([
            '批次ID', '类型', '文件名', '时间', '更新', '新增', '跳过'
        ])
        for i in range(7):
            if i != 2:
                self.batch_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.batch_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.batch_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.batch_table.setAlternatingRowColors(True)
        self.batch_table.verticalHeader().setVisible(False)
        self.batch_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.batch_table.itemSelectionChanged.connect(self._on_batch_selected)
        left_layout.addWidget(self.batch_table)
        splitter.addWidget(left_box)

        right_splitter = QSplitter(Qt.Vertical)

        dept_box = QGroupBox('部门影响面（选中批次 → 按部门汇总）')
        dept_layout = QVBoxLayout(dept_box)
        self.dept_table = QTableWidget()
        self.dept_table.setColumnCount(5)
        self.dept_table.setHorizontalHeaderLabels(['部门', '更新', '新增', '跳过(锁定)', '合计'])
        for i in range(5):
            self.dept_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
        self.dept_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.dept_table.setAlternatingRowColors(True)
        self.dept_table.verticalHeader().setVisible(False)
        self.dept_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.dept_table.itemSelectionChanged.connect(self._on_dept_selected)
        dept_layout.addWidget(self.dept_table)
        right_splitter.addWidget(dept_box)

        people_box = QGroupBox('人员明细（选中部门 → 查看具体人员）')
        people_layout = QVBoxLayout(people_box)
        self.people_table = QTableWidget()
        self.people_table.setColumnCount(5)
        self.people_table.setHorizontalHeaderLabels(['员工编号', '姓名', '部门', '状态', '说明'])
        for i in range(5):
            if i != 4:
                self.people_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.people_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.people_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.people_table.setAlternatingRowColors(True)
        self.people_table.verticalHeader().setVisible(False)
        people_layout.addWidget(self.people_table)
        right_splitter.addWidget(people_box)
        right_splitter.setSizes([200, 250])

        splitter.addWidget(right_splitter)
        splitter.setSizes([520, 480])

        import_layout.addWidget(splitter)
        self.tabs.addTab(import_tab, '导入批次影响面')

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

        if not batches:
            self.dept_table.setRowCount(0)
            self.people_table.setRowCount(0)

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

        dept_summary = {}

        for eid in batch.updated_employees:
            r = self.store.get_record(eid)
            dept = r.department if r else '未知部门'
            if dept not in dept_summary:
                dept_summary[dept] = {'updated': [], 'new': [], 'skipped': []}
            dept_summary[dept]['updated'].append((eid, r.name if r else eid))

        for eid in batch.new_employees:
            r = self.store.get_record(eid)
            dept = r.department if r else '未知部门'
            if dept not in dept_summary:
                dept_summary[dept] = {'updated': [], 'new': [], 'skipped': []}
            dept_summary[dept]['new'].append((eid, r.name if r else eid))

        for eid in batch.skipped_employees:
            r = self.store.get_record(eid)
            dept = r.department if r else '未知部门'
            if dept not in dept_summary:
                dept_summary[dept] = {'updated': [], 'new': [], 'skipped': []}
            dept_summary[dept]['skipped'].append((eid, r.name if r else eid))

        self._current_batch = batch
        self._current_dept_summary = dept_summary

        self.dept_table.setRowCount(len(dept_summary))
        for row, (dept, data) in enumerate(sorted(dept_summary.items())):
            u, n, s = len(data['updated']), len(data['new']), len(data['skipped'])
            values = [dept, str(u), str(n), str(s), str(u + n + s)]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                if col == 3 and s > 0:
                    item.setForeground(QBrush(QColor('#e67e22')))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                item.setData(Qt.UserRole, dept)
                self.dept_table.setItem(row, col, item)

        self.people_table.setRowCount(0)

    def _on_dept_selected(self):
        if not hasattr(self, '_current_dept_summary') or not self._current_dept_summary:
            return
        items = self.dept_table.selectedItems()
        if not items:
            return
        dept = self.dept_table.item(items[0].row(), 0).data(Qt.UserRole)
        if not dept or dept not in self._current_dept_summary:
            return

        data = self._current_dept_summary[dept]
        people = []
        for eid, name in data['updated']:
            people.append((eid, name, dept, '更新', '本次导入更新数据'))
        for eid, name in data['new']:
            people.append((eid, name, dept, '新增', '本次导入新增员工'))
        for eid, name in data['skipped']:
            people.append((eid, name, dept, '跳过(已锁定)', '已锁定未被更新'))

        self.people_table.setRowCount(len(people))
        for row, (eid, name, d, status, note) in enumerate(people):
            values = [eid, name, d, status, note]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter if col != 4 else Qt.AlignVCenter | Qt.AlignLeft)
                if col == 3:
                    if status == '更新':
                        item.setForeground(QBrush(QColor('#2980b9')))
                    elif status == '新增':
                        item.setForeground(QBrush(QColor('#27ae60')))
                    elif '跳过' in status:
                        item.setForeground(QBrush(QColor('#e67e22')))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.people_table.setItem(row, col, item)

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
            people_data = []
            for batch in self.store.get_import_batches():
                type_label = IMPORT_TYPE_LABELS.get(batch.file_type, batch.file_type.value)
                updated_names, new_names, skipped_names = [], [], []
                for eid in batch.updated_employees:
                    r = self.store.get_record(eid)
                    name = r.name if r else eid
                    dept = r.department if r else '-'
                    updated_names.append(f'{name}({eid})')
                    people_data.append({
                        '批次ID': batch.batch_id,
                        '导入类型': type_label,
                        '文件名': batch.file_name,
                        '部门': dept,
                        '员工编号': eid,
                        '姓名': name,
                        '状态': '更新',
                    })
                for eid in batch.new_employees:
                    r = self.store.get_record(eid)
                    name = r.name if r else eid
                    dept = r.department if r else '-'
                    new_names.append(f'{name}({eid})')
                    people_data.append({
                        '批次ID': batch.batch_id,
                        '导入类型': type_label,
                        '文件名': batch.file_name,
                        '部门': dept,
                        '员工编号': eid,
                        '姓名': name,
                        '状态': '新增',
                    })
                for eid in batch.skipped_employees:
                    r = self.store.get_record(eid)
                    name = r.name if r else eid
                    dept = r.department if r else '-'
                    skipped_names.append(f'{name}({eid})')
                    people_data.append({
                        '批次ID': batch.batch_id,
                        '导入类型': type_label,
                        '文件名': batch.file_name,
                        '部门': dept,
                        '员工编号': eid,
                        '姓名': name,
                        '状态': '跳过(已锁定)',
                    })

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
                    pd.DataFrame(batch_data).to_excel(writer, index=False, sheet_name='导入批次汇总')
                if people_data:
                    pd.DataFrame(people_data).to_excel(writer, index=False, sheet_name='导入人员明细')

            parts = []
            if op_data:
                parts.append(f'{len(op_data)}条操作记录')
            if batch_data:
                parts.append(f'{len(batch_data)}条批次汇总')
            if people_data:
                parts.append(f'{len(people_data)}条人员明细')
            QMessageBox.information(self, '提示', f'成功导出: {" + ".join(parts)}')
        except Exception as e:
            QMessageBox.warning(self, '导出失败', f'导出失败: {str(e)}')
