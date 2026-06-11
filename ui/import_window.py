import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QGroupBox,
    QTextEdit
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush

from models.data_store import DataStore
from services.excel_service import (
    import_salary_excel, import_attendance_excel, import_last_month_salary
)


class ImportWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.store = DataStore()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        btn_group = QGroupBox('数据导入')
        btn_layout = QHBoxLayout(btn_group)

        self.btn_salary = QPushButton('导入本月工资表')
        self.btn_salary.setMinimumHeight(42)
        self.btn_salary.setStyleSheet('font-size: 14px; font-weight: bold; padding: 8px 16px;')
        self.btn_salary.clicked.connect(lambda: self._import_file('salary'))

        self.btn_attendance = QPushButton('导入考勤表')
        self.btn_attendance.setMinimumHeight(42)
        self.btn_attendance.setStyleSheet('font-size: 14px; font-weight: bold; padding: 8px 16px;')
        self.btn_attendance.clicked.connect(lambda: self._import_file('attendance'))

        self.btn_last_month = QPushButton('导入上月工资表（对比用）')
        self.btn_last_month.setMinimumHeight(42)
        self.btn_last_month.setStyleSheet('font-size: 14px; font-weight: bold; padding: 8px 16px;')
        self.btn_last_month.clicked.connect(lambda: self._import_file('last_month'))

        btn_layout.addWidget(self.btn_salary)
        btn_layout.addWidget(self.btn_attendance)
        btn_layout.addWidget(self.btn_last_month)
        btn_layout.addStretch()

        status_group = QGroupBox('导入状态')
        status_layout = QHBoxLayout(status_group)
        self.lbl_salary = QLabel('工资表: 未导入')
        self.lbl_attendance = QLabel('考勤表: 未导入')
        self.lbl_last = QLabel('上月工资: 未导入')
        self.lbl_total = QLabel('员工总数: 0')
        for lbl in [self.lbl_salary, self.lbl_attendance, self.lbl_last, self.lbl_total]:
            lbl.setStyleSheet('font-size: 13px; padding: 4px 12px;')
        status_layout.addWidget(self.lbl_salary)
        status_layout.addWidget(self.lbl_attendance)
        status_layout.addWidget(self.lbl_last)
        status_layout.addStretch()
        status_layout.addWidget(self.lbl_total)

        table_group = QGroupBox('已导入数据预览')
        table_layout = QVBoxLayout(table_group)
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            '员工编号', '姓名', '部门', '职位', '基本工资', '绩效奖金',
            '津贴', '应发工资', '实发工资', '考勤天数'
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet('QTableWidget { gridline-color: #ddd; }')
        table_layout.addWidget(self.table)

        log_group = QGroupBox('导入日志')
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(140)
        self.log_text.setStyleSheet('font-family: Consolas, monospace; font-size: 12px;')
        log_layout.addWidget(self.log_text)

        layout.addWidget(btn_group)
        layout.addWidget(status_group)
        layout.addWidget(table_group, stretch=1)
        layout.addWidget(log_group)

        self.refresh()

    def _import_file(self, file_type: str):
        file_path, _ = QFileDialog.getOpenFileName(
            self, '选择Excel文件', os.getcwd(), 'Excel文件 (*.xlsx *.xls)'
        )
        if not file_path:
            return

        if file_type == 'salary':
            imported, skipped, errors, warnings = import_salary_excel(file_path)
            self._log(f'[工资表] 成功导入 {imported} 条，跳过锁定 {skipped} 人')
            if errors:
                self._log('⚠ 错误: ' + '; '.join(errors))
            if warnings:
                for w in warnings:
                    self._log('⚠ ' + w)
            if imported > 0:
                self.lbl_salary.setText(f'工资表: 已导入 ({imported}人)')
                self.lbl_salary.setStyleSheet('font-size: 13px; padding: 4px 12px; color: #27ae60; font-weight: bold;')

        elif file_type == 'attendance':
            if not self.store.import_status['salary']:
                QMessageBox.warning(self, '提示', '请先导入工资表，再导入考勤表以便按员工编号匹配。')
                return
            matched, mismatched, errors, warnings = import_attendance_excel(file_path)
            self._log(f'[考勤表] 匹配 {matched} 人，未匹配 {mismatched} 人')
            if errors:
                self._log('⚠ 错误: ' + '; '.join(errors))
            if warnings:
                for w in warnings:
                    self._log('⚠ ' + w)
            if matched > 0:
                self.lbl_attendance.setText(f'考勤表: 已导入 ({matched}人匹配)')
                self.lbl_attendance.setStyleSheet('font-size: 13px; padding: 4px 12px; color: #27ae60; font-weight: bold;')

        elif file_type == 'last_month':
            if not self.store.import_status['salary']:
                QMessageBox.warning(self, '提示', '请先导入本月工资表，再导入上月工资表进行对比。')
                return
            matched, mismatched, errors, warnings = import_last_month_salary(file_path)
            self._log(f'[上月工资] 匹配 {matched} 人，{mismatched} 人本月未出现')
            if errors:
                self._log('⚠ 错误: ' + '; '.join(errors))
            if warnings:
                for w in warnings:
                    self._log('⚠ ' + w)
            if matched > 0:
                self.lbl_last.setText(f'上月工资: 已导入 ({matched}人匹配)')
                self.lbl_last.setStyleSheet('font-size: 13px; padding: 4px 12px; color: #27ae60; font-weight: bold;')

        self.refresh()

    def _log(self, msg: str):
        from datetime import datetime
        ts = datetime.now().strftime('%H:%M:%S')
        self.log_text.append(f'[{ts}] {msg}')

    def refresh(self):
        records = self.store.get_all_records()
        self.table.setRowCount(len(records))

        for row, r in enumerate(records):
            s = r.salary
            values = [
                r.emp_id, r.name, r.department, r.position,
                f'{s.base_salary:.2f}', f'{s.performance_bonus:.2f}',
                f'{s.allowance:.2f}', f'{s.gross_salary:.2f}',
                f'{s.net_salary:.2f}', str(r.attendance.work_days)
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                if r.is_locked:
                    item.setBackground(QBrush(QColor('#d5f5e3')))
                self.table.setItem(row, col, item)

        self.lbl_total.setText(f'员工总数: {len(records)}')

        if self.store.import_status['salary']:
            self.lbl_salary.setStyleSheet('font-size: 13px; padding: 4px 12px; color: #27ae60; font-weight: bold;')
        if self.store.import_status['attendance']:
            self.lbl_attendance.setStyleSheet('font-size: 13px; padding: 4px 12px; color: #27ae60; font-weight: bold;')
        if self.store.import_status['last_month']:
            self.lbl_last.setStyleSheet('font-size: 13px; padding: 4px 12px; color: #27ae60; font-weight: bold;')
