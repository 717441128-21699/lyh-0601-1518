from typing import List, Dict, Tuple

from models.data_store import DataStore
from models.data_models import (
    SalaryRecord, SalaryStatus, IssueItem, OperationType
)


FIELD_NAMES_CN = {
    'base_salary': '基本工资',
    'performance_bonus': '绩效奖金',
    'allowance': '津贴',
    'social_insurance': '社保',
    'housing_fund': '公积金',
    'personal_tax': '个税',
    'other_deduction': '其他扣款',
    'gross_salary': '应发工资',
    'net_salary': '实发工资',
}


class RuleChecker:
    def __init__(self):
        self.store = DataStore()

    def check_all(self, refresh: bool = True) -> Dict[str, List[IssueItem]]:
        issues_by_emp: Dict[str, List[IssueItem]] = {}

        for record in self.store.get_all_records():
            if record.is_locked:
                continue
            emp_id = record.emp_id
            current_issues = []

            self._check_missing_attendance(current_issues, record)
            self._check_social_insurance(current_issues, record)
            self._check_housing_fund(current_issues, record)
            self._check_personal_tax(current_issues, record)
            self._check_gross_salary_calc(current_issues, record)
            self._check_net_salary_calc(current_issues, record)
            self._check_large_fluctuation(current_issues, record)
            self._check_negative_salary(current_issues, record)

            if refresh:
                resolved_notes = {}
                for old_issue in record.issues:
                    if old_issue.resolved:
                        resolved_notes[old_issue.message] = (
                            old_issue.resolve_time, old_issue.resolve_note
                        )

                for issue in current_issues:
                    if issue.message in resolved_notes:
                        rt, rn = resolved_notes[issue.message]
                        issue.resolved = True
                        issue.resolve_time = rt
                        issue.resolve_note = rn

                record.issues = current_issues
                record.issue_messages = [i.message for i in current_issues]

                if current_issues and not record.is_locked:
                    if record.status == SalaryStatus.PENDING:
                        record.status = SalaryStatus.CHECKING
                elif not current_issues and record.status == SalaryStatus.CHECKING:
                    pass

                unresolved = [i for i in current_issues if not i.resolved]
                if not unresolved and record.review_steps.rule_checked:
                    for issue in current_issues:
                        if not issue.resolved:
                            issue.resolved = True
                            issue.resolve_note = issue.resolve_note or '规则检查通过，无未解决问题'

            if current_issues:
                issues_by_emp[emp_id] = current_issues

        self.store.mark_data_changed()
        return issues_by_emp

    def _add_issue(self, issues: List, level: str, category: str, message: str):
        issues.append(IssueItem(
            level=level,
            category=category,
            message=message,
            resolved=False,
        ))

    def _check_missing_attendance(self, issues: List, record: SalaryRecord):
        att = record.attendance
        if att.work_days == 0 and att.overtime_hours == 0 \
                and att.leave_days == 0 and att.sick_days == 0:
            self._add_issue(
                issues, 'warning', '考勤',
                '该员工无考勤数据，请确认是否为新入职或特殊情况'
            )

    def _check_social_insurance(self, issues: List, record: SalaryRecord):
        rate = self.store.social_insurance_rate
        s = record.salary
        if s.gross_salary <= 0:
            return
        expected = round(s.base_salary * rate, 2)
        actual = s.social_insurance
        if expected > 0 and abs(expected - actual) / expected > 0.1:
            self._add_issue(
                issues, 'warning', '社保',
                f'社保金额异常：预计{expected:.2f}元，实际{actual:.2f}元'
            )

    def _check_housing_fund(self, issues: List, record: SalaryRecord):
        rate = self.store.housing_fund_rate
        s = record.salary
        if s.gross_salary <= 0:
            return
        expected = round(s.base_salary * rate, 2)
        actual = s.housing_fund
        if expected > 0 and abs(expected - actual) / expected > 0.1:
            self._add_issue(
                issues, 'warning', '公积金',
                f'公积金金额异常：预计{expected:.2f}元，实际{actual:.2f}元'
            )

    def _check_personal_tax(self, issues: List, record: SalaryRecord):
        threshold = self.store.tax_threshold
        s = record.salary
        taxable = s.gross_salary - s.social_insurance - s.housing_fund - threshold
        if taxable <= 0:
            if s.personal_tax > 0:
                self._add_issue(
                    issues, 'error', '个税',
                    f'应纳税所得额为{taxable:.2f}元，个税应为0，实际{s.personal_tax:.2f}元'
                )
            return
        if s.personal_tax <= 0:
            self._add_issue(
                issues, 'warning', '个税',
                f'应纳税所得额{taxable:.2f}元，个税不应为0'
            )

    def _check_gross_salary_calc(self, issues: List, record: SalaryRecord):
        s = record.salary
        expected = round(s.base_salary + s.performance_bonus + s.allowance, 2)
        if abs(expected - s.gross_salary) > 0.02:
            self._add_issue(
                issues, 'error', '计算',
                f'应发工资计算异常：合计{expected:.2f}元，实际{s.gross_salary:.2f}元'
            )

    def _check_net_salary_calc(self, issues: List, record: SalaryRecord):
        s = record.salary
        expected = round(
            s.gross_salary - s.social_insurance - s.housing_fund
            - s.personal_tax - s.other_deduction, 2
        )
        if abs(expected - s.net_salary) > 0.02:
            self._add_issue(
                issues, 'error', '计算',
                f'实发工资计算异常：应为{expected:.2f}元，实际{s.net_salary:.2f}元'
            )

    def _check_large_fluctuation(self, issues: List, record: SalaryRecord):
        threshold = self.store.fluctuation_threshold
        if not record.last_month_salary:
            return
        last_net = record.last_month_salary.net_salary
        curr_net = record.salary.net_salary
        if last_net <= 0:
            return
        diff = curr_net - last_net
        rate = abs(diff) / last_net
        if rate > threshold:
            direction = '上涨' if diff > 0 else '下降'
            self._add_issue(
                issues, 'warning', '波动',
                f'实发工资较上月{direction}{rate*100:.1f}%（{diff:+.2f}元），超过{threshold*100:.0f}%阈值'
            )

    def _check_negative_salary(self, issues: List, record: SalaryRecord):
        s = record.salary
        if s.net_salary < 0:
            self._add_issue(
                issues, 'error', '金额',
                f'实发工资为负数: {s.net_salary:.2f}元'
            )
        if s.base_salary < 0:
            self._add_issue(
                issues, 'error', '金额',
                f'基本工资为负数: {s.base_salary:.2f}元'
            )

    def get_records_with_issues(self) -> List[Tuple[SalaryRecord, List[IssueItem]]]:
        issues_by_emp = self.check_all(refresh=False)
        result = []
        for record in self.store.get_all_records():
            issues = issues_by_emp.get(record.emp_id, [])
            if issues:
                result.append((record, issues))
        return sorted(result, key=lambda x: -len([i for i in x[1] if not i.resolved]))

    def get_missing_employees(self) -> List[SalaryRecord]:
        return [r for r in self.store.get_all_records()
                if not r.salary or r.salary.gross_salary <= 0]

    def get_issue_summary(self) -> Dict:
        issues_by_emp = self.check_all(refresh=False)
        total_errors = 0
        total_warnings = 0
        for issues in issues_by_emp.values():
            for issue in issues:
                if issue.resolved:
                    continue
                if issue.level == 'error':
                    total_errors += 1
                elif issue.level == 'warning':
                    total_warnings += 1
        return {
            'employees_with_issues': len(issues_by_emp),
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'issues_by_emp': issues_by_emp,
        }
