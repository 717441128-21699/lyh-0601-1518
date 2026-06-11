from typing import List, Dict, Tuple

from models.data_store import DataStore
from models.data_models import SalaryRecord, SalaryStatus


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

    def check_all(self) -> Dict[str, List[Dict]]:
        issues_by_emp: Dict[str, List[Dict]] = {}

        self._check_missing_attendance(issues_by_emp)
        self._check_social_insurance(issues_by_emp)
        self._check_housing_fund(issues_by_emp)
        self._check_personal_tax(issues_by_emp)
        self._check_gross_salary_calc(issues_by_emp)
        self._check_net_salary_calc(issues_by_emp)
        self._check_large_fluctuation(issues_by_emp)
        self._check_negative_salary(issues_by_emp)

        for emp_id, issues in issues_by_emp.items():
            record = self.store.get_record(emp_id)
            if record:
                record.issues = [i['message'] for i in issues]
                if issues and not record.is_locked:
                    record.status = SalaryStatus.CHECKING

        return issues_by_emp

    def _add_issue(self, issues_by_emp: Dict, emp_id: str, level: str,
                   category: str, message: str):
        if emp_id not in issues_by_emp:
            issues_by_emp[emp_id] = []
        issues_by_emp[emp_id].append({
            'level': level,
            'category': category,
            'message': message,
        })

    def _check_missing_attendance(self, issues_by_emp: Dict):
        for record in self.store.get_all_records():
            att = record.attendance
            if att.work_days == 0 and att.overtime_hours == 0 \
                    and att.leave_days == 0 and att.sick_days == 0:
                self._add_issue(
                    issues_by_emp, record.emp_id, 'warning', '考勤',
                    '该员工无考勤数据，请确认是否为新入职或特殊情况'
                )

    def _check_social_insurance(self, issues_by_emp: Dict):
        rate = self.store.social_insurance_rate
        for record in self.store.get_all_records():
            s = record.salary
            if s.gross_salary <= 0:
                continue
            expected = round(s.base_salary * rate, 2)
            actual = s.social_insurance
            if expected > 0 and abs(expected - actual) / expected > 0.1:
                self._add_issue(
                    issues_by_emp, record.emp_id, 'warning', '社保',
                    f'社保金额异常：预计{expected:.2f}元，实际{actual:.2f}元'
                )

    def _check_housing_fund(self, issues_by_emp: Dict):
        rate = self.store.housing_fund_rate
        for record in self.store.get_all_records():
            s = record.salary
            if s.gross_salary <= 0:
                continue
            expected = round(s.base_salary * rate, 2)
            actual = s.housing_fund
            if expected > 0 and abs(expected - actual) / expected > 0.1:
                self._add_issue(
                    issues_by_emp, record.emp_id, 'warning', '公积金',
                    f'公积金金额异常：预计{expected:.2f}元，实际{actual:.2f}元'
                )

    def _check_personal_tax(self, issues_by_emp: Dict):
        threshold = self.store.tax_threshold
        for record in self.store.get_all_records():
            s = record.salary
            taxable = s.gross_salary - s.social_insurance - s.housing_fund - threshold
            if taxable <= 0:
                if s.personal_tax > 0:
                    self._add_issue(
                        issues_by_emp, record.emp_id, 'error', '个税',
                        f'应纳税所得额为{taxable:.2f}元，个税应为0，实际{s.personal_tax:.2f}元'
                    )
                continue
            if s.personal_tax <= 0:
                self._add_issue(
                    issues_by_emp, record.emp_id, 'warning', '个税',
                    f'应纳税所得额{taxable:.2f}元，个税不应为0'
                )

    def _check_gross_salary_calc(self, issues_by_emp: Dict):
        for record in self.store.get_all_records():
            s = record.salary
            expected = round(s.base_salary + s.performance_bonus + s.allowance, 2)
            if abs(expected - s.gross_salary) > 0.02:
                self._add_issue(
                    issues_by_emp, record.emp_id, 'error', '计算',
                    f'应发工资计算异常：合计{expected:.2f}元，实际{s.gross_salary:.2f}元'
                )

    def _check_net_salary_calc(self, issues_by_emp: Dict):
        for record in self.store.get_all_records():
            s = record.salary
            expected = round(
                s.gross_salary - s.social_insurance - s.housing_fund
                - s.personal_tax - s.other_deduction, 2
            )
            if abs(expected - s.net_salary) > 0.02:
                self._add_issue(
                    issues_by_emp, record.emp_id, 'error', '计算',
                    f'实发工资计算异常：应为{expected:.2f}元，实际{s.net_salary:.2f}元'
                )

    def _check_large_fluctuation(self, issues_by_emp: Dict):
        threshold = self.store.fluctuation_threshold
        for record in self.store.get_all_records():
            if not record.last_month_salary:
                continue
            last_net = record.last_month_salary.net_salary
            curr_net = record.salary.net_salary
            if last_net <= 0:
                continue
            diff = curr_net - last_net
            rate = abs(diff) / last_net
            if rate > threshold:
                direction = '上涨' if diff > 0 else '下降'
                self._add_issue(
                    issues_by_emp, record.emp_id, 'warning', '波动',
                    f'实发工资较上月{direction}{rate*100:.1f}%（{diff:+.2f}元），超过{threshold*100:.0f}%阈值'
                )

    def _check_negative_salary(self, issues_by_emp: Dict):
        for record in self.store.get_all_records():
            s = record.salary
            if s.net_salary < 0:
                self._add_issue(
                    issues_by_emp, record.emp_id, 'error', '金额',
                    f'实发工资为负数: {s.net_salary:.2f}元'
                )
            if s.base_salary < 0:
                self._add_issue(
                    issues_by_emp, record.emp_id, 'error', '金额',
                    f'基本工资为负数: {s.base_salary:.2f}元'
                )

    def get_records_with_issues(self) -> List[Tuple[SalaryRecord, List[Dict]]]:
        issues_by_emp = self.check_all()
        result = []
        for record in self.store.get_all_records():
            issues = issues_by_emp.get(record.emp_id, [])
            if issues:
                result.append((record, issues))
        return sorted(result, key=lambda x: -len(x[1]))

    def get_missing_employees(self) -> List[SalaryRecord]:
        return [r for r in self.store.get_all_records() if not r.salary or r.salary.gross_salary <= 0]
