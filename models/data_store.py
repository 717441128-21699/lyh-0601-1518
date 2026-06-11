import json
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from .data_models import (
    SalaryRecord, AdjustmentRecord, SalaryData,
    AttendanceData, Employee, SalaryStatus,
    OperationType, OperationLog, IssueItem,
    ProjectMeta, ReviewSteps, ImportBatch, ImportFileType
)


def _salary_data_to_dict(s: SalaryData) -> Dict:
    if s is None:
        return None
    return {
        'emp_id': s.emp_id,
        'base_salary': s.base_salary,
        'performance_bonus': s.performance_bonus,
        'allowance': s.allowance,
        'social_insurance': s.social_insurance,
        'housing_fund': s.housing_fund,
        'personal_tax': s.personal_tax,
        'other_deduction': s.other_deduction,
        'gross_salary': s.gross_salary,
        'net_salary': s.net_salary,
    }


def _salary_data_from_dict(d: Dict) -> Optional[SalaryData]:
    if d is None:
        return None
    return SalaryData(**d)


def _attendance_data_to_dict(a: AttendanceData) -> Dict:
    return {
        'emp_id': a.emp_id,
        'work_days': a.work_days,
        'overtime_hours': a.overtime_hours,
        'leave_days': a.leave_days,
        'sick_days': a.sick_days,
        'late_times': a.late_times,
        'absenteeism_days': a.absenteeism_days,
    }


def _attendance_data_from_dict(d: Dict) -> AttendanceData:
    return AttendanceData(**d)


def _review_steps_to_dict(r: ReviewSteps) -> Dict:
    return {
        'rule_checked': r.rule_checked,
        'diff_checked': r.diff_checked,
        'adjustment_reviewed': r.adjustment_reviewed,
        'rule_check_time': r.rule_check_time.isoformat() if r.rule_check_time else None,
        'diff_check_time': r.diff_check_time.isoformat() if r.diff_check_time else None,
        'adjustment_review_time': r.adjustment_review_time.isoformat() if r.adjustment_review_time else None,
    }


def _review_steps_from_dict(d: Dict) -> ReviewSteps:
    r = ReviewSteps(
        rule_checked=d.get('rule_checked', False),
        diff_checked=d.get('diff_checked', False),
        adjustment_reviewed=d.get('adjustment_reviewed', False),
    )
    if d.get('rule_check_time'):
        r.rule_check_time = datetime.fromisoformat(d['rule_check_time'])
    if d.get('diff_check_time'):
        r.diff_check_time = datetime.fromisoformat(d['diff_check_time'])
    if d.get('adjustment_review_time'):
        r.adjustment_review_time = datetime.fromisoformat(d['adjustment_review_time'])
    return r


def _record_to_dict(r: SalaryRecord) -> Dict:
    return {
        'emp_id': r.emp_id,
        'name': r.name,
        'department': r.department,
        'position': r.position,
        'salary': _salary_data_to_dict(r.salary),
        'attendance': _attendance_data_to_dict(r.attendance),
        'last_month_salary': _salary_data_to_dict(r.last_month_salary),
        'status': r.status.name,
        'issues': [i.to_dict() for i in r.issues],
        'issue_messages': r.issue_messages,
        'review_steps': _review_steps_to_dict(r.review_steps),
        'adjustments': [a.to_dict() for a in r.adjustments],
        'is_locked': r.is_locked,
        'confirm_time': r.confirm_time.isoformat() if r.confirm_time else None,
        'unlock_time': r.unlock_time.isoformat() if r.unlock_time else None,
    }


def _record_from_dict(d: Dict) -> SalaryRecord:
    r = SalaryRecord(
        emp_id=d['emp_id'],
        name=d['name'],
        department=d['department'],
        position=d.get('position', ''),
        salary=_salary_data_from_dict(d.get('salary', {})),
        attendance=_attendance_data_from_dict(d.get('attendance', {})),
        last_month_salary=_salary_data_from_dict(d.get('last_month_salary')),
        status=SalaryStatus[d.get('status', 'PENDING')],
        issues=[IssueItem.from_dict(i) for i in d.get('issues', [])],
        issue_messages=d.get('issue_messages', []),
        review_steps=_review_steps_from_dict(d.get('review_steps', {})),
        adjustments=[OperationLog.from_dict(a) for a in d.get('adjustments', [])],
        is_locked=d.get('is_locked', False),
    )
    if d.get('confirm_time'):
        r.confirm_time = datetime.fromisoformat(d['confirm_time'])
    if d.get('unlock_time'):
        r.unlock_time = datetime.fromisoformat(d['unlock_time'])
    return r


class DataStore:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.records: Dict[str, SalaryRecord] = {}
        self.operation_logs: List[OperationLog] = []
        self.employees: Dict[str, Employee] = {}
        self.last_month_data: Dict[str, SalaryData] = {}
        self.import_status: Dict[str, bool] = {
            'salary': False, 'attendance': False, 'last_month': False
        }
        self.current_month: str = ''
        self.operator: str = '薪酬专员'
        self.social_insurance_rate: float = 0.105
        self.housing_fund_rate: float = 0.12
        self.tax_threshold: float = 5000
        self.fluctuation_threshold: float = 0.20
        self.current_project_path: Optional[str] = None
        self.project_meta: Optional[ProjectMeta] = None
        self.data_changed: bool = False
        self.import_batches: List[ImportBatch] = []
        self.ui_state: Dict[str, Any] = {
            'current_tab': 0,
            'rule_filter': 'all',
            'diff_department': '全部',
            'diff_only_diff': False,
            'diff_only_issue': False,
            'diff_only_unlocked': False,
            'adj_filter_type': 'all',
            'adj_filter_emp': 'all',
            'confirm_department': '全部',
        }

    def _log_operation(self, op_type: OperationType, emp_id: str, name: str,
                       detail: str, field_name: str = '',
                       old_value: float = 0.0, new_value: float = 0.0) -> OperationLog:
        log = OperationLog(
            operation_type=op_type,
            emp_id=emp_id,
            name=name,
            detail=detail,
            operator=self.operator,
            operate_time=datetime.now(),
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
        )
        self.operation_logs.append(log)
        self.data_changed = True
        return log

    def mark_data_changed(self):
        self.data_changed = True

    def add_employee(self, emp: Employee):
        self.employees[emp.emp_id] = emp

    def add_or_update_record(self, record: SalaryRecord, check_lock: bool = True) -> Tuple[bool, str]:
        existing = self.records.get(record.emp_id)
        if check_lock and existing and existing.is_locked:
            return False, f'员工 {record.name} ({record.emp_id}) 已锁定，无法更新'
        self.records[record.emp_id] = record
        self.data_changed = True
        return True, 'success'

    def get_record(self, emp_id: str) -> Optional[SalaryRecord]:
        return self.records.get(emp_id)

    def get_all_records(self) -> List[SalaryRecord]:
        return list(self.records.values())

    def get_departments(self) -> List[str]:
        depts = {r.department for r in self.records.values() if r.department}
        return sorted(list(depts))

    def get_operation_logs(self) -> List[OperationLog]:
        return self.operation_logs

    def get_operation_logs_by_emp(self, emp_id: str) -> List[OperationLog]:
        return [l for l in self.operation_logs if l.emp_id == emp_id]

    def get_operation_logs_by_type(self, op_type: OperationType) -> List[OperationLog]:
        return [l for l in self.operation_logs if l.operation_type == op_type]

    def adjust_salary_field(self, emp_id: str, field_name: str,
                            new_value: float, reason: str) -> Tuple[bool, str]:
        record = self.records.get(emp_id)
        if not record:
            return False, '员工不存在'
        if record.is_locked:
            return False, f'员工 {record.name} 已锁定，无法调整金额。如需调整请先取消锁定。'
        salary = record.salary
        old_value = getattr(salary, field_name, None)
        if old_value is None:
            return False, '字段不存在'
        old_value = float(old_value)
        if abs(old_value - new_value) < 0.01:
            return False, '新值与原值相同，无需调整'

        from services.rule_checker import FIELD_NAMES_CN
        field_label = FIELD_NAMES_CN.get(field_name, field_name)
        log = self._log_operation(
            OperationType.ADJUSTMENT,
            emp_id=emp_id,
            name=record.name,
            detail=f'{field_label}: {old_value:.2f} → {new_value:.2f}，原因：{reason}',
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
        )

        record.adjustments.append(log)
        setattr(salary, field_name, new_value)
        self._recalculate_salary(emp_id)
        record.status = SalaryStatus.ADJUSTED
        record.review_steps.adjustment_reviewed = False
        record.review_steps.adjustment_review_time = None

        return True, '调整成功'

    def _recalculate_salary(self, emp_id: str):
        record = self.records.get(emp_id)
        if not record:
            return
        s = record.salary
        s.gross_salary = round(
            s.base_salary + s.performance_bonus + s.allowance, 2
        )
        s.net_salary = round(
            s.gross_salary - s.social_insurance - s.housing_fund
            - s.personal_tax - s.other_deduction, 2
        )

    def mark_rule_checked(self, emp_id: str, all_ok: bool = False) -> Tuple[bool, str]:
        record = self.records.get(emp_id)
        if not record:
            return False, '员工不存在'
        if record.is_locked:
            return False, f'员工 {record.name} 已锁定'
        record.review_steps.rule_checked = True
        record.review_steps.rule_check_time = datetime.now()
        unresolved = [i for i in record.issues if not i.resolved]
        if not unresolved:
            for issue in record.issues:
                issue.resolved = True
                if not issue.resolve_time:
                    issue.resolve_time = datetime.now()
                    issue.resolve_note = '规则检查通过，自动标记'
        self._log_operation(
            OperationType.RULE_CHECKED, emp_id, record.name,
            '规则检查完成，无未解决问题' if all_ok else '规则检查完成（仍有未解决问题需关注）'
        )
        if record.status == SalaryStatus.PENDING:
            record.status = SalaryStatus.CHECKING
        self.data_changed = True
        return True, '已标记规则检查完成'

    def mark_diff_checked(self, emp_id: str) -> Tuple[bool, str]:
        record = self.records.get(emp_id)
        if not record:
            return False, '员工不存在'
        if record.is_locked:
            return False, f'员工 {record.name} 已锁定'
        record.review_steps.diff_checked = True
        record.review_steps.diff_check_time = datetime.now()
        self._log_operation(
            OperationType.DIFF_CHECKED, emp_id, record.name,
            '差异核对完成，已确认本月与上月差异'
        )
        self.data_changed = True
        return True, '已标记差异核对完成'

    def mark_adjustment_reviewed(self, emp_id: str) -> Tuple[bool, str]:
        record = self.records.get(emp_id)
        if not record:
            return False, '员工不存在'
        if record.is_locked:
            return False, f'员工 {record.name} 已锁定'
        record.review_steps.adjustment_reviewed = True
        record.review_steps.adjustment_review_time = datetime.now()
        self._log_operation(
            OperationType.ADJUSTMENT_REVIEWED, emp_id, record.name,
            '调整复核完成，已确认所有调整原因合理'
        )
        self.data_changed = True
        return True, '已标记调整复核完成'

    def mark_issue_resolved(self, emp_id: str, issue_id: str, note: str = '') -> Tuple[bool, str]:
        record = self.records.get(emp_id)
        if not record:
            return False, '员工不存在'
        if record.is_locked:
            return False, f'员工 {record.name} 已锁定'
        issue = None
        for i in record.issues:
            if i.issue_id == issue_id:
                issue = i
                break
        if not issue:
            return False, '问题不存在'
        if issue.resolved:
            return False, '该问题已经标记为已解决'
        issue.resolved = True
        issue.resolve_time = datetime.now()
        issue.resolve_note = note or '手动标记已解决'
        self._log_operation(
            OperationType.ISSUE_RESOLVED, emp_id, record.name,
            f'问题"{issue.message}"已标记解决：{issue.resolve_note}'
        )
        self.data_changed = True
        return True, '已标记问题解决'

    def batch_mark_rule_checked(self) -> Tuple[int, int, List[str]]:
        success = 0
        failed = 0
        errors = []
        for record in self.records.values():
            if record.is_locked:
                continue
            ok, msg = self.mark_rule_checked(record.emp_id, all_ok=not record.has_unresolved_issues())
            if ok:
                success += 1
            else:
                failed += 1
                errors.append(msg)
        return success, failed, errors

    def batch_mark_diff_checked(self) -> Tuple[int, int, List[str]]:
        success = 0
        failed = 0
        errors = []
        for record in self.records.values():
            if record.is_locked:
                continue
            ok, msg = self.mark_diff_checked(record.emp_id)
            if ok:
                success += 1
            else:
                failed += 1
                errors.append(msg)
        return success, failed, errors

    def lock_record(self, emp_id: str, check_review: bool = True) -> Tuple[bool, str]:
        record = self.records.get(emp_id)
        if not record:
            return False, '员工不存在'
        if record.is_locked:
            return False, f'员工 {record.name} 已经是锁定状态'
        if check_review:
            unfinished = record.get_unfinished_review_steps()
            if unfinished:
                steps = '、'.join(unfinished)
                return False, f'员工 {record.name} 还有复核步骤未完成：{steps}。请完成所有复核后再锁定。'
            if record.has_unresolved_issues():
                return False, f'员工 {record.name} 还有未解决的问题，请先处理所有问题。'
        record.is_locked = True
        record.status = SalaryStatus.LOCKED
        record.confirm_time = datetime.now()
        self._log_operation(
            OperationType.LOCK, emp_id, record.name,
            '已锁定，正式确认发薪数据，不再允许修改'
        )
        self.data_changed = True
        return True, '锁定成功'

    def unlock_record(self, emp_id: str, reason: str = '') -> Tuple[bool, str]:
        record = self.records.get(emp_id)
        if not record:
            return False, '员工不存在'
        if not record.is_locked:
            return False, f'员工 {record.name} 未处于锁定状态'
        record.is_locked = False
        record.status = SalaryStatus.CHECKING
        record.unlock_time = datetime.now()
        detail = '已取消锁定，允许修改数据'
        if reason:
            detail += f'，原因：{reason}'
        self._log_operation(
            OperationType.UNLOCK, emp_id, record.name, detail
        )
        self.data_changed = True
        return True, '取消锁定成功'

    def get_unfinished_count(self) -> int:
        return sum(1 for r in self.records.values() if not r.is_locked)

    def get_confirmed_count(self) -> int:
        return sum(1 for r in self.records.values() if r.is_locked)

    def get_confirmed_records(self) -> List[SalaryRecord]:
        return [r for r in self.records.values() if r.is_locked]

    def get_unconfirmed_records(self) -> List[SalaryRecord]:
        return [r for r in self.records.values() if not r.is_locked]

    def get_records_with_unfinished_review(self) -> List[SalaryRecord]:
        return [r for r in self.records.values() if not r.is_locked and not r.is_review_complete()]

    def get_records_by_department(self, dept: str) -> List[SalaryRecord]:
        if not dept or dept == '全部':
            return self.get_all_records()
        return [r for r in self.records.values() if r.department == dept]

    def get_unfinished_review_summary(self) -> Dict:
        total = len(self.records)
        locked = self.get_confirmed_count()
        unlocked = total - locked
        need_rule = sum(1 for r in self.records.values() if not r.is_locked and not r.review_steps.rule_checked)
        need_diff = sum(1 for r in self.records.values() if not r.is_locked and not r.review_steps.diff_checked)
        need_adj = sum(1 for r in self.records.values() if not r.is_locked and not r.review_steps.adjustment_reviewed)
        has_issues = sum(1 for r in self.records.values() if not r.is_locked and r.has_unresolved_issues())
        return {
            'total': total,
            'locked': locked,
            'unlocked': unlocked,
            'need_rule_check': need_rule,
            'need_diff_check': need_diff,
            'need_adjustment_review': need_adj,
            'has_unresolved_issues': has_issues,
        }

    def add_import_batch(self, batch: ImportBatch):
        self.import_batches.append(batch)
        op_type_map = {
            ImportFileType.SALARY: OperationType.SALARY_IMPORTED,
            ImportFileType.ATTENDANCE: OperationType.ATTENDANCE_IMPORTED,
            ImportFileType.LAST_MONTH: OperationType.LASTMONTH_IMPORTED,
        }
        op_type = op_type_map.get(batch.file_type, OperationType.SALARY_IMPORTED)
        detail = (
            f'{batch.file_type.value}导入: 共{batch.total_count}条, '
            f'更新{batch.updated_count}条, 新增{batch.new_count}条, '
            f'跳过锁定{batch.skipped_locked_count}条'
        )
        self._log_operation(op_type, 'BATCH', '批量', detail)
        self.data_changed = True

    def get_import_batches(self) -> List[ImportBatch]:
        return sorted(self.import_batches, key=lambda b: b.import_time, reverse=True)

    def get_import_batches_by_type(self, file_type: ImportFileType) -> List[ImportBatch]:
        return [b for b in self.import_batches if b.file_type == file_type]

    def set_ui_state(self, key: str, value: Any):
        self.ui_state[key] = value

    def get_ui_state(self, key: str, default: Any = None) -> Any:
        return self.ui_state.get(key, default)

    def clear_all(self):
        self.records.clear()
        self.operation_logs.clear()
        self.employees.clear()
        self.last_month_data.clear()
        self.import_batches.clear()
        self.import_status = {
            'salary': False, 'attendance': False, 'last_month': False
        }
        self.current_month = ''
        self.current_project_path = None
        self.project_meta = None
        self.data_changed = False
        self.ui_state = {
            'current_tab': 0,
            'rule_filter': 'all',
            'diff_department': '全部',
            'diff_only_diff': False,
            'diff_only_issue': False,
            'diff_only_unlocked': False,
            'adj_filter_type': 'all',
            'adj_filter_emp': 'all',
            'confirm_department': '全部',
        }

    def save_project(self, file_path: str, project_name: str = '', note: str = '') -> Tuple[bool, str]:
        try:
            meta = ProjectMeta(
                project_name=project_name or os.path.splitext(os.path.basename(file_path))[0],
                created_time=self.project_meta.created_time if self.project_meta else datetime.now(),
                last_saved_time=datetime.now(),
                current_month=self.current_month,
                operator=self.operator,
                total_employees=len(self.records),
                locked_count=self.get_confirmed_count(),
                adjustment_count=len([l for l in self.operation_logs if l.operation_type == OperationType.ADJUSTMENT]),
                note=note,
            )
            data = {
                'version': '2.1',
                'meta': meta.to_dict(),
                'operator': self.operator,
                'current_month': self.current_month,
                'import_status': self.import_status,
                'rates': {
                    'social_insurance': self.social_insurance_rate,
                    'housing_fund': self.housing_fund_rate,
                    'tax_threshold': self.tax_threshold,
                    'fluctuation': self.fluctuation_threshold,
                },
                'records': [_record_to_dict(r) for r in self.records.values()],
                'operation_logs': [l.to_dict() for l in self.operation_logs],
                'employees': {eid: e.__dict__ for eid, e in self.employees.items()},
                'import_batches': [b.to_dict() for b in self.import_batches],
                'ui_state': self.ui_state,
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.current_project_path = file_path
            self.project_meta = meta
            self.data_changed = False
            return True, f'项目已保存到: {file_path}'
        except Exception as e:
            return False, f'保存失败: {str(e)}'

    def load_project(self, file_path: str) -> Tuple[bool, str]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            version = data.get('version', '1.0')
            meta = ProjectMeta.from_dict(data.get('meta', {}))

            self.clear_all()

            self.operator = data.get('operator', '薪酬专员')
            self.current_month = data.get('current_month', '')
            self.import_status = data.get('import_status', {
                'salary': False, 'attendance': False, 'last_month': False
            })
            rates = data.get('rates', {})
            self.social_insurance_rate = rates.get('social_insurance', 0.105)
            self.housing_fund_rate = rates.get('housing_fund', 0.12)
            self.tax_threshold = rates.get('tax_threshold', 5000)
            self.fluctuation_threshold = rates.get('fluctuation', 0.20)

            for r_dict in data.get('records', []):
                record = _record_from_dict(r_dict)
                self.records[record.emp_id] = record

            for l_dict in data.get('operation_logs', []):
                self.operation_logs.append(OperationLog.from_dict(l_dict))

            for eid, e_dict in data.get('employees', {}).items():
                self.employees[eid] = Employee(**e_dict)

            for b_dict in data.get('import_batches', []):
                self.import_batches.append(ImportBatch.from_dict(b_dict))

            if 'ui_state' in data:
                self.ui_state.update(data['ui_state'])

            for r in self.records.values():
                if r.last_month_salary:
                    self.last_month_data[r.emp_id] = r.last_month_salary

            self.current_project_path = file_path
            self.project_meta = meta
            self.data_changed = False
            return True, (
                f'成功加载项目，共 {len(self.records)} 名员工，'
                f'{len(self.operation_logs)} 条操作记录，'
                f'{len(self.import_batches)} 次导入批次'
            )
        except Exception as e:
            return False, f'加载失败: {str(e)}'
