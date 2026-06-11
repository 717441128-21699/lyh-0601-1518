from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any
from enum import Enum


class SalaryStatus(Enum):
    PENDING = '待处理'
    CHECKING = '核对中'
    ADJUSTED = '已调整'
    CONFIRMED = '已确认'
    LOCKED = '已锁定'


@dataclass
class Employee:
    emp_id: str
    name: str
    department: str
    position: str = ''


@dataclass
class SalaryData:
    emp_id: str = ''
    base_salary: float = 0.0
    performance_bonus: float = 0.0
    allowance: float = 0.0
    social_insurance: float = 0.0
    housing_fund: float = 0.0
    personal_tax: float = 0.0
    other_deduction: float = 0.0
    gross_salary: float = 0.0
    net_salary: float = 0.0


@dataclass
class AttendanceData:
    emp_id: str = ''
    work_days: int = 0
    overtime_hours: float = 0.0
    leave_days: int = 0
    sick_days: int = 0
    late_times: int = 0
    absenteeism_days: int = 0


@dataclass
class SalaryRecord:
    emp_id: str
    name: str
    department: str
    position: str = ''
    salary: SalaryData = field(default_factory=SalaryData)
    attendance: AttendanceData = field(default_factory=AttendanceData)
    last_month_salary: Optional[SalaryData] = None
    status: SalaryStatus = SalaryStatus.PENDING
    issues: List[str] = field(default_factory=list)
    adjustments: List[Any] = field(default_factory=list)
    is_locked: bool = False
    confirm_time: Optional[datetime] = None


@dataclass
class AdjustmentRecord:
    emp_id: str
    name: str
    field_name: str
    old_value: float
    new_value: float
    reason: str
    operator: str
    adjust_time: datetime
