"""
Seed script: Import Excel data into the database.
Run with: python3 seed.py <path-to-excel>
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import openpyxl
from database import SessionLocal, Base, engine
from models.user import User
from models.project import Project
from models.task import Task
from models import seed_defaults
from datetime import datetime, date


def import_excel(filepath):
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Create default super admin
        admin = db.query(User).filter(User.email == "admin@ecs.com").first()
        if not admin:
            admin = User(
                email="admin@ecs.com",
                username="系统管理员",
                company="ECS",
                role="super_admin",
                status="active",
            )
            admin.set_password(os.environ.get("INITIAL_ADMIN_PASSWORD", "").strip() or __import__("secrets").token_urlsafe(18))
            db.add(admin)
            print("[+] 创建超级管理员: admin@ecs.com（密码来自 INITIAL_ADMIN_PASSWORD 或随机生成）")
        else:
            print("[=] 管理员已存在，跳过")

        wb = openpyxl.load_workbook(filepath, data_only=True)

        # 2. Import projects
        ws = wb["项目列表"]
        project_map = {}
        for row in ws.iter_rows(min_row=2, values_only=True):
            pid, name, status, sort_order = row[0], row[1], row[2], row[3]
            if not name:
                continue
            project = db.query(Project).filter(Project.name == name).first()
            if not project:
                project = Project(name=name, status=status or "进行中", sort_order=sort_order or 99)
                db.add(project)
                db.flush()
                print(f"[+] 创建项目: {name}")
            else:
                print(f"[=] 项目已存在: {name}")
            project_map[pid] = project

        db.commit()

        # 3. Import tasks
        ws = wb["甘特图数据"]
        task_count = 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            project_name, ebc_step, phase, content, deliverable, company, person, status, start_date, end_date, is_milestone, task_id = row
            if not project_name or not content:
                continue

            project = db.query(Project).filter(Project.name == project_name).first()
            if not project:
                continue

            existing = db.query(Task).filter(
                Task.project_id == project.id,
                Task.content == content,
                Task.deliverable == deliverable,
            ).first()
            if existing:
                continue

            sd = None
            if isinstance(start_date, (datetime, date)):
                sd = start_date if isinstance(start_date, date) else start_date.date()
            elif start_date:
                try:
                    sd = datetime.strptime(str(start_date), "%Y-%m-%d").date()
                except Exception:
                    pass

            ed = None
            if isinstance(end_date, (datetime, date)):
                ed = end_date if isinstance(end_date, date) else end_date.date()
            elif end_date:
                try:
                    ed = datetime.strptime(str(end_date), "%Y-%m-%d").date()
                except Exception:
                    pass

            task = Task(
                project_id=project.id,
                ebc_step=str(ebc_step or ""),
                phase=str(phase or "准备阶段"),
                content=str(content or ""),
                deliverable=str(deliverable or ""),
                company=str(company or ""),
                person_responsible=str(person or ""),
                status=str(status or "待开始"),
                start_date=sd,
                end_date=ed,
                is_milestone=bool(is_milestone and str(is_milestone).strip() == "\u2713"),
                is_draft=False,
                sort_order=task_count,
            )
            db.add(task)
            task_count += 1

        db.commit()
        print(f"[+] 导入 {task_count} 条任务")

        print("\n=== 导入完成 ===")
        print("管理员: admin@ecs.com（密码来自 INITIAL_ADMIN_PASSWORD 或随机生成）")
        print(f"项目数: {db.query(Project).count()}")
        print(f"任务数: {db.query(Task).count()}")

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 seed.py <path-to-excel.xlsx>")
        sys.exit(1)
    import_excel(sys.argv[1])
