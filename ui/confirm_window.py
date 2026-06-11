import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QComboBox, QMessageBox,
    QFileDialog, QSplitter, QFrame, QInputDialog, QStatusBar, QDialog,
    QTextEdit,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QBrush, QFont

from models.data_store import DataStore
from services.excel_service import export_final_salary, export_review_list, export_adjustments


class ConfirmWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.store = DataStore()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        self.alert_frame = QFrame()
        self.alert_frame.setStyleSheet(
            'background: #fadbd8; border: 2px solid #c0392b; border-radius: 6px;'
        )
        alert_layout = QHBoxLayout(self.alert_frame)
        alert_layout.setContentsMargins(16, 10, 16, 10)
        self.alert_icon = QLabel('⚠')
        self.alert_icon.setStyleSheet('font-size: 22px; color: #c0392b;')
        self.alert_label = QLabel('')
        self.alert_label.setStyleSheet(
            'font-size: 14px; font-weight: bold; color: #c0392b;'
        )
        alert_layout.addWidget(self.alert_icon)
        alert_layout.addWidget(self.alert_label, stretch=1)
        self.alert_frame.hide()

        summary_group = QGroupBox('复核进度总览')
        summary_layout = QHBoxLayout(summary_group)

        self.card_total = self._make_card('总人数', '0', '#3498db')
        self.card_confirmed = self._make_card('已确认/锁定', '0', '#27ae60')
        self.card_unfinished = self._make_card('待处理', '0', '#e74c3c')
        self.card_issues = self._make_card('仍有问题', '0', '#e67e22')
        self.card_adjusted = self._make_card('已调整', '0', '#8e44ad')
        self.card_need_rule = self._make_card('未规则检查', '0', '#e67e22')
        self.card_need_diff = self._make_card('未差异核对', '0', '#e67e22')
        self.card_need_adj = self._make_card('未调整复核', '0', '#e67e22')
        self.card_unresolved = self._make_card('有未解决问题', '0', '#c0392b')

        for card in [self.card_total, self.card_confirmed, self.card_unfinished,
                     self.card_issues, self.card_adjusted, self.card_need_rule,
                     self.card_need_diff, self.card_need_adj, self.card_unresolved]:
            summary_layout.addWidget(card)

        action_group = QGroupBox('操作')
        action_layout = QHBoxLayout(action_group)

        action_layout.addWidget(QLabel('部门筛选:'))
        self.cmb_dept = QComboBox()
        self.cmb_dept.setMinimumWidth(180)
        self.cmb_dept.currentIndexChanged.connect(self._populate_table)
        action_layout.addWidget(self.cmb_dept)

        action_layout.addSpacing(16)

        self.btn_confirm_selected = QPushButton('确认选中（锁定）')
        self.btn_confirm_selected.setStyleSheet(
            'font-size: 13px; font-weight: bold; padding: 6px 16px; '
            'background: #27ae60; color: white; border-radius: 4px;'
        )
        self.btn_confirm_selected.clicked.connect(lambda: self._lock_selected(True))

        self.btn_unlock_selected = QPushButton('取消锁定')
        self.btn_unlock_selected.setStyleSheet(
            'font-size: 13px; font-weight: bold; padding: 6px 16px; '
            'background: #e67e22; color: white; border-radius: 4px;'
        )
        self.btn_unlock_selected.clicked.connect(lambda: self._lock_selected(False))

        self.btn_confirm_all = QPushButton('一键确认全部（无问题）')
        self.btn_confirm_all.setStyleSheet(
            'font-size: 13px; font-weight: bold; padding: 6px 16px; '
            'background: #3498db; color: white; border-radius: 4px;'
        )
        self.btn_confirm_all.clicked.connect(self._confirm_all_clean)

        self.btn_precheck = QPushButton('最终预检报告')
        self.btn_precheck.setStyleSheet(
            'font-size: 13px; font-weight: bold; padding: 6px 16px; '
            'background: #9b59b6; color: white; border-radius: 4px;'
        )
        self.btn_precheck.clicked.connect(self._show_precheck_report)

        action_layout.addWidget(self.btn_confirm_selected)
        action_layout.addWidget(self.btn_unlock_selected)
        action_layout.addWidget(self.btn_confirm_all)
        action_layout.addWidget(self.btn_precheck)
        action_layout.addStretch()

        export_group = QGroupBox('导出')
        export_layout = QHBoxLayout(export_group)
        self.btn_export_final = QPushButton('导出最终发薪表')
        self.btn_export_review = QPushButton('导出复核清单')
        self.btn_export_adj = QPushButton('导出调整记录')
        for btn in [self.btn_export_final, self.btn_export_review, self.btn_export_adj]:
            btn.setMinimumHeight(36)
            btn.setStyleSheet(
                'font-size: 13px; font-weight: bold; padding: 6px 18px;'
            )
        self.btn_export_final.setStyleSheet(
            'font-size: 13px; font-weight: bold; padding: 6px 18px; '
            'background: #8e44ad; color: white; border-radius: 4px;'
        )
        self.btn_export_final.clicked.connect(lambda: self._export('final'))
        self.btn_export_review.clicked.connect(lambda: self._export('review'))
        self.btn_export_adj.clicked.connect(lambda: self._export('adjustments'))
        export_layout.addWidget(self.btn_export_final)
        export_layout.addWidget(self.btn_export_review)
        export_layout.addWidget(self.btn_export_adj)
        export_layout.addStretch()

        table_group = QGroupBox('复核清单')
        table_layout = QVBoxLayout(table_group)
        self.table = QTableWidget()
        self.table.setColumnCount(14)
        self.table.setHorizontalHeaderLabels([
            '员工编号', '姓名', '部门', '实发工资', '上月实发', '波动额',
            '规则检查', '差异核对', '调整复核', '未解决问题数',
            '问题数', '调整次数', '状态', '确认时间'
        ])
        for i in range(14):
            if i in [3, 4, 5, 13]:
                self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
            else:
                self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        table_layout.addWidget(self.table)

        top_layout = QVBoxLayout()
        top_layout.addWidget(self.alert_frame)
        top_layout.addWidget(summary_group)

        action_export_layout = QHBoxLayout()
        action_export_layout.addWidget(action_group, stretch=2)
        action_export_layout.addWidget(export_group, stretch=1)
        top_layout.addLayout(action_export_layout)

        layout.addLayout(top_layout)
        layout.addWidget(table_group, stretch=1)

        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(
            'background: #f8f9fa; border-top: 1px solid #dee2e6; '
            'font-size: 12px; color: #495057;'
        )
        self.status_label = QLabel('')
        self.status_label.setStyleSheet('padding: 2px 8px;')
        self.status_bar.addWidget(self.status_label)
        layout.addWidget(self.status_bar)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(3000)

    def _make_card(self, title: str, value: str, color: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            f'background: white; border: 2px solid {color}; '
            f'border-radius: 8px; padding: 4px;'
        )
        frame.setMinimumHeight(80)
        v = QVBoxLayout(frame)
        v.setContentsMargins(12, 8, 12, 8)
        lbl_val = QLabel(value)
        lbl_val.setAlignment(Qt.AlignCenter)
        lbl_val.setStyleSheet(
            f'font-size: 26px; font-weight: bold; color: {color};'
        )
        lbl_title = QLabel(title)
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet('font-size: 13px; color: #555;')
        v.addWidget(lbl_val)
        v.addWidget(lbl_title)
        frame.value_label = lbl_val
        return frame

    def refresh(self):
        self._reload_depts()
        self._update_summary()
        self._populate_table()
        self._restore_filter_state()

    def _restore_filter_state(self):
        saved_dept = self.store.get_ui_state('confirm_department', '全部')
        idx = self.cmb_dept.findData(saved_dept)
        if idx >= 0:
            self.cmb_dept.blockSignals(True)
            self.cmb_dept.setCurrentIndex(idx)
            self.cmb_dept.blockSignals(False)
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

    def _update_summary(self):
        records = self.store.get_all_records()
        summary = self.store.get_unfinished_review_summary()
        total = summary['total']
        confirmed = summary['locked']
        unfinished = summary['unlocked']
        need_rule = summary['need_rule_check']
        need_diff = summary['need_diff_check']
        need_adj = summary['need_adjustment_review']
        has_issues = summary['has_unresolved_issues']
        with_issues = sum(1 for r in records if r.issues and not r.is_locked)
        adjusted = sum(1 for r in records if r.adjustments)

        self.card_total.value_label.setText(str(total))
        self.card_confirmed.value_label.setText(str(confirmed))
        self.card_unfinished.value_label.setText(str(unfinished))
        self.card_issues.value_label.setText(str(with_issues))
        self.card_adjusted.value_label.setText(str(adjusted))
        self.card_need_rule.value_label.setText(str(need_rule))
        self.card_need_diff.value_label.setText(str(need_diff))
        self.card_need_adj.value_label.setText(str(need_adj))
        self.card_unresolved.value_label.setText(str(has_issues))

        all_unfinished = need_rule + need_diff + need_adj + has_issues
        if all_unfinished > 0:
            parts = []
            if need_rule > 0:
                parts.append(f'{need_rule} 人未完成规则检查')
            if need_diff > 0:
                parts.append(f'{need_diff} 人未完成差异核对')
            if need_adj > 0:
                parts.append(f'{need_adj} 人未完成调整复核')
            if has_issues > 0:
                parts.append(f'{has_issues} 人有未解决问题')
            self.alert_label.setText('⚠ ' + '；'.join(parts) + '，请在发薪前完成全部复核！')
            self.alert_frame.show()
        else:
            self.alert_label.setText('')
            self.alert_frame.hide()

        not_all_complete = sum(1 for r in records if not r.is_locked and not r.is_review_complete())
        if not_all_complete > 0:
            self.status_label.setText(f'还有 {not_all_complete} 人未完成全部复核，{has_issues} 人有未解决问题')
            self.status_label.setStyleSheet('padding: 2px 8px; color: #c0392b; font-weight: bold;')
        else:
            unlocked_no_issues = sum(1 for r in records if not r.is_locked and r.is_review_complete() and not r.has_unresolved_issues())
            if unlocked_no_issues > 0:
                self.status_label.setText(f'所有复核已完成，还有 {unlocked_no_issues} 人待锁定确认')
                self.status_label.setStyleSheet('padding: 2px 8px; color: #e67e22; font-weight: bold;')
            else:
                self.status_label.setText('全部人员已完成复核并锁定')
                self.status_label.setStyleSheet('padding: 2px 8px; color: #27ae60; font-weight: bold;')

    def _populate_table(self):
        self.store.set_ui_state('confirm_department', self.cmb_dept.currentData())
        dept = self.cmb_dept.currentData() or '全部'
        records = self.store.get_records_by_department(dept)
        records = sorted(records, key=lambda r: (1 if r.is_locked else 0, -len(r.issues)))

        self.table.setRowCount(len(records))
        for row, r in enumerate(records):
            s = r.salary
            last = r.last_month_salary
            last_net = last.net_salary if last else 0.0
            diff = round(s.net_salary - last_net, 2) if last else 0.0

            confirm_time = r.confirm_time.strftime('%Y-%m-%d %H:%M:%S') if r.confirm_time else ''

            rule_checked = r.review_steps.rule_checked
            diff_checked = r.review_steps.diff_checked
            adj_reviewed = r.review_steps.adjustment_reviewed
            unresolved_count = len(r.get_unresolved_issues())

            values = [
                r.emp_id, r.name, r.department,
                f'{s.net_salary:.2f}',
                f'{last_net:.2f}' if last else '-',
                f'{diff:+.2f}' if last else '-',
                '✓ 已完成' if rule_checked else '✗ 未完成',
                '✓ 已完成' if diff_checked else '✗ 未完成',
                '✓ 已完成' if adj_reviewed else '✗ 未完成',
                str(unresolved_count),
                str(len(r.issues)),
                str(len(r.adjustments)),
                r.status.value,
                confirm_time
            ]
            for col, v in enumerate(values):
                item = QTableWidgetItem(str(v))
                item.setTextAlignment(Qt.AlignCenter)
                if r.is_locked:
                    item.setBackground(QBrush(QColor('#d5f5e3')))
                    if col == 12:
                        item.setForeground(QBrush(QColor('#27ae60')))
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                else:
                    if r.issues:
                        item.setBackground(QBrush(QColor('#fdebd0')))
                    if col in [6, 7, 8]:
                        if (col == 6 and not rule_checked) or \
                           (col == 7 and not diff_checked) or \
                           (col == 8 and not adj_reviewed):
                            item.setBackground(QBrush(QColor('#fadbd8')))
                            item.setForeground(QBrush(QColor('#c0392b')))
                            font = item.font()
                            font.setBold(True)
                            item.setFont(font)
                        else:
                            item.setForeground(QBrush(QColor('#27ae60')))
                            font = item.font()
                            font.setBold(True)
                            item.setFont(font)
                    if col == 9 and unresolved_count > 0:
                        item.setBackground(QBrush(QColor('#fadbd8')))
                        item.setForeground(QBrush(QColor('#c0392b')))
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                    if col == 10 and len(r.issues) > 0:
                        item.setForeground(QBrush(QColor('#c0392b')))
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                if col == 5 and last and abs(diff) > 0.01:
                    if diff > 0:
                        item.setForeground(QBrush(QColor('#27ae60')))
                    else:
                        item.setForeground(QBrush(QColor('#c0392b')))
                self.table.setItem(row, col, item)
            self.table.item(row, 0).setData(Qt.UserRole, r.emp_id)

    def _lock_selected(self, lock: bool):
        rows = set(i.row() for i in self.table.selectedItems())
        if not rows:
            QMessageBox.information(self, '提示', '请先在表格中选择员工（可按住Ctrl多选）')
            return

        if lock:
            success_count = 0
            skipped_count = 0
            errors = []
            skipped = []

            for row in rows:
                emp_id = self.table.item(row, 0).data(Qt.UserRole)
                if not emp_id:
                    continue
                record = self.store.get_record(emp_id)
                if not record:
                    continue
                if record.is_locked:
                    skipped_count += 1
                    skipped.append(f'{record.name} ({emp_id}) 已是锁定状态')
                    continue
                ok, msg = self.store.lock_record(emp_id, check_review=True)
                if ok:
                    success_count += 1
                else:
                    errors.append(msg)

            msg_parts = []
            if success_count > 0:
                msg_parts.append(f'成功锁定 {success_count} 人')
            if skipped_count > 0:
                msg_parts.append(f'跳过 {skipped_count} 人（已是锁定状态）')
            if errors:
                msg_parts.append(f'失败 {len(errors)} 人：')
                msg_parts.extend([f'  - {e}' for e in errors])
            if skipped:
                msg_parts.append('跳过详情：')
                msg_parts.extend([f'  - {s}' for s in skipped])

            if success_count > 0 and not errors:
                QMessageBox.information(self, '完成', '\n'.join(msg_parts))
            elif errors:
                QMessageBox.warning(self, '部分失败', '\n'.join(msg_parts))
            else:
                QMessageBox.information(self, '提示', '\n'.join(msg_parts))

        else:
            reason, ok = QInputDialog.getText(
                self, '取消锁定', '请输入取消锁定的原因：',
                text=''
            )
            if not ok:
                return
            reason = reason.strip()
            if not reason:
                QMessageBox.warning(self, '提示', '请输入取消锁定的原因')
                return

            success_count = 0
            skipped_count = 0
            errors = []
            skipped = []

            for row in rows:
                emp_id = self.table.item(row, 0).data(Qt.UserRole)
                if not emp_id:
                    continue
                record = self.store.get_record(emp_id)
                if not record:
                    continue
                if not record.is_locked:
                    skipped_count += 1
                    skipped.append(f'{record.name} ({emp_id}) 未处于锁定状态')
                    continue
                ok_unlock, msg = self.store.unlock_record(emp_id, reason)
                if ok_unlock:
                    success_count += 1
                else:
                    errors.append(msg)

            msg_parts = []
            if success_count > 0:
                msg_parts.append(f'成功取消锁定 {success_count} 人')
            if skipped_count > 0:
                msg_parts.append(f'跳过 {skipped_count} 人（未锁定）')
            if errors:
                msg_parts.append(f'失败 {len(errors)} 人：')
                msg_parts.extend([f'  - {e}' for e in errors])
            if skipped:
                msg_parts.append('跳过详情：')
                msg_parts.extend([f'  - {s}' for s in skipped])

            if success_count > 0 and not errors:
                QMessageBox.information(self, '完成', '\n'.join(msg_parts))
            elif errors:
                QMessageBox.warning(self, '部分失败', '\n'.join(msg_parts))
            else:
                QMessageBox.information(self, '提示', '\n'.join(msg_parts))

        self.refresh()

    def _confirm_all_clean(self):
        records = [r for r in self.store.get_all_records() if not r.is_locked]

        ready_count = 0
        skip_reasons = {}

        for r in records:
            reasons = []
            if not r.review_steps.rule_checked:
                reasons.append('未完成规则检查')
            if not r.review_steps.diff_checked:
                reasons.append('未完成差异核对')
            if not r.review_steps.adjustment_reviewed:
                reasons.append('未完成调整复核')
            if r.has_unresolved_issues():
                reasons.append('有未解决问题')

            if reasons:
                skip_reasons[f'{r.name} ({r.emp_id})'] = reasons
            else:
                ready_count += 1

        if ready_count == 0:
            msg_parts = ['没有符合条件的人员可以锁定。']
            if skip_reasons:
                msg_parts.append(f'共 {len(skip_reasons)} 人不满足锁定条件：')
                for name, reasons in skip_reasons.items():
                    msg_parts.append(f'  - {name}: {"、".join(reasons)}')
            QMessageBox.warning(self, '无法锁定', '\n'.join(msg_parts))
            return

        msg_parts = [
            f'将锁定 {ready_count} 名满足条件的人员（所有复核步骤完成、无未解决问题）。',
            f'跳过 {len(skip_reasons)} 名不满足条件的人员。'
        ]
        if skip_reasons:
            msg_parts.append('跳过详情：')
            for name, reasons in list(skip_reasons.items())[:10]:
                msg_parts.append(f'  - {name}: {"、".join(reasons)}')
            if len(skip_reasons) > 10:
                msg_parts.append(f'  ... 还有 {len(skip_reasons) - 10} 人')

        reply = QMessageBox.question(
            self, '确认',
            '\n'.join(msg_parts) + '\n\n是否继续？',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        success_count = 0
        errors = []

        for r in records:
            if f'{r.name} ({r.emp_id})' in skip_reasons:
                continue
            ok, msg = self.store.lock_record(r.emp_id, check_review=True)
            if ok:
                success_count += 1
            else:
                errors.append(msg)

        result_parts = [f'成功锁定 {success_count} 人']
        if len(skip_reasons) > 0:
            result_parts.append(f'跳过 {len(skip_reasons)} 人（不满足锁定条件）')
        if errors:
            result_parts.append(f'失败 {len(errors)} 人：')
            result_parts.extend([f'  - {e}' for e in errors])

        if errors:
            QMessageBox.warning(self, '部分失败', '\n'.join(result_parts))
        else:
            QMessageBox.information(self, '完成', '\n'.join(result_parts))

        self.refresh()

    def _show_precheck_report(self):
        records = self.store.get_all_records()
        unlocked_records = [r for r in records if not r.is_locked]

        ready_count = 0
        not_ready = []
        total_diff_amount = 0.0
        total_issues = 0

        for r in unlocked_records:
            reasons = []
            if not r.review_steps.rule_checked:
                reasons.append('未完成规则检查')
            if not r.review_steps.diff_checked:
                reasons.append('未完成差异核对')
            if not r.review_steps.adjustment_reviewed:
                reasons.append('未完成调整复核')
            unresolved = r.get_unresolved_issues()
            if unresolved:
                reasons.append(f'有 {len(unresolved)} 个未解决问题')
                total_issues += len(unresolved)

            if r.last_month_salary:
                diff = r.salary.net_salary - r.last_month_salary.net_salary
                total_diff_amount += diff

            if reasons:
                not_ready.append({
                    'emp_id': r.emp_id,
                    'name': r.name,
                    'department': r.department,
                    'net_salary': r.salary.net_salary,
                    'last_net': r.last_month_salary.net_salary if r.last_month_salary else None,
                    'diff': (r.salary.net_salary - r.last_month_salary.net_salary) if r.last_month_salary else None,
                    'reasons': reasons,
                    'issues': unresolved,
                })
            else:
                ready_count += 1

        dialog = QDialog(self)
        dialog.setWindowTitle('发薪前最终预检报告')
        dialog.setMinimumSize(900, 650)
        dialog.resize(1000, 700)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)

        header = QLabel('📋 发薪前最终预检报告')
        header.setStyleSheet(
            'font-size: 20px; font-weight: bold; color: #2c3e50; '
            'padding: 8px 0;'
        )
        layout.addWidget(header)

        stat_row = QHBoxLayout()
        stat_row.setSpacing(16)

        total_card = self._make_report_card('总人数', str(len(records)), '#3498db')
        locked_card = self._make_report_card('已锁定', str(len(records) - len(unlocked_records)), '#27ae60')
        ready_card = self._make_report_card('可锁定', str(ready_count), '#27ae60')
        not_ready_card = self._make_report_card('待处理', str(len(not_ready)), '#e74c3c')
        issues_card = self._make_report_card('未解决问题', str(total_issues), '#e67e22')

        for card in [total_card, locked_card, ready_card, not_ready_card, issues_card]:
            stat_row.addWidget(card)
        layout.addLayout(stat_row)

        amount_row = QHBoxLayout()
        amount_label = QLabel(f'本月实发总额：{sum(r.salary.net_salary for r in records):,.2f} 元')
        amount_label.setStyleSheet(
            'font-size: 15px; font-weight: bold; padding: 8px 16px; '
            'background: #e8f6f3; color: #16a085; border-radius: 4px;'
        )
        amount_row.addWidget(amount_label)

        diff_label_text = f'较上月变化：{total_diff_amount:+,.2f} 元'
        diff_label = QLabel(diff_label_text)
        diff_color = '#27ae60' if total_diff_amount >= 0 else '#c0392b'
        diff_label.setStyleSheet(
            f'font-size: 15px; font-weight: bold; padding: 8px 16px; '
            f'background: #f8f9f9; color: {diff_color}; border-radius: 4px;'
        )
        amount_row.addWidget(diff_label)
        amount_row.addStretch()
        layout.addLayout(amount_row)

        detail_group = QGroupBox(f'待处理人员明细（共 {len(not_ready)} 人）')
        detail_layout = QVBoxLayout(detail_group)

        detail_table = QTableWidget()
        detail_table.setColumnCount(7)
        detail_table.setHorizontalHeaderLabels([
            '员工编号', '姓名', '部门', '本月实发', '上月实发', '较上月变化', '未完成项'
        ])
        detail_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        detail_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        detail_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        detail_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        detail_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        detail_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        detail_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        detail_table.setEditTriggers(QTableWidget.NoEditTriggers)
        detail_table.setAlternatingRowColors(True)
        detail_table.setRowCount(len(not_ready))

        for row, item in enumerate(sorted(not_ready, key=lambda x: x['department'])):
            diff_val = item.get('diff')
            diff_text = f'{diff_val:+,.2f}' if diff_val is not None else '-'
            values = [
                item['emp_id'], item['name'], item['department'],
                f'{item["net_salary"]:.2f}',
                f'{item["last_net"]:.2f}' if item['last_net'] is not None else '-',
                diff_text,
                '；'.join(item['reasons']),
            ]
            for col, val in enumerate(values):
                cell = QTableWidgetItem(str(val))
                if col < 6:
                    cell.setTextAlignment(Qt.AlignCenter)
                else:
                    cell.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                cell.setBackground(QBrush(QColor('#fdf2e9')))
                if col == 5 and diff_val is not None:
                    if diff_val > 0:
                        cell.setForeground(QBrush(QColor('#27ae60')))
                    elif diff_val < 0:
                        cell.setForeground(QBrush(QColor('#c0392b')))
                    font = cell.font()
                    font.setBold(True)
                    cell.setFont(font)
                if col == 6:
                    cell.setForeground(QBrush(QColor('#c0392b')))
                    font = cell.font()
                    font.setBold(True)
                    cell.setFont(font)
                detail_table.setItem(row, col, cell)

        detail_layout.addWidget(detail_table)
        layout.addWidget(detail_group, stretch=1)

        issue_summary = QGroupBox('未解决问题汇总')
        issue_layout = QVBoxLayout(issue_summary)
        issue_text = QTextEdit()
        issue_text.setReadOnly(True)
        issue_text.setMaximumHeight(150)

        if not_ready:
            lines = []
            for item in not_ready[:20]:
                if item['issues']:
                    issue_msgs = '; '.join(i.message for i in item['issues'][:3])
                    lines.append(f'【{item["name"]}({item["emp_id"]})】{issue_msgs}')
            if len(not_ready) > 20:
                lines.append(f'... 还有 {len(not_ready) - 20} 人的问题未列出')
            issue_text.setPlainText('\n'.join(lines) if lines else '暂无未解决问题')
        else:
            issue_text.setPlainText('🎉 所有人员均已完成复核，无未解决问题！')

        issue_layout.addWidget(issue_text)
        layout.addWidget(issue_summary)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_close = QPushButton('关闭')
        btn_close.setMinimumWidth(100)
        btn_close.setMinimumHeight(38)
        btn_close.clicked.connect(dialog.reject)
        btn_row.addWidget(btn_close)

        btn_lock_ready = QPushButton('一键锁定可确认人员')
        btn_lock_ready.setMinimumWidth(180)
        btn_lock_ready.setMinimumHeight(38)
        btn_lock_ready.setStyleSheet(
            'font-size: 14px; font-weight: bold; '
            'background: #27ae60; color: white; border-radius: 4px;'
        )
        if ready_count == 0:
            btn_lock_ready.setEnabled(False)
            btn_lock_ready.setText('暂无可锁定人员')
        btn_lock_ready.clicked.connect(lambda: self._lock_ready_from_precheck(dialog, ready_count))
        btn_row.addWidget(btn_lock_ready)

        layout.addLayout(btn_row)

        dialog.exec_()

    def _make_report_card(self, title: str, value: str, color: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            f'background: white; border: 2px solid {color}; '
            f'border-radius: 8px;'
        )
        frame.setMinimumHeight(70)
        v = QVBoxLayout(frame)
        v.setContentsMargins(12, 8, 12, 8)
        v.setSpacing(2)
        lbl_val = QLabel(value)
        lbl_val.setAlignment(Qt.AlignCenter)
        lbl_val.setStyleSheet(
            f'font-size: 22px; font-weight: bold; color: {color};'
        )
        lbl_title = QLabel(title)
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet('font-size: 12px; color: #666;')
        v.addWidget(lbl_val)
        v.addWidget(lbl_title)
        return frame

    def _lock_ready_from_precheck(self, dialog: QDialog, ready_count: int):
        reply = QMessageBox.question(
            self, '确认锁定',
            f'即将锁定 {ready_count} 名已完成全部复核的人员，是否继续？',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        success = 0
        errors = []
        for r in self.store.get_all_records():
            if r.is_locked:
                continue
            if r.review_steps.all_completed() and not r.has_unresolved_issues():
                ok, msg = self.store.lock_record(r.emp_id, check_review=True)
                if ok:
                    success += 1
                else:
                    errors.append(msg)

        dialog.accept()
        self.refresh()

        if errors:
            QMessageBox.warning(self, '部分失败',
                                f'成功锁定 {success} 人，失败 {len(errors)} 人：\n' + '\n'.join(errors))
        else:
            QMessageBox.information(self, '完成', f'成功锁定 {success} 人')

    def _export(self, export_type: str):
        records = self.store.get_all_records()
        if not records:
            QMessageBox.warning(self, '提示', '没有数据可导出')
            return

        default_name = {
            'final': '最终发薪表.xlsx',
            'review': '复核清单.xlsx',
            'adjustments': '调整记录.xlsx',
        }.get(export_type, '导出.xlsx')

        file_path, _ = QFileDialog.getSaveFileName(
            self, '保存导出文件',
            os.path.join(os.getcwd(), default_name),
            'Excel文件 (*.xlsx)'
        )
        if not file_path:
            return

        func_map = {
            'final': export_final_salary,
            'review': export_review_list,
            'adjustments': export_adjustments,
        }
        func = func_map.get(export_type)
        if not func:
            return
        ok, msg = func(file_path)
        if ok:
            QMessageBox.information(self, '导出成功', msg + f'\n文件已保存至:\n{file_path}')
        else:
            QMessageBox.critical(self, '导出失败', msg)
