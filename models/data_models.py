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


class OperationType(Enum):
    ADJUSTMENT = '金额调整'
    LOCK = '锁定确认'
    UNLOCK = '取消锁定'
    RULE_CHECKED = '规则检查通过'
    DIFF_CHECKED = '差异核对通过'
    ADJUSTMENT_REVIEWED = '调整复核通过'
    SALARY_IMPORTED = '工资表导入'
    ATTENDANCE_IMPORTED = '考勤表导入'
    LASTMONTH_IMPORTED = '上月工资导入'
    ISSUE_RESOLVED = '问题标记已解决'
    BATCH_RULE_CHECK = '批量规则检查'
    BATCH_DIFF_CHECK = '批量差异核对'
    BATCH_LOCK = '批量锁定确认'
    PROJECT_SAVED = '项目保存'
    PROJECT_LOADED = '项目加载'


class ImportFileType(Enum):
    SALARY = '工资表'
    ATTENDANCE = '考勤表'
    LAST_MONTH = '上月工资表'


@dataclass
class ImportBatch:
    batch_id: str
    file_type: ImportFileType
    file_name: str
    import_time: datetime
    operator: str
    total_count: int = 0
    updated_count: int = 0
    skipped_locked_count: int = 0
    new_count: int = 0
    updated_employees: List[str] = field(default_factory=list)
    skipped_employees: List[str] = field(default_factory=list)
    new_employees: List[str] = field(default_factory=list)
    note: str = ''

    def to_dict(self) -> Dict:
        return {
            'batch_id': self.batch_id,
            'file_type': self.file_type.name,
            'file_name': self.file_name,
            'import_time': self.import_time.isoformat(),
            'operator': self.operator,
            'total_count': self.total_count,
            'updated_count': self.updated_count,
            'skipped_locked_count': self.skipped_locked_count,
            'new_count': self.new_count,
            'updated_employees': self.updated_employees,
            'skipped_employees': self.skipped_employees,
            'new_employees': self.new_employees,
            'note': self.note,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ImportBatch':
        return cls(
            batch_id=data['batch_id'],
            file_type=ImportFileType[data['file_type']],
            file_name=data['file_name'],
            import_time=datetime.fromisoformat(data['import_time']),
            operator=data.get('operator', ''),
            total_count=data.get('total_count', 0),
            updated_count=data.get('updated_count', 0),
            skipped_locked_count=data.get('skipped_locked_count', 0),
            new_count=data.get('new_count', 0),
            updated_employees=data.get('updated_employees', []),
            skipped_employees=data.get('skipped_employees', []),
            new_employees=data.get('new_employees', []),
            note=data.get('note', ''),
        )


@dataclass
class ReviewSteps:
    rule_checked: bool = False
    diff_checked: bool = False
    adjustment_reviewed: bool = False
    rule_check_time: Optional[datetime] = None
    diff_check_time: Optional[datetime] = None
    adjustment_review_time: Optional[datetime] = None

    def all_completed(self) -> bool:
        return self.rule_checked and self.diff_checked and self.adjustment_reviewed

    def get_unfinished(self) -> List[str]:
        unfinished = []
        if not self.rule_checked:
            unfinished.append('规则检查')
        if not self.diff_checked:
            unfinished.append('差异核对')
        if not self.adjustment_reviewed:
            unfinished.append('调整复核')
        return unfinished


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
class IssueItem:
    issue_id: str
    level: str
    category: str
    message: str
    resolved: bool = False
    resolve_time: Optional[datetime] = None
    resolve_note: str = ''

    def to_dict(self) -> Dict:
        return {
            'issue_id': self.issue_id,
            'level': self.level,
            'category': self.category,
            'message': self.message,
            'resolved': self.resolved,
            'resolve_time': self.resolve_time.isoformat() if self.resolve_time else None,
            'resolve_note': self.resolve_note,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'IssueItem':
        item = cls(
            issue_id=data.get('issue_id', ''),
            level=data['level'],
            category=data['category'],
            message=data['message'],
            resolved=data.get('resolved', False),
            resolve_note=data.get('resolve_note', ''),
        )
        if data.get('resolve_time'):
            item.resolve_time = datetime.fromisoformat(data['resolve_time'])
        return item


@dataclass
class OperationLog:
    operation_type: OperationType
    emp_id: str
    name: str
    detail: str
    operator: str
    operate_time: datetime
    field_name: str = ''
    old_value: float = 0.0
    new_value: float = 0.0

    def to_dict(self) -> Dict:
        return {
            'operation_type': self.operation_type.name,
            'emp_id': self.emp_id,
            'name': self.name,
            'detail': self.detail,
            'operator': self.operator,
            'operate_time': self.operate_time.isoformat(),
            'field_name': self.field_name,
            'old_value': self.old_value,
            'new_value': self.new_value,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'OperationLog':
        return cls(
            operation_type=OperationType[data['operation_type']],
            emp_id=data['emp_id'],
            name=data['name'],
            detail=data['detail'],
            operator=data['operator'],
            operate_time=datetime.fromisoformat(data['operate_time']),
            field_name=data.get('field_name', ''),
            old_value=data.get('old_value', 0.0),
            new_value=data.get('new_value', 0.0),
        )


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
    issues: List[IssueItem] = field(default_factory=list)
    issue_messages: List[str] = field(default_factory=list)
    review_steps: ReviewSteps = field(default_factory=ReviewSteps)
    adjustments: List[OperationLog] = field(default_factory=list)
    is_locked: bool = False
    confirm_time: Optional[datetime] = None
    unlock_time: Optional[datetime] = None

    def get_unfinished_review_steps(self) -> List[str]:
        return self.review_steps.get_unfinished()

    def is_review_complete(self) -> bool:
        return self.review_steps.all_completed()

    def has_unresolved_issues(self) -> bool:
        return any(not i.resolved for i in self.issues)

    def get_unresolved_issues(self) -> List[IssueItem]:
        return [i for i in self.issues if not i.resolved]


@dataclass
class ProjectMeta:
    project_name: str
    created_time: datetime
    last_saved_time: Optional[datetime]
    current_month: str
    operator: str
    total_employees: int = 0
    locked_count: int = 0
    adjustment_count: int = 0
    note: str = ''

    def to_dict(self) -> Dict:
        return {
            'project_name': self.project_name,
            'created_time': self.created_time.isoformat(),
            'last_saved_time': self.last_saved_time.isoformat() if self.last_saved_time else None,
            'current_month': self.current_month,
            'operator': self.operator,
            'total_employees': self.total_employees,
            'locked_count': self.locked_count,
            'adjustment_count': self.adjustment_count,
            'note': self.note,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ProjectMeta':
        meta = cls(
            project_name=data['project_name'],
            created_time=datetime.fromisoformat(data['created_time']),
            last_saved_time=datetime.fromisoformat(data['last_saved_time']) if data.get('last_saved_time') else None,
            current_month=data.get('current_month', ''),
            operator=data.get('operator', ''),
            total_employees=data.get('total_employees', 0),
            locked_count=data.get('locked_count', 0),
            adjustment_count=data.get('adjustment_count', 0),
            note=data.get('note', ''),
        )
        return meta


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
