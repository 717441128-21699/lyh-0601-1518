import os
import pandas as pd
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import uuid

from models.data_store import DataStore
from models.data_models import (
    Employee, SalaryRecord, SalaryData,
    AttendanceData, SalaryStatus, OperationType,
    IssueItem, ImportBatch, ImportFileType
)


SALARY_COLUMN_MAP = {
    '员工编号': 'emp_id', '工号': 'emp_id', 'EmpID': 'emp_id', 'ID': 'emp_id',
    '姓名': 'name', 'Name': 'name',
    '部门': 'department', 'Department': 'department',
    '职位': 'position', '岗位': 'position', 'Position': 'position',
    '基本工资': 'base_salary', '底薪': 'base_salary',
    '绩效奖金': 'performance_bonus', '绩效': 'performance_bonus',
    '津贴': 'allowance', '补贴': 'allowance',
    '社保': 'social_insurance', '社会保险': 'social_insurance',
    '公积金': 'housing_fund', '住房公积金': 'housing_fund',
    '个税': 'personal_tax', '个人所得税': 'personal_tax',
    '其他扣款': 'other_deduction',
    '应发工资': 'gross_salary', '应发合计': 'gross_salary',
    '实发工资': 'net_salary', '实发合计': 'net_salary',
}

ATTENDANCE_COLUMN_MAP = {
    '员工编号': 'emp_id', '工号': 'emp_id',
    '出勤天数': 'work_days', '工作日': 'work_days',
    '加班小时': 'overtime_hours', '加班时长': 'overtime_hours',
    '请假天数': 'leave_days', '事假': 'leave_days',
    '病假天数': 'sick_days', '病假': 'sick_days',
    '迟到次数': 'late_times', '迟到': 'late_times',
    '旷工天数': 'absenteeism_days', '旷工': 'absenteeism_days',
}


def _map_columns(df_columns: List[str], column_map: Dict[str, str]) -> Dict[str, str]:
    mapping = {}
    for col in df_columns:
        col_clean = str(col).strip()
        if col_clean in column_map:
            mapping[col] = column_map[col_clean]
    return mapping


def _safe_float(val) -> float:
    try:
        if pd.isna(val):
            return 0.0
        return round(float(val), 2)
    except (ValueError, TypeError):
        return 0.0


def _safe_int(val) -> int:
    try:
        if pd.isna(val):
            return 0
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def _safe_str(val) -> str:
    try:
        if pd.isna(val):
            return ''
        return str(val).strip()
    except (ValueError, TypeError):
        return ''


def import_salary_excel(file_path: str, force: bool = False) -> Tuple[int, int, List[str], List[str]]:
    if not os.path.exists(file_path):
        return 0, 0, ['文件不存在'], []

    store = DataStore()
    errors: List[str] = []
    warnings: List[str] = []
    imported = 0
    skipped_locked = 0
    new_count = 0

    locked_names: List[str] = []
    updated_ids: List[str] = []
    new_ids: List[str] = []
    skipped_ids: List[str] = []

    try:
        df = pd.read_excel(file_path, dtype=str)
    except Exception as e:
        return 0, 0, [f'读取Excel失败: {str(e)}'], []

    if df.empty:
        return 0, 0, ['Excel文件为空'], []

    col_mapping = _map_columns(df.columns.tolist(), SALARY_COLUMN_MAP)

    if 'emp_id' not in col_mapping.values():
        return 0, 0, ['未找到"员工编号"或"工号"列'], []

    reverse_map = {v: k for k, v in col_mapping.items()}

    for idx, row in df.iterrows():
        emp_id = _safe_str(row.get(reverse_map.get('emp_id', ''), ''))
        if not emp_id:
            continue

        name = _safe_str(row.get(reverse_map.get('name', ''), ''))
        department = _safe_str(row.get(reverse_map.get('department', ''), ''))
        position = _safe_str(row.get(reverse_map.get('position', ''), ''))

        existing = store.get_record(emp_id)
        if existing and existing.is_locked and not force:
            skipped_locked += 1
            locked_names.append(f'{existing.name}({emp_id})')
            skipped_ids.append(emp_id)
            continue

        salary = SalaryData(
            emp_id=emp_id,
            base_salary=_safe_float(row.get(reverse_map.get('base_salary', ''), 0)),
            performance_bonus=_safe_float(row.get(reverse_map.get('performance_bonus', ''), 0)),
            allowance=_safe_float(row.get(reverse_map.get('allowance', ''), 0)),
            social_insurance=_safe_float(row.get(reverse_map.get('social_insurance', ''), 0)),
            housing_fund=_safe_float(row.get(reverse_map.get('housing_fund', ''), 0)),
            personal_tax=_safe_float(row.get(reverse_map.get('personal_tax', ''), 0)),
            other_deduction=_safe_float(row.get(reverse_map.get('other_deduction', ''), 0)),
            gross_salary=_safe_float(row.get(reverse_map.get('gross_salary', ''), 0)),
            net_salary=_safe_float(row.get(reverse_map.get('net_salary', ''), 0)),
        )

        if salary.gross_salary <= 0.01:
            salary.gross_salary = round(
                salary.base_salary + salary.performance_bonus + salary.allowance, 2
            )
        if salary.net_salary <= 0.01:
            salary.net_salary = round(
                salary.gross_salary - salary.social_insurance
                - salary.housing_fund - salary.personal_tax
                - salary.other_deduction, 2
            )

        emp = Employee(emp_id=emp_id, name=name, department=department, position=position)
        store.add_employee(emp)

        if existing:
            old_salary = existing.salary
            existing.name = name or existing.name
            existing.department = department or existing.department
            existing.position = position or existing.position
            existing.salary = salary
            existing.issues = []
            existing.issue_messages = []
            existing.review_steps.rule_checked = False
            existing.review_steps.diff_checked = False
            existing.status = SalaryStatus.PENDING
            existing.confirm_time = None
            store._log_operation(
                OperationType.SALARY_IMPORTED, emp_id, existing.name,
                f'重新导入工资数据，原应发{old_salary.gross_salary:.2f}→新应发{salary.gross_salary:.2f}'
            )
            updated_ids.append(emp_id)
        else:
            record = SalaryRecord(
                emp_id=emp_id, name=name, department=department,
                position=position, salary=salary, status=SalaryStatus.PENDING
            )
            store.add_or_update_record(record, check_lock=False)
            store._log_operation(
                OperationType.SALARY_IMPORTED, emp_id, name,
                '首次导入工资数据'
            )
            new_ids.append(emp_id)
            new_count += 1

        imported += 1

    store.import_status['salary'] = True

    if skipped_locked > 0:
        show_names = ', '.join(locked_names[:5])
        if len(locked_names) > 5:
            show_names += f' 等{len(locked_names)}人'
        warnings.append(f'已跳过 {skipped_locked} 名已锁定人员（{show_names}），如需更新请先取消锁定')

    batch = ImportBatch(
        batch_id=str(uuid.uuid4())[:8],
        file_type=ImportFileType.SALARY,
        file_name=os.path.basename(file_path),
        import_time=datetime.now(),
        operator=store.operator,
        total_count=imported + skipped_locked,
        updated_count=len(updated_ids),
        skipped_locked_count=skipped_locked,
        new_count=new_count,
        updated_employees=updated_ids,
        skipped_employees=skipped_ids,
        new_employees=new_ids,
    )
    store.add_import_batch(batch)

    return imported, skipped_locked, errors, warnings


def import_attendance_excel(file_path: str) -> Tuple[int, int, List[str], List[str]]:
    if not os.path.exists(file_path):
        return 0, 0, ['文件不存在'], []

    store = DataStore()
    errors: List[str] = []
    warnings: List[str] = []
    matched = 0
    skipped_locked = 0
    mismatched: List[str] = []
    updated_ids: List[str] = []
    skipped_ids: List[str] = []
    skipped_names: List[str] = []

    try:
        df = pd.read_excel(file_path, dtype=str)
    except Exception as e:
        return 0, 0, [f'读取Excel失败: {str(e)}'], []

    if df.empty:
        return 0, 0, ['Excel文件为空'], []

    col_mapping = _map_columns(df.columns.tolist(), ATTENDANCE_COLUMN_MAP)

    if 'emp_id' not in col_mapping.values():
        return 0, 0, ['未找到"员工编号"或"工号"列'], []

    reverse_map = {v: k for k, v in col_mapping.items()}

    for idx, row in df.iterrows():
        emp_id = _safe_str(row.get(reverse_map.get('emp_id', ''), ''))
        if not emp_id:
            continue

        attendance = AttendanceData(
            emp_id=emp_id,
            work_days=_safe_int(row.get(reverse_map.get('work_days', ''), 0)),
            overtime_hours=_safe_float(row.get(reverse_map.get('overtime_hours', ''), 0)),
            leave_days=_safe_int(row.get(reverse_map.get('leave_days', ''), 0)),
            sick_days=_safe_int(row.get(reverse_map.get('sick_days', ''), 0)),
            late_times=_safe_int(row.get(reverse_map.get('late_times', ''), 0)),
            absenteeism_days=_safe_int(row.get(reverse_map.get('absenteeism_days', ''), 0)),
        )

        record = store.get_record(emp_id)
        if record:
            if record.is_locked:
                skipped_locked += 1
                skipped_ids.append(emp_id)
                skipped_names.append(f'{record.name}({emp_id})')
                continue
            record.attendance = attendance
            record.review_steps.rule_checked = False
            matched += 1
            updated_ids.append(emp_id)
            store._log_operation(
                OperationType.ATTENDANCE_IMPORTED, emp_id, record.name,
                '更新考勤数据'
            )
        else:
            mismatched.append(emp_id)

    store.import_status['attendance'] = True

    if skipped_locked > 0:
        show_names = ', '.join(skipped_names[:5])
        if len(skipped_names) > 5:
            show_names += f' 等{len(skipped_names)}人'
        warnings.append(f'已跳过 {skipped_locked} 名已锁定人员的考勤数据更新（{show_names}）')

    if mismatched:
        errors.append(f'未匹配到工资表的员工编号: {", ".join(mismatched[:10])}')
        if len(mismatched) > 10:
            errors.append(f'... 还有 {len(mismatched) - 10} 人未匹配')

    batch = ImportBatch(
        batch_id=str(uuid.uuid4())[:8],
        file_type=ImportFileType.ATTENDANCE,
        file_name=os.path.basename(file_path),
        import_time=datetime.now(),
        operator=store.operator,
        total_count=matched + skipped_locked + len(mismatched),
        updated_count=matched,
        skipped_locked_count=skipped_locked,
        new_count=0,
        updated_employees=updated_ids,
        skipped_employees=skipped_ids,
        new_employees=[],
    )
    store.add_import_batch(batch)

    return matched, len(mismatched), errors, warnings


def import_last_month_salary(file_path: str) -> Tuple[int, int, List[str], List[str]]:
    if not os.path.exists(file_path):
        return 0, 0, ['文件不存在'], []

    store = DataStore()
    errors: List[str] = []
    warnings: List[str] = []
    matched = 0
    skipped_locked = 0
    mismatched: List[str] = []
    updated_ids: List[str] = []
    skipped_ids: List[str] = []
    skipped_names: List[str] = []

    try:
        df = pd.read_excel(file_path, dtype=str)
    except Exception as e:
        return 0, 0, [f'读取Excel失败: {str(e)}'], []

    if df.empty:
        return 0, 0, ['Excel文件为空'], []

    col_mapping = _map_columns(df.columns.tolist(), SALARY_COLUMN_MAP)

    if 'emp_id' not in col_mapping.values():
        return 0, 0, ['未找到"员工编号"或"工号"列'], []

    reverse_map = {v: k for k, v in col_mapping.items()}

    for idx, row in df.iterrows():
        emp_id = _safe_str(row.get(reverse_map.get('emp_id', ''), ''))
        if not emp_id:
            continue

        last_salary = SalaryData(
            emp_id=emp_id,
            base_salary=_safe_float(row.get(reverse_map.get('base_salary', ''), 0)),
            performance_bonus=_safe_float(row.get(reverse_map.get('performance_bonus', ''), 0)),
            allowance=_safe_float(row.get(reverse_map.get('allowance', ''), 0)),
            social_insurance=_safe_float(row.get(reverse_map.get('social_insurance', ''), 0)),
            housing_fund=_safe_float(row.get(reverse_map.get('housing_fund', ''), 0)),
            personal_tax=_safe_float(row.get(reverse_map.get('personal_tax', ''), 0)),
            other_deduction=_safe_float(row.get(reverse_map.get('other_deduction', ''), 0)),
            gross_salary=_safe_float(row.get(reverse_map.get('gross_salary', ''), 0)),
            net_salary=_safe_float(row.get(reverse_map.get('net_salary', ''), 0)),
        )

        if last_salary.gross_salary <= 0.01:
            last_salary.gross_salary = round(
                last_salary.base_salary + last_salary.performance_bonus + last_salary.allowance, 2
            )
        if last_salary.net_salary <= 0.01:
            last_salary.net_salary = round(
                last_salary.gross_salary - last_salary.social_insurance
                - last_salary.housing_fund - last_salary.personal_tax
                - last_salary.other_deduction, 2
            )

        record = store.get_record(emp_id)
        if record:
            if record.is_locked:
                skipped_locked += 1
                skipped_ids.append(emp_id)
                skipped_names.append(f'{record.name}({emp_id})')
                continue
            record.last_month_salary = last_salary
            record.review_steps.diff_checked = False
            matched += 1
            updated_ids.append(emp_id)
            store._log_operation(
                OperationType.LASTMONTH_IMPORTED, emp_id, record.name,
                f'更新上月工资数据，应发{last_salary.gross_salary:.2f}'
            )
        else:
            mismatched.append(emp_id)

    store.last_month_data = {r.emp_id: r.last_month_salary
                             for r in store.get_all_records() if r.last_month_salary}
    store.import_status['last_month'] = True

    if skipped_locked > 0:
        show_names = ', '.join(skipped_names[:5])
        if len(skipped_names) > 5:
            show_names += f' 等{len(skipped_names)}人'
        warnings.append(f'已跳过 {skipped_locked} 名已锁定人员的上月工资更新（{show_names}）')

    if mismatched:
        errors.append(f'上月工资表中未在本月出现的员工: {", ".join(mismatched[:10])}')

    batch = ImportBatch(
        batch_id=str(uuid.uuid4())[:8],
        file_type=ImportFileType.LAST_MONTH,
        file_name=os.path.basename(file_path),
        import_time=datetime.now(),
        operator=store.operator,
        total_count=matched + skipped_locked + len(mismatched),
        updated_count=matched,
        skipped_locked_count=skipped_locked,
        new_count=0,
        updated_employees=updated_ids,
        skipped_employees=skipped_ids,
        new_employees=[],
    )
    store.add_import_batch(batch)

    return matched, len(mismatched), errors, warnings


def export_final_salary(file_path: str) -> Tuple[bool, str]:
    store = DataStore()
    records = store.get_all_records()

    if not records:
        return False, '没有数据可导出'

    data = []
    for r in records:
        s = r.salary
        steps = r.review_steps
        data.append({
            '员工编号': r.emp_id,
            '姓名': r.name,
            '部门': r.department,
            '职位': r.position,
            '基本工资': s.base_salary,
            '绩效奖金': s.performance_bonus,
            '津贴': s.allowance,
            '应发工资': s.gross_salary,
            '社保': s.social_insurance,
            '公积金': s.housing_fund,
            '个税': s.personal_tax,
            '其他扣款': s.other_deduction,
            '实发工资': s.net_salary,
            '规则检查': '已完成' if steps.rule_checked else '未完成',
            '差异核对': '已完成' if steps.diff_checked else '未完成',
            '调整复核': '已完成' if steps.adjustment_reviewed else '未完成',
            '状态': r.status.value,
            '是否锁定': '是' if r.is_locked else '否',
            '确认时间': r.confirm_time.strftime('%Y-%m-%d %H:%M:%S') if r.confirm_time else '',
        })

    df = pd.DataFrame(data)
    try:
        df.to_excel(file_path, index=False, sheet_name='最终发薪表')
        return True, f'成功导出 {len(records)} 条记录'
    except Exception as e:
        return False, f'导出失败: {str(e)}'


def export_review_list(file_path: str) -> Tuple[bool, str]:
    store = DataStore()
    records = store.get_all_records()

    if not records:
        return False, '没有数据可导出'

    data = []
    for r in records:
        unresolved = [i.message for i in r.issues if not i.resolved]
        issues = '; '.join(unresolved) if unresolved else '无'
        adj_count = len([a for a in r.adjustments if a.operation_type == OperationType.ADJUSTMENT])
        steps = r.get_unfinished_review_steps()
        step_status = '全部完成' if not steps else '未完成: ' + '、'.join(steps)
        last = r.last_month_salary
        diff = round(r.salary.net_salary - last.net_salary, 2) if last else None

        data.append({
            '员工编号': r.emp_id,
            '姓名': r.name,
            '部门': r.department,
            '实发工资': r.salary.net_salary,
            '上月实发': last.net_salary if last else '',
            '波动额': diff if diff is not None else '',
            '未解决问题数': len(unresolved),
            '问题描述': issues,
            '调整次数': adj_count,
            '复核状态': step_status,
            '状态': r.status.value,
            '是否锁定': '是' if r.is_locked else '否',
        })

    df = pd.DataFrame(data)
    try:
        df.to_excel(file_path, index=False, sheet_name='复核清单')
        return True, f'成功导出复核清单'
    except Exception as e:
        return False, f'导出失败: {str(e)}'


def export_adjustments(file_path: str) -> Tuple[bool, str]:
    store = DataStore()
    from models.data_models import OperationType
    adjustments = [l for l in store.get_operation_logs()
                   if l.operation_type in (OperationType.ADJUSTMENT, OperationType.UNLOCK, OperationType.LOCK)]

    if not adjustments:
        return False, '没有操作记录'

    data = []
    for a in adjustments:
        diff = round(a.new_value - a.old_value, 2) if a.operation_type == OperationType.ADJUSTMENT else None
        data.append({
            '操作类型': a.operation_type.value,
            '员工编号': a.emp_id,
            '姓名': a.name,
            '调整字段': a.field_name if a.field_name else '-',
            '原值': a.old_value if a.operation_type == OperationType.ADJUSTMENT else '-',
            '新值': a.new_value if a.operation_type == OperationType.ADJUSTMENT else '-',
            '差额': diff if diff is not None else '-',
            '操作详情': a.detail,
            '操作人': a.operator,
            '操作时间': a.operate_time.strftime('%Y-%m-%d %H:%M:%S'),
        })

    df = pd.DataFrame(data)
    try:
        df.to_excel(file_path, index=False, sheet_name='操作记录')
        return True, f'成功导出 {len(adjustments)} 条操作记录'
    except Exception as e:
        return False, f'导出失败: {str(e)}'
