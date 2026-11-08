"""
OGD Project seed script - Hardcoded data from Excel
Run: cd /app && python3 -m app.seed_ogd
"""
import sys
sys.path.insert(0, '/app')

from database import SessionLocal, Base, engine
from models.project import Project
from models.task import Task
from datetime import datetime

TASKS = [
    ('Visioning', '准备阶段', '界定成功画像', '确定CSF', 'ECS', 'Sam', '待开始', '2026-06-24', '2026-06-30', True, 0),
    ('Visioning', '准备阶段', '项目策略', '渠道及产品策略', '嘉顿', 'Lim/Carlson制定，Lori确认', '完成', '2026-06-03', '2026-06-10', True, 1),
    ('Visioning', '准备阶段', '项目预算', '项目预估', '嘉顿', 'Lori/Lim', '完成', '2026-06-11', '2026-06-25', False, 2),
    ('Fesibility', '准备阶段', '业务机会分析', '确定目标城市', '嘉顿', 'Lori', '完成', '2026-06-02', '2026-06-02', True, 3),
    ('Fesibility', '准备阶段', '业务机会分析', '渠道及门店清单', 'ECS', 'Lilia', '完成', '2026-06-03', '2026-06-15', False, 4),
    ('Fesibility', '准备阶段', '业务机会分析', '确定目标门店清单', '嘉顿', 'Lori/何纪辉', '完成', '2026-06-15', '2026-06-18', False, 5),
    ('Development', '准备阶段', '供应链流程', '确定供应链具体对接方案', '嘉顿', '蒋大方', '完成', '2026-06-08', '2026-06-12', False, 6),
    ('Development', '准备阶段', '财务对接流程', '确定财务具体对接方案', '嘉顿', '张振兴', '完成', '2026-06-08', '2026-06-12', False, 7),
    ('Development', '准备阶段', '项目目标', '确定分销产品清单', '嘉顿', 'Lim/Carlson制定，Lori确认', '完成', '2026-06-08', '2026-06-10', True, 8),
    ('Development', '准备阶段', '项目目标', '分销目标', '嘉顿', 'Lori/何纪辉', '完成', '2026-06-15', '2026-06-23', True, 9),
    ('Development', '准备阶段', '项目目标', '门店活跃率目标', '嘉顿', 'Lori/何纪辉', '完成', '2026-06-15', '2026-06-23', False, 10),
    ('Development', '准备阶段', '项目目标', '门店上翻目标', '嘉顿', 'Lori/何纪辉', '完成', '2026-06-15', '2026-06-23', False, 11),
    ('Development', '准备阶段', '项目目标', 'AAM指标及衡量标准', '嘉顿/ECS', 'Joanne/Sam', '完成', '2026-06-03', '2026-06-15', True, 12),
    ('Development', '准备阶段', '执行标准', '确定渠道门店分销标准', '嘉顿', 'Lim/Carlson制定，Lori确认', '完成', '2026-06-03', '2026-06-10', False, 13),
    ('Development', '准备阶段', '执行标准', '确定渠道陈列标准', '嘉顿', 'Lim/Carlson', '完成', '2026-06-03', '2026-06-10', False, 14),
    ('Development', '准备阶段', '执行标准', '确定渠道销售套餐', '嘉顿', 'Lim/Carlson', '完成', '2026-06-03', '2026-06-10', False, 15),
    ('Development', '准备阶段', '项目奖励机制', '销售团队奖励机制', '嘉顿', 'Lim/Carlson', '完成', '2026-06-03', '2026-06-10', False, 16),
    ('Development', '准备阶段', '项目奖励机制', '客户奖励机制', '嘉顿', 'Lim/Carlson', '完成', '2026-06-03', '2026-06-10', False, 17),
    ('Development', '准备阶段', '项目流程', '确定供应链流程', '嘉顿/ECS', 'Lim/Lila', '进行中', '2026-06-03', '2026-06-10', False, 18),
    ('Development', '准备阶段', '项目流程', '确定财务流程', '嘉顿/ECS', 'Lim/Lila', '进行中', '2026-06-03', '2026-06-10', False, 19),
    ('Development', '准备阶段', '项目预算', '制定项目预算', '嘉顿', 'Lori/Lim', '完成', '2026-06-11', '2026-06-25', False, 20),
    ('Development', '准备阶段', '项目预算', '确定项目预算', '嘉顿', 'Lori/Lim', '完成', '2026-06-11', '2026-06-25', True, 21),
    ('Development', '准备阶段', '项目流程', '确认服务形式及费用', '嘉顿/ECS', 'Lori/Sam', '完成', '2026-06-10', '2026-06-15', False, 22),
    ('Development', '准备阶段', '项目流程', '完成合同签署', '嘉顿/ECS', 'Lori/Sam', '进行中', '2026-07-01', '2026-07-10', True, 23),
    ('Development', '准备阶段', '技术解决方案', '系统配置', 'ECS', 'Lila', '进行中', '2026-07-01', '2026-07-06', False, 24),
    ('Development', '准备阶段', '技术解决方案', '商城配置', 'ECS', 'Lila', '进行中', '2026-07-01', '2026-07-06', False, 25),
    ('Development', '准备阶段', '嘉顿微信小程序注册', '完成微信小程序注册', 'ECS', 'Lila', '进行中', '2026-07-01', '2026-07-10', True, 26),
    ('Development', '准备阶段', '微信小程序主体', '确定微信小程序主体', '嘉顿/ECS', 'Sam', '完成', '2026-06-22', '2026-06-24', True, 27),
    ('Commissioning', '准备阶段', '团队沟通', '一线团队培训', 'ECS', 'Lila', '待开始', '2026-07-03', '2026-07-03', True, 28),
    ('Commissioning', '准备阶段', '可持续机制', '商城活动', 'ECS', 'Lila', '待开始', '2026-06-16', '2026-06-26', False, 29),
    ('Commissioning', '准备阶段', '可持续机制', '商城内容', 'ECS', 'Lila', '待开始', '2026-06-16', '2026-06-30', False, 30),
    ('Commissioning', '项目实施', '项目上线', '项目正式启动', '嘉顿/ECS', 'Lori/Lilia', '待开始', '2026-07-10', '2026-07-10', True, 31),
    ('Commissioning', '实施阶段', '拓店管理', '销售拓、店内执行及活跃率管理', 'ECS', 'Lila', '待开始', None, None, False, 32),
    ('Commissioning', '实施阶段', '拓店管理', '订货商城运营', 'ECS', 'Lila', '待开始', None, None, False, 33),
    ('Commissioning', '实施阶段', '建立项目追踪体系', '每日项目进度追踪报告', 'ECS', 'Lila', '待开始', None, None, False, 34),
    ('Commissioning', '实施阶段', '建立项目追踪体系', '每周项目进度回顾及调优', 'ECS', 'Lila', '待开始', None, None, False, 35),
    ('Implementation & Nurture', '准备阶段', '项目回顾及调优', '制定项目调优行动计划', 'ECS', 'Sam', '待开始', '2026-08-01', '2026-07-10', False, 36),
    ('Continue Improvement', '回顾阶段', '项目回顾及调优', '项目周期性评估（每月）', 'ECS', 'Lila', '待开始', '2026-08-01', '2026-08-10', True, 37),
    ('Continue Improvement', '回顾阶段', '项目回顾及调优', 'AAM指标评估', 'ECS', 'Sam', '待开始', '2026-08-01', '2026-08-10', False, 38),
]


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.name == "Garden OGD Project").first()
        if not project:
            project = Project(name="Garden OGD Project", status="进行中", sort_order=1)
            db.add(project)
            db.flush()
            print(f"[+] 创建项目: Garden OGD Project")
        else:
            print(f"[=] 项目已存在: Garden OGD Project")
            db.query(Task).filter(Task.project_id == project.id).delete()
            db.flush()

        for i, (ebc, phase, content, deliverable, company, person, status, start_str, end_str, is_milestone, sort) in enumerate(TASKS):
            sd = datetime.strptime(start_str, "%Y-%m-%d").date() if start_str else None
            ed = datetime.strptime(end_str, "%Y-%m-%d").date() if end_str else None
            task = Task(
                project_id=project.id, ebc_step=ebc, phase=phase, content=content,
                deliverable=deliverable, company=company, person_responsible=person,
                status=status, start_date=sd, end_date=ed, is_milestone=is_milestone,
                is_draft=False, sort_order=i,
            )
            db.add(task)

        db.commit()
        total = len(TASKS)
        print(f"[+] 导入完成！共 {total} 条任务")
        print(f"[+] 项目: Garden OGD Project")
        done = sum(1 for t in TASKS if t[6] == "完成")
        progress = sum(1 for t in TASKS if t[6] == "进行中")
        pending = sum(1 for t in TASKS if t[6] == "待开始")
        mile = sum(1 for t in TASKS if t[7])
        print(f"[+] 已完成: {done}, 进行中: {progress}, 待开始: {pending}, 里程碑: {mile}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
