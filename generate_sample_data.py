import os
import random
import pandas as pd


EMPLOYEES = [
    ('E001', '张伟', '技术部', '高级工程师'),
    ('E002', '李娜', '技术部', '工程师'),
    ('E003', '王强', '技术部', '工程师'),
    ('E004', '刘洋', '技术部', '技术经理'),
    ('E005', '陈静', '产品部', '产品经理'),
    ('E006', '杨帆', '产品部', '产品专员'),
    ('E007', '赵敏', '设计部', '高级设计师'),
    ('E008', '孙丽', '设计部', '设计师'),
    ('E009', '周杰', '市场部', '市场经理'),
    ('E010', '吴芳', '市场部', '市场专员'),
    ('E011', '郑浩', '销售部', '销售总监'),
    ('E012', '钱玲', '销售部', '销售经理'),
    ('E013', '冯磊', '销售部', '销售代表'),
    ('E014', '韩雪', '人事部', 'HR经理'),
    ('E015', '曹阳', '人事部', '招聘专员'),
    ('E016', '许婷', '财务部', '财务经理'),
    ('E017', '何军', '财务部', '会计'),
    ('E018', '罗敏', '行政部', '行政主管'),
    ('E019', '谢涛', '运营部', '运营经理'),
    ('E020', '唐倩', '运营部', '运营专员'),
]

DEPARTMENTS = {
    '技术部': (8000, 25000),
    '产品部': (9000, 22000),
    '设计部': (7000, 20000),
    '市场部': (6000, 18000),
    '销售部': (5000, 30000),
    '人事部': (6000, 15000),
    '财务部': (7000, 20000),
    '行政部': (5000, 12000),
    '运营部': (6000, 18000),
}


def calc_tax(taxable):
    if taxable <= 0:
        return 0.0
    if taxable <= 3000:
        return taxable * 0.03
    if taxable <= 12000:
        return taxable * 0.10 - 210
    if taxable <= 25000:
        return taxable * 0.20 - 1410
    if taxable <= 35000:
        return taxable * 0.25 - 2660
    if taxable <= 55000:
        return taxable * 0.30 - 4410
    if taxable <= 80000:
        return taxable * 0.35 - 7160
    return taxable * 0.45 - 15160


def gen_salary_row(emp, abn_idx=-1, large_fluct=False, last_base=0):
    emp_id, name, dept, pos = emp
    base_range = DEPARTMENTS.get(dept, (8000, 20000))

    if last_base > 0 and not large_fluct:
        base_salary = round(last_base * random.uniform(0.98, 1.05), 0)
    else:
        base_salary = round(random.uniform(*base_range), -2)

    if large_fluct and last_base > 0:
        mult = random.choice([0.5, 0.6, 1.5, 1.8])
        base_salary = round(last_base * mult, -2)

    performance = round(base_salary * random.uniform(0.05, 0.3), 2)
    allowance = round(random.uniform(200, 1500), 2)

    social_rate = 0.105
    housing_rate = 0.12

    social_insurance = round(base_salary * social_rate, 2)
    housing_fund = round(base_salary * housing_rate, 2)

    gross = round(base_salary + performance + allowance, 2)
    taxable = gross - social_insurance - housing_fund - 5000
    personal_tax = round(max(0, calc_tax(taxable)), 2)
    other_deduction = round(random.choice([0, 0, 0, 50, 100, 200]), 2)
    net = round(gross - social_insurance - housing_fund - personal_tax - other_deduction, 2)

    row = {
        '员工编号': emp_id,
        '姓名': name,
        '部门': dept,
        '职位': pos,
        '基本工资': base_salary,
        '绩效奖金': performance,
        '津贴': allowance,
        '社保': social_insurance,
        '公积金': housing_fund,
        '个税': personal_tax,
        '其他扣款': other_deduction,
        '应发工资': gross,
        '实发工资': net,
    }

    if abn_idx == 0:
        row['社保'] = 0.0
    elif abn_idx == 1:
        row['公积金'] = round(row['公积金'] * 0.5, 2)
    elif abn_idx == 2:
        row['个税'] = 0.0
    elif abn_idx == 3:
        row['实发工资'] = round(net + 500, 2)
    elif abn_idx == 4:
        row['应发工资'] = round(gross - 1000, 2)

    return row


def gen_attendance_row(emp, abn=False):
    emp_id, name, dept, pos = emp
    work_days = 22 if not abn else random.randint(10, 18)
    return {
        '员工编号': emp_id,
        '出勤天数': work_days,
        '加班小时': round(random.uniform(0, 40), 1),
        '请假天数': random.randint(0, 3) if not abn else random.randint(4, 8),
        '病假天数': random.randint(0, 2),
        '迟到次数': random.randint(0, 3),
        '旷工天数': 0 if not abn else random.randint(1, 3),
    }


def generate_sample_data(output_dir):
    os.makedirs(output_dir, exist_ok=True)

    random.seed(42)

    last_salary_data = []
    for emp in EMPLOYEES:
        last_salary_data.append(gen_salary_row(emp))
    last_df = pd.DataFrame(last_salary_data)
    last_df.to_excel(os.path.join(output_dir, '上月工资表.xlsx'), index=False)

    this_salary_data = []
    abn_indices = list(range(len(EMPLOYEES)))
    random.shuffle(abn_indices)
    abnormal_emps = set(abn_indices[:6])
    large_fluct_emps = set(abn_indices[6:9])

    for i, emp in enumerate(EMPLOYEES):
        last_base = last_salary_data[i]['基本工资']
        abn_type = -1
        if i in abnormal_emps:
            abn_type = i % 5
        large = i in large_fluct_emps
        this_salary_data.append(gen_salary_row(emp, abn_type, large, last_base))

    this_df = pd.DataFrame(this_salary_data)
    this_df.to_excel(os.path.join(output_dir, '本月工资表.xlsx'), index=False)

    attendance_data = []
    for i, emp in enumerate(EMPLOYEES):
        abn = i in abnormal_emps
        attendance_data.append(gen_attendance_row(emp, abn))

    att_df = pd.DataFrame(attendance_data)
    att_df.to_excel(os.path.join(output_dir, '本月考勤表.xlsx'), index=False)

    print(f'示例数据已生成到: {output_dir}')
    print(f'  - 本月工资表.xlsx ({len(this_df)} 人，含 {len(abnormal_emps)} 条异常, {len(large_fluct_emps)} 条大额波动)')
    print(f'  - 本月考勤表.xlsx ({len(att_df)} 人)')
    print(f'  - 上月工资表.xlsx ({len(last_df)} 人)')


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sample_dir = os.path.join(script_dir, 'sample_data')
    generate_sample_data(sample_dir)
