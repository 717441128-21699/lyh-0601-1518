from typing import List, Dict, Optional
from datetime import datetime
from .data_models import (
    SalaryRecord, AdjustmentRecord, SalaryData,
    AttendanceData, Employee, SalaryStatus
)


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
        self.adjustments: List[AdjustmentRecord] = []
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

    def add_employee(self, emp: Employee):
        self.employees[emp.emp_id] = emp

    def add_or_update_record(self, record: SalaryRecord):
        self.records[record.emp_id] = record

    def get_record(self, emp_id: str) -> Optional[SalaryRecord]:
        return self.records.get(emp_id)

    def get_all_records(self) -> List[SalaryRecord]:
        return list(self.records.values())

    def get_departments(self) -> List[str]:
        depts = {r.department for r in self.records.values() if r.department}
        return sorted(list(depts))

    def add_adjustment(self, adj: AdjustmentRecord):
        self.adjustments.append(adj)

    def get_adjustments(self) -> List[AdjustmentRecord]:
        return self.adjustments

    def get_adjustments_by_emp(self, emp_id: str) -> List[AdjustmentRecord]:
        return [a for a in self.adjustments if a.emp_id == emp_id]

    def adjust_salary_field(self, emp_id: str, field_name: str,
                            new_value: float, reason: str) -> bool:
        record = self.records.get(emp_id)
        if not record or record.is_locked:
            return False
        salary = record.salary
        old_value = getattr(salary, field_name, None)
        if old_value is None:
            return False
        old_value = float(old_value)
        if abs(old_value - new_value) < 0.01:
            return False
        adj = AdjustmentRecord(
            emp_id=emp_id,
            name=record.name,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            operator=self.operator,
            adjust_time=datetime.now()
        )
        self.adjustments.append(adj)
        record.adjustments.append(adj)
        setattr(salary, field_name, new_value)
        self._recalculate_salary(emp_id)
        record.status = SalaryStatus.ADJUSTED
        return True

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

    def lock_record(self, emp_id: str) -> bool:
        record = self.records.get(emp_id)
        if record:
            record.is_locked = True
            record.status = SalaryStatus.LOCKED
            record.confirm_time = datetime.now()
            return True
        return False

    def unlock_record(self, emp_id: str) -> bool:
        record = self.records.get(emp_id)
        if record:
            record.is_locked = False
            record.status = SalaryStatus.CHECKING
            record.confirm_time = None
            return True
        return False

    def get_unfinished_count(self) -> int:
        return sum(1 for r in self.records.values() if not r.is_locked)

    def get_confirmed_count(self) -> int:
        return sum(1 for r in self.records.values() if r.is_locked)

    def get_confirmed_records(self) -> List[SalaryRecord]:
        return [r for r in self.records.values() if r.is_locked]

    def get_unconfirmed_records(self) -> List[SalaryRecord]:
        return [r for r in self.records.values() if not r.is_locked]

    def get_records_by_department(self, dept: str) -> List[SalaryRecord]:
        if not dept or dept == '全部':
            return self.get_all_records()
        return [r for r in self.records.values() if r.department == dept]

    def clear_all(self):
        self.records.clear()
        self.adjustments.clear()
        self.employees.clear()
        self.last_month_data.clear()
        self.import_status = {
            'salary': False, 'attendance': False, 'last_month': False
        }
