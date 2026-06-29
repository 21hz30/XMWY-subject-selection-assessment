# XMWY Subject Selection Assessment

上海市西南位育中学“小三门”选课辅助系统。项目基于 Flask、Flask-Login 和 Flask-SQLAlchemy，提供学生/教师登录、学生选科测评、选科推荐结果保存，以及教师侧学生管理能力。

## 功能概览

- 学生通道：使用 8 位学号登录，完成 69 题选科测评。
- 推荐算法：按兴趣、学业表现、学习信心、竞赛/活动经历等维度计算六门学科得分，再对三科组合进行排序推荐。
- 教师通道：教师登录后可查看、添加、编辑、删除学生，并重置学生密码。
- 管理页面：代码中保留了教师表、路人表和管理员密码相关页面与路由。

## 项目结构

```text
.
├── app.py                 # Flask 主应用、路由和推荐计算逻辑
├── models.py              # SQLAlchemy 用户模型
├── config.py              # Flask/数据库配置
├── requirements.txt       # Python 依赖
├── static/                # CSS 和前端脚本
├── templates/             # Jinja2 页面模板
└── test.py                # 早期算法/页面原型
```

## 本地运行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

默认访问地址：

```text
http://127.0.0.1:5000
```

应用默认使用当前目录下的 SQLite 数据库 `xuanke.db`。该文件包含本地账号和业务数据，已被 `.gitignore` 排除，不会提交到 GitHub。

## 初始化账号

首次运行会自动建表，但不会自动创建登录账号。可用 Flask Shell 或临时脚本创建教师/学生账号，例如：

```python
from app import app
from models import db, Teacher, Student

with app.app_context():
    db.create_all()

    teacher = Teacher(name="测试教师", gender="男", employee_id="T001")
    teacher.set_password("123456")
    db.session.add(teacher)

    student = Student(class_name="高一1班", name="测试学生", gender="女", student_number="20240101")
    student.set_password("123456")
    db.session.add(student)

    db.session.commit()
```

## 注意事项

- `SECRET_KEY` 和 `DATABASE_URL` 可通过环境变量覆盖，生产环境不要使用默认密钥。
- 当前主登录页只实现了学生和教师登录。
- `app.py` 中保留了若干访客/管理员路由，但 `models.py` 里尚未定义 `Guest` 模型；如需启用这些页面，需要补齐模型和对应登录流程。
