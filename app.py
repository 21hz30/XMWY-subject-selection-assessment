import random
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, Student, Teacher
import itertools

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = '请先登录后再访问该页面。'
recommendation_store = []


class StaticStudent:
    id = '20250226'
    name = '刘恺文'
    class_name = '高一(2)班'
    student_number = '20250226'

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return 'static_student_20250226'

    def get_role(self):
        return 'student'


STATIC_STUDENT = StaticStudent()
STATIC_STUDENT_NUMBER = '20250226'
STATIC_STUDENT_PASSWORD = '20250226'


# ---------- Flask-Login user loader ----------
@login_manager.user_loader
def load_user(user_id):
    if user_id == STATIC_STUDENT.get_id():
        return STATIC_STUDENT
    return None


# ---------- Permission decorators ----------
def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.get_role() not in roles:
                flash('您没有权限访问该页面。', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ---------- Login page (multi-channel) ----------
@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        role = request.form.get('role')
        if role == 'student':
            student_number = request.form.get('student_number', '').strip()
            password = request.form.get('password', '').strip()
            if not student_number or not password:
                flash('请输入学号和密码。', 'warning')
                return redirect(url_for('login'))
            if student_number == STATIC_STUDENT_NUMBER and password == STATIC_STUDENT_PASSWORD:
                login_user(STATIC_STUDENT)
                flash(f'欢迎回来，{STATIC_STUDENT.name}同学！', 'success')
                return redirect(url_for('dashboard'))
            flash('学号或密码错误。', 'danger')
            return redirect(url_for('login'))

        elif role == 'teacher':
            flash('当前线上版本仅开放学生账号登录。', 'warning')
            return redirect(url_for('login'))

    return render_template('login.html')


# ---------- Logout ----------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已成功退出登录。', 'info')
    return redirect(url_for('login'))


# ---------- Dashboard ----------
@app.route('/dashboard')
@login_required
def dashboard():
    role = current_user.get_role()
    if role == 'student':
        selected = session.get('selected_courses')
        return render_template('dashboard.html', role=role, selected = selected)
    else:
        return render_template('dashboard.html', role=role)


# Survey questions definition
SURVEY_QUESTIONS = [
    # 第一部分：兴趣倾向测评 (1-28)
    # 物理学科兴趣 1-4
    {'id': 1, 'text': '物理课上讲到一个新原理时，我心里会涌起一种"原来世界是这样运转的"的满足感，而不仅仅是记住了一个考点。', 'type': 'scale_0_5', 'category': '物理兴趣'},
    {'id': 2, 'text': '做物理题时，如果解出一种巧妙的方法，我会忍不住想跟同桌分享或者自己在草稿纸上反复回味，哪怕它并不是考试要求的最优解。', 'type': 'scale_0_5', 'category': '物理兴趣'},
    {'id': 3, 'text': '当老师讲一个新公式时，我更在意"它是怎么推导出来的"，而不仅仅是"怎么用它做题"。', 'type': 'scale_0_5', 'category': '物理兴趣'},
    {'id': 4, 'text': '即使物理不是我成绩最好的科目，我也隐隐觉得这门课让我"变聪明了"——它教会我用一种更清晰的逻辑去看待其他事情。', 'type': 'scale_0_5', 'category': '物理兴趣'},
    # 化学学科兴趣 5-8
    {'id': 5, 'text': '刚开始学化学时，老师演示加热实验时，我心里会下意识有一种"会不会爆炸"的期待', 'type': 'scale_0_5', 'category': '化学兴趣'},
    {'id': 6, 'text': '学到一种物质的性质时，我会下意识联想到它在生活中的用途，比如"原来这个清洁剂就是利用了酸去水垢"。', 'type': 'scale_0_5', 'category': '化学兴趣'},
    {'id': 7, 'text': '在厨房看到小苏打和白醋反应冒泡时，我会觉得好玩，并好奇为什么。', 'type': 'scale_0_5', 'category': '化学兴趣'},
    {'id': 8, 'text': '我乐于了解化学在医药、材料、环保等领域的实际应用。', 'type': 'scale_0_5', 'category': '化学兴趣'},
    # 生物学科兴趣 9-12
    {'id': 9, 'text': '我对于在什么时间什么地点能看到什么样的动植物出现很感兴趣。', 'type': 'scale_0_5', 'category': '生物兴趣'},
    {'id': 10, 'text': '看到显微镜下的细胞切片或课本上的DNA双螺旋图时，我会觉得生命在微观层面如此精巧，甚至有些感动。', 'type': 'scale_0_5', 'category': '生物兴趣'},
    {'id': 11, 'text': '我主动关注人体生理、营养健康、疾病预防等医学话题。', 'type': 'scale_0_5', 'category': '生物兴趣'},
    {'id': 12, 'text': '即使要背的东西很多，我也觉得生物讲的都是"关于生命本身的故事"，而不仅仅是零散的知识点。', 'type': 'scale_0_5', 'category': '生物兴趣'},
    # 历史学科兴趣 13-16
    {'id': 13, 'text': '学到某个历史事件时，我会想了解更多当时事件的细节以及发生原因。', 'type': 'scale_0_5', 'category': '历史兴趣'},
    {'id': 14, 'text': '我逛博物馆时，能盯着一件文物看很久，想了解它背后的故事。', 'type': 'scale_0_5', 'category': '历史兴趣'},
    {'id': 15, 'text': '我觉得历史不只是"过去发生的事"，而是一面能帮我看懂今天许多事情的镜子。', 'type': 'scale_0_5', 'category': '历史兴趣'},
    {'id': 16, 'text': '当老师讲到一个历史人物的抉择时，我会试着站在他的立场去感受当时的压力与两难，而不是简单地直接批判他的行为。', 'type': 'scale_0_5', 'category': '历史兴趣'},
    # 地理学科兴趣 17-20
    {'id': 17, 'text': '旅游或出门时，我会在心里默默对照学过的地理知识，比如"湿润地区的屋顶尖尖的"。', 'type': 'scale_0_5', 'category': '地理兴趣'},
    {'id': 18, 'text': '到一个新地方，我很快就能在脑子里建立起方向感，不喜欢只靠导航软件指路。', 'type': 'scale_0_5', 'category': '地理兴趣'},
    {'id': 19, 'text': '无聊的时候我愿意去拨弄地球仪，或盯着挂在墙上的地图看个半天。', 'type': 'scale_0_5', 'category': '地理兴趣'},
    {'id': 20, 'text': '坐火车或长途汽车时，我会盯着窗外看沿途的地形、植被和农田怎么变化，不觉得无聊。', 'type': 'scale_0_5', 'category': '地理兴趣'},
    # 政治学科兴趣 21-24
    {'id': 21, 'text': '当一个社会热点事件出来时，我会忍不住去分析"这件事涉及哪几方的利益、他们各自想要什么"，而不仅仅是站队吃瓜。', 'type': 'scale_0_5', 'category': '政治兴趣'},
    {'id': 22, 'text': '在课堂上讨论一个有争议的话题时，我更关心"为什么大家会持有不同的立场"，而不是急于证明自己是对的。', 'type': 'scale_0_5', 'category': '政治兴趣'},
    {'id': 23, 'text': '学习某项制度或法律时，我会下意识去想"它当初是为了解决什么问题而设计的"，而不仅仅是把它当作要背的条目。', 'type': 'scale_0_5', 'category': '政治兴趣'},
    {'id': 24, 'text': '我希望找到某种合理的政策或制度，让所有人生活的更幸福。', 'type': 'scale_0_5', 'category': '政治兴趣'},
    # 跨学科兴趣倾向 25-28
    {'id': 25, 'text': '我对"事物的因果链条"更着迷，而对"事物的美感和情绪"相对没那么敏感。', 'type': 'scale_0_5', 'category': '跨学科'},
    {'id': 26, 'text': '同样是"论证一件事"，我更喜欢用逻辑推理的方式，而不是用讲故事或用情感打动人的方式。', 'type': 'scale_0_5', 'category': '跨学科'},
    {'id': 27, 'text': '比起在一个领域里钻得很深，我对"把两个不同的领域连接起来"更有兴奋感。', 'type': 'scale_0_5', 'category': '跨学科'},
    {'id': 28, 'text': '在阅读科普文章或观看纪录片时，我更喜欢那些既讲科学原理又讲社会影响的内容（如《地球脉动》、《美丽中国》），而不是纯科学或纯人文的内容。', 'type': 'scale_0_5', 'category': '跨学科'},

    # 第二部分：学业表现测评 (29-60)
    # 物理成绩相关 29-33
    {'id': 29, 'text': '我的物理成绩在当前年级中的相对水平如何？', 'type': 'rank', 'category': '物理成绩'},
    {'id': 30, 'text': '在物理考试中，遇到公式推导题，我得分如何？', 'type': 'percentage', 'category': '物理成绩'},
    {'id': 31, 'text': '我的物理成绩的稳定性如何？', 'type': 'scale_1_5', 'category': '物理成绩'},
    {'id': 32, 'text': '上物理新课时，我的课堂吸收率大概是多少？', 'type': 'percentage', 'category': '物理成绩'},
    {'id': 33, 'text': '我在物理学科的投入产出比（努力程度与成绩的匹配度）如何？', 'type': 'percentage', 'category': '物理成绩'},
    # 化学成绩相关 34-38
    {'id': 34, 'text': '我的化学成绩在当前年级中的相对水平如何？', 'type': 'rank', 'category': '化学成绩'},
    {'id': 35, 'text': '在考卷上遇到新的方程式时，我能够联想自己已经学过的方程式吗？', 'type': 'scale_0_5', 'category': '化学成绩'},
    {'id': 36, 'text': '我的化学成绩的稳定性如何？', 'type': 'scale_0_5', 'category': '化学成绩'},
    {'id': 37, 'text': '上化学新课时，我的课堂吸收率大概是多少？', 'type': 'scale_0_5', 'category': '化学成绩'},
    {'id': 38, 'text': '我在化学学科的投入产出比（努力程度与成绩的匹配度）如何？', 'type': 'percentage', 'category': '化学成绩'},
    # 生物成绩相关 39-43
    {'id': 39, 'text': '我的生物成绩在当前年级中的相对水平如何？', 'type': 'rank', 'category': '生物成绩'},
    {'id': 40, 'text': '现在让我对于生物课本中的某一生理过程进行自主描述，我能讲清楚吗？', 'type': 'percentage', 'category': '生物成绩'},
    {'id': 41, 'text': '我的生物成绩的稳定性如何？', 'type': 'scale_0_5', 'category': '生物成绩'},
    {'id': 42, 'text': '上生物新课时，我的课堂吸收率大概是多少？', 'type': 'percentage', 'category': '生物成绩'},
    {'id': 43, 'text': '我在生物学科的投入产出比（努力程度与成绩的匹配度）如何？', 'type': 'percentage', 'category': '生物成绩'},
    # 历史成绩相关 44-48
    {'id': 44, 'text': '我的历史成绩在当前年级中的相对水平如何？', 'type': 'rank', 'category': '历史成绩'},
    {'id': 45, 'text': '我在答历史大题时，大脑中是否能梳理出清晰的逻辑框架？', 'type': 'percentage', 'category': '历史成绩'},
    {'id': 46, 'text': '我的历史成绩的稳定性如何？', 'type': 'scale_0_5', 'category': '历史成绩'},
    {'id': 47, 'text': '我对历史时间线、事件脉络的梳理能力如何？', 'type': 'scale_0_5', 'category': '历史成绩'},
    {'id': 48, 'text': '我在历史学科的投入产出比（努力程度与成绩的匹配度）如何？', 'type': 'percentage', 'category': '历史成绩'},
    # 地理成绩相关 49-53
    {'id': 49, 'text': '我的地理成绩在当前年级中的相对水平如何？', 'type': 'rank', 'category': '地理成绩'},
    {'id': 50, 'text': '我的地理读图识图能力如何？', 'type': 'percentage', 'category': '地理成绩'},
    {'id': 51, 'text': '我的地理成绩的稳定性如何？', 'type': 'scale_0_5', 'category': '地理成绩'},
    {'id': 52, 'text': '上地理新课时，我的课堂吸收率大概是多少？', 'type': 'scale_0_5', 'category': '地理成绩'},
    {'id': 53, 'text': '我在地理学科的投入产出比（努力程度与成绩的匹配度）如何？', 'type': 'percentage', 'category': '地理成绩'},
    # 政治成绩相关 54-58
    {'id': 54, 'text': '我的政治成绩在当前年级中的相对水平如何？', 'type': 'rank', 'category': '政治成绩'},
    {'id': 55, 'text': '我在答政治大题时，大脑中是否能梳理出清晰的逻辑框架？', 'type': 'percentage', 'category': '政治成绩'},
    {'id': 56, 'text': '我的政治成绩的稳定性如何？', 'type': 'scale_0_5', 'category': '政治成绩'},
    {'id': 57, 'text': '我在大题中运用政治术语和理论的能力如何？', 'type': 'scale_0_5', 'category': '政治成绩'},
    {'id': 58, 'text': '我在政治学科的投入产出比（努力程度与成绩的匹配度）如何？', 'type': 'percentage', 'category': '政治成绩'},
    # 学习信心 59-64
    {'id': 59, 'text': '面对物理的新知识新题型，我有信心学好并应对考试吗？', 'type': 'scale_0_5', 'category': '物理信心'},
    {'id': 60, 'text': '面对化学的新知识新题型，我有信心学好并应对考试吗？', 'type': 'scale_0_5', 'category': '化学信心'},
    {'id': 61, 'text': '面对生物的新知识新题型，我有信心学好并应对考试吗？', 'type': 'scale_0_5', 'category': '生物信心'},
    {'id': 62, 'text': '面对历史的新知识新题型，我有信心学好并应对考试吗？', 'type': 'scale_0_5', 'category': '历史信心'},
    {'id': 63, 'text': '面对地理的新知识新题型，我有信心学好并应对考试吗？', 'type': 'scale_0_5', 'category': '地理信心'},
    {'id': 64, 'text': '面对政治的新知识新题型，我有信心学好并应对考试吗？', 'type': 'scale_0_5', 'category': '政治信心'},
    # 竞赛与活动经历 65-69
    {'id': 65, 'text': '我是否参加过偏理科相关竞赛或科技活动？（eg.数理化生信相关竞赛、地生竞赛、数学建模、机器人…）', 'type': 'scale_0_5', 'category': '理科竞赛'},
    {'id': 66, 'text': '我在偏理科相关竞赛或课题研究中参与程度如何？', 'type': 'scale_0_5', 'category': '理科研究'},
    {'id': 67, 'text': '我是否有偏文科相关的课题研究经历或竞赛？（eg.时政竞赛、作文大赛、古诗文竞赛……）', 'type': 'scale_0_5', 'category': '文科竞赛'},
    {'id': 68, 'text': '我在偏文科相关竞赛或课题研究中参与程度如何？', 'type': 'scale_0_5', 'category': '文科研究'},
    {'id': 69, 'text': '我参与的校本课程或社团活动中，与理科相关的占比如何？（1=完全偏向文科，3=文理均衡，5=完全偏向理科）', 'type': 'scale_0_5', 'category': '活动'}
]


# ---------- Survey page ----------
@app.route('/survey')
@login_required
def survey():
    return render_template('survey.html', questions=SURVEY_QUESTIONS)


@app.route('/survey/get-resource')
@login_required
def get_resource():
    selected = session.get('selected_courses')
    return jsonify({
        'status': 'ok',
        'recommendation': selected
    })

# ---------- Survey submission & scoring ----------
@app.route('/survey/submit', methods=['POST'])
@login_required
def survey_submit():
    data = request.get_json()
    answers = data.get('answers', {})

    # 解析所有答案分数
    scores = {}
    for q in SURVEY_QUESTIONS:
        qid = str(q['id'])
        raw = answers.get(qid)
        if raw is None:
            scores[q['id']] = 1
            continue
        try:
            raw = int(raw)
        except (ValueError, TypeError):
            scores[q['id']] = 1
            continue

        qtype = q['type']
        if qtype == 'rank':
            # D1=1, C1=2, B2=3, B1=4, A1=5
            mapping = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}
            scores[q['id']] = mapping.get(raw, 1)
        elif qtype == 'percentage':
            # Already 1-5 from frontend
            scores[q['id']] = raw
        elif qtype == 'scale_0_5':
            scores[q['id']] = raw
        elif qtype == 'scale_1_5':
            scores[q['id']] = raw
        elif qtype == 'subject_choice':
            scores[q['id']] = raw
        else:
            scores[q['id']] = raw

    # 计算各科权重分（原始分累加）
    def sum_q(nums):
        return sum(scores.get(n, 1) for n in nums)

    physics_interest = round(sum_q([1, 2, 3, 4]) / 4,3)
    chemistry_interest = round(sum_q([5, 6, 7, 8]) / 4,3)
    biology_interest = round(sum_q([9, 10, 11, 12]) / 4,3)
    geography_interest = round(sum_q([17, 18, 19, 20]) / 4,3)
    politics_interest = round(sum_q([21, 22, 23, 24]) / 4,3)
    history_interest = round(sum_q([13, 14, 15, 16]) / 4,3)
    leng = [25,26]
    for i in leng:
        tmp = scores.get(i, 1)
        if tmp == 5:
            physics_interest *= 1.2
            chemistry_interest *= 1.2
            biology_interest *= 1.2
        elif tmp == 4:
            physics_interest *= 1.1
            chemistry_interest *= 1.1
            biology_interest *= 1.1
        elif tmp == 2:
            geography_interest *= 1.1
            politics_interest *= 1.1
            history_interest *= 1.1
        elif tmp == 1:
            geography_interest *= 1.2
            politics_interest *= 1.2
            history_interest *= 1.2

    leng = [27,28]
    for i in leng:
        tmp = scores.get(i, 1)
        if tmp == 5:
            geography_interest *= 1.2
            biology_interest *= 1.2
        elif tmp == 4:
            geography_interest *= 1.1
            biology_interest *= 1.1

    physics_score = round(sum_q([29,30,31,32,33]) / 5 , 3)
    chemistry_score = round(sum_q([34,35,36,37,38]) / 5 , 3)
    biology_score = round(sum_q([39,40,41,42,43]) / 5 , 3)
    geography_score = round(sum_q([49,50,51,52,53]) / 5 , 3)
    politics_score = round(sum_q([54,55,56,57,58]) / 5 , 3)
    history_score = round(sum_q([44,45,46,47,48]) / 5 , 3)

    physics_confidence = scores.get(59, 1)
    chemistry_confidence = scores.get(60, 1)
    biology_confidence = scores.get(61, 1)
    geography_confidence = scores.get(63, 1)
    politics_confidence = scores.get(64, 1)
    history_confidence = scores.get(62, 1)

    tmp = scores.get(69, 1)
    if tmp == 1:
        li_practice = round((scores.get(65, 1) + scores.get(66, 1)) / 2 , 3)
        physics_raw = round(physics_interest * 0.35 + physics_score * 0.4 + physics_confidence * 0.1 + li_practice * 0.15 , 3)
        chemistry_raw = round(chemistry_interest * 0.35 + chemistry_score * 0.4 + chemistry_confidence * 0.1 + li_practice* 0.15 , 3)
        biology_raw = round(biology_interest * 0.35 + biology_score * 0.4 + biology_confidence * 0.1 + li_practice * 0.15 , 3)

        wen_practice = round((scores.get(67, 1) + scores.get(68, 1) + 5) / 3 , 3)
        geography_raw = round(geography_interest * 0.35 + geography_score * 0.4 + geography_confidence * 0.1 + wen_practice * 0.15 , 3)
        politics_raw = round(politics_interest * 0.35 + politics_score * 0.4 + politics_confidence * 0.1 + wen_practice * 0.15 , 3)
        history_raw = round(history_interest * 0.35 + history_score * 0.4 + history_confidence * 0.1 + wen_practice * 0.15 , 3)
    elif tmp == 2:
        li_practice = round((scores.get(65, 1) + scores.get(66, 1)) / 2 , 3)
        physics_raw = round(physics_interest * 0.35 + physics_score * 0.4 + physics_confidence * 0.1 + li_practice * 0.15 , 3)
        chemistry_raw = round(chemistry_interest * 0.35 + chemistry_score * 0.4 + chemistry_confidence * 0.1 + li_practice * 0.15 , 3)
        biology_raw = round(biology_interest * 0.35 + biology_score * 0.4 + biology_confidence * 0.1 + li_practice * 0.15 , 3)

        wen_practice = round((scores.get(67, 1) + scores.get(68, 1) + 4) / 3 , 3)
        geography_raw = round(geography_interest * 0.35 + geography_score * 0.4 + geography_confidence * 0.1 + wen_practice * 0.15 , 3)
        politics_raw = round(politics_interest * 0.35 + politics_score * 0.4 + politics_confidence * 0.1 + wen_practice * 0.15 , 3)
        history_raw = round(history_interest * 0.35 + history_score * 0.4 + history_confidence * 0.1 + wen_practice * 0.15 , 3)
    elif tmp == 4:
        li_practice = round((scores.get(65, 1) + scores.get(66, 1) + 4) / 3 , 3)
        physics_raw = round(physics_interest * 0.35 + physics_score * 0.4 + physics_confidence * 0.1 + li_practice * 0.15 , 3)
        chemistry_raw = round(chemistry_interest * 0.35 + chemistry_score * 0.4 + chemistry_confidence * 0.1 + li_practice * 0.15 , 3)
        biology_raw = round(biology_interest * 0.35 + biology_score * 0.4 + biology_confidence * 0.1 + li_practice * 0.15 , 3)

        wen_practice = round((scores.get(67, 1) + scores.get(68, 1)) / 2 , 3)
        geography_raw = round(geography_interest * 0.35 + geography_score * 0.4 + geography_confidence * 0.1 + wen_practice * 0.15 , 3)
        politics_raw = round(politics_interest * 0.35 + politics_score * 0.4 + politics_confidence * 0.1 + wen_practice * 0.15 , 3)
        history_raw = round(history_interest * 0.35 + history_score * 0.4 + history_confidence * 0.1 + wen_practice * 0.15 , 3)
    elif tmp == 5:
        li_practice = round((scores.get(65, 1) + scores.get(66, 1) + 5) / 3 , 3)
        physics_raw = round(physics_interest * 0.35 + physics_score * 0.4 + physics_confidence * 0.1 + li_practice * 0.15 , 3)
        chemistry_raw = round(chemistry_interest * 0.35 + chemistry_score * 0.4 + chemistry_confidence * 0.1 + li_practice * 0.15 , 3)
        biology_raw = round(biology_interest * 0.35 + biology_score * 0.4 + biology_confidence * 0.1 + li_practice * 0.15 , 3)

        wen_practice = round((scores.get(67, 1) + scores.get(68, 1)) / 2 , 3)
        geography_raw = round(geography_interest * 0.35 + geography_score * 0.4 + geography_confidence * 0.1 + wen_practice * 0.15 , 3)
        politics_raw = round(politics_interest * 0.35 + politics_score * 0.4 + politics_confidence * 0.1 + wen_practice * 0.15 , 3)
        history_raw = round(history_interest * 0.35 + history_score * 0.4 + history_confidence * 0.1 + wen_practice * 0.15 , 3)
    else:
        li_practice = round((scores.get(65, 1) + scores.get(66, 1)) / 2 , 3)
        physics_raw = round(physics_interest * 0.35 + physics_score * 0.4 + physics_confidence * 0.1 + li_practice * 0.15 , 3)
        chemistry_raw = round(chemistry_interest * 0.35 + chemistry_score * 0.4 + chemistry_confidence * 0.1 + li_practice * 0.15 , 3)
        biology_raw = round(biology_interest * 0.35 + biology_score * 0.4 + biology_confidence * 0.1 + li_practice * 0.15 , 3)

        wen_practice = round((scores.get(67, 1) + scores.get(68, 1)) / 2 , 3)
        geography_raw = round(geography_interest * 0.35 + geography_score * 0.4 + geography_confidence * 0.1 + wen_practice * 0.15 , 3)
        politics_raw = round(politics_interest * 0.35 + politics_score * 0.4 + politics_confidence * 0.1 + wen_practice * 0.15 , 3)
        history_raw = round(history_interest * 0.35 + history_score * 0.4 + history_confidence * 0.1 + wen_practice * 0.15 , 3)

    raw_scores = {}
    sub_list = ['物理','化学','生物','历史','地理','政治']
    scores_tmp = [physics_raw, chemistry_raw, biology_raw, history_raw, geography_raw, politics_raw]
    i = 0
    for sub in sub_list:
        raw_scores[sub] = scores_tmp[i]
        i += 1
    print(raw_scores)
    # physics_raw = sum_q([1, 2, 3, 4, 29, 30, 31, 32, 33, 59, 25, 26, 28])
    # chemistry_raw = sum_q([5, 6, 7, 8, 34, 35, 36, 37, 38, 59, 25, 26, 27])
    # biology_raw = sum_q([9, 10, 11, 12, 39, 40, 41, 42, 43, 59, 25, 26, 27])
    # geography_raw = sum_q([17, 18, 19, 20, 49, 50, 51, 52, 53, 59, 60, 26, 27])
    # politics_raw = sum_q([21, 22, 23, 24, 54, 55, 56, 57, 58, 60])
    # history_raw = sum_q([13, 14, 15, 16, 44, 45, 46, 47, 48, 60, 27])

    # # 加权总分 = (1-28总分 * 0.4) + (29-60总分 * 0.6)
    # part1_total = sum(scores.get(i, 0) for i in range(1, 29))
    # part2_total = sum(scores.get(i, 0) for i in range(29, 61))
    # weighted_base = part1_total * 0.4 + part2_total * 0.6

    # 这个加权基准用于按比例缩放各科原始分
    # 各科最终得分 = 该科权重分占总权重分的比例 * 加权基准
    ADJ = {
        '物理': ['化学','地理'],
        '化学': ['物理','生物'],
        '生物': ['化学'],
        '地理': ['物理','历史','政治'],
        '历史': ['地理','政治'],
        '政治': ['历史','地理']
    }

    TIER_MAP = {
        ('物理','化学','生物'): 'T1',
        ('物理','化学','地理'): 'T1',
        ('物理','化学','历史'): 'T1',
        ('物理','化学','政治'): 'T1',
        ('地理','历史','政治'): 'T1',
        ('化学','生物','地理'): 'T2',
        ('化学','生物','政治'): 'T2',
        ('物理','生物','地理'): 'T2',
        ('物理','生物','政治'): 'T2',
        ('历史','地理','生物'): 'T2',
        ('历史','政治','生物'): 'T2',
        ('物理','生物','历史'): 'T3',
        ('物理','地理','历史'): 'T3',
        ('物理','地理','政治'): 'T3',
        ('化学','生物','历史'): 'T3',
        ('化学','地理','政治'): 'T3',
        ('生物','地理','政治'): 'T3',
        ('物理','历史','政治'): 'T4',
        ('物理','历史','生物'): 'T4',
        ('物理','政治','生物'): 'T4',
    }
    TIER_BONUS = {'T1':0.15, 'T2':0.10, 'T3':0.05, 'T4':0}

    def get_tier(combo):
        return TIER_MAP.get(tuple(sorted(combo)), 'T4')

    def is_phys_chem(combo):
        return '物理' in combo and '化学' in combo

    def count_edges(combo):
        cnt = 0
        for i in range(3):
            for j in range(i+1, 3):
                if combo[j] in ADJ.get(combo[i], []):
                    cnt += 1
        return cnt
    
    subjects = list(raw_scores.keys())
    combos = list(itertools.combinations(subjects, 3))
    results = []
    for combo in combos:
        total_raw = sum(raw_scores[s] for s in combo)
        tier = get_tier(combo)
        bonus = TIER_BONUS[tier]
        extra = 1.05 if is_phys_chem(combo) else 1.0
        score = total_raw * (1 + bonus) * extra
        results.append({
            'combo': combo,
            'total_raw': round(total_raw, 3),
            'tier': tier,
            'bonus': bonus,
            'extra': extra,
            'score': round(score, 3),
            'edges': count_edges(combo)
        })
    results.sort(key=lambda x: x['score'], reverse=True)
    # print(results)

    recommendation = []
    for i in range(0,3):
        tmp_list = results[i]
        recommendation.extend(tmp_list['combo'])
    session['selected_courses'] = recommendation

    tmp_list = results[0]
    recommendation = tmp_list['combo']
    print(recommendation)
    return jsonify({
        'status': 'ok',
        'results': results,
        'recommendation': recommendation
    })

# @app.route('/get_class', methods=['POST'])
# @login_required
# def get_class():
#     print(recommendation)
#     return jsonify({
#         'status': 'ok',
#         'recommendation': recommendation
#     })


# ---------- Course selection (子页面三, 仅学生) ----------
# @app.route('/course-selection')
# @login_required
# @role_required('student')
# def course_selection():
    # student = Student.query.get(current_user.id)
    # selected = None
    # if student.selected_courses:
    #     selected = student.selected_courses.split(',')
    # return render_template('course_selection.html', selected=selected)


# @app.route('/course-selection/submit', methods=['POST'])
# @login_required
# @role_required('student')
# def course_selection_submit():
#     data = request.get_json()
#     courses = data.get('courses', [])

#     if len(courses) != 3:
#         return jsonify({'status': 'error', 'message': '请选择三门课程。'}), 400
#     if len(set(courses)) != 3:
#         return jsonify({'status': 'error', 'message': '三门课程不能重复。'}), 400

#     valid = {'物理', '化学', '生物', '政治', '历史', '地理'}
#     for c in courses:
#         if c not in valid:
#             return jsonify({'status': 'error', 'message': f'无效的课程: {c}'}), 400

#     student = Student.query.get(current_user.id)
#     student.selected_courses = ','.join(courses)
#     db.session.commit()

#     return jsonify({'status': 'ok', 'message': '选课提交成功！'})


# ---------- Student management (教师) ----------
@app.route('/student-management')
@login_required
@role_required('teacher', 'admin')
def student_management():
    students = Student.query.all()
    return render_template('student_management.html', students=students)


@app.route('/student/add', methods=['POST'])
@login_required
@role_required('teacher', 'admin')
def student_add():
    data = request.get_json()
    class_name = data.get('class_name', '').strip()
    name = data.get('name', '').strip()
    gender = data.get('gender', '').strip()
    student_number = data.get('student_number', '').strip()
    password = data.get('password', '').strip()

    if not all([class_name, name, gender, student_number, password]):
        return jsonify({'status': 'error', 'message': '所有字段均为必填。'}), 400
    if len(student_number) != 8 or not student_number.isdigit():
        return jsonify({'status': 'error', 'message': '学号必须为8位数字。'}), 400
    if Student.query.filter_by(student_number=student_number).first():
        return jsonify({'status': 'error', 'message': '该学号已存在。'}), 400

    student = Student(class_name=class_name, name=name, gender=gender, student_number=student_number)
    student.set_password(password)
    db.session.add(student)
    db.session.commit()
    return jsonify({'status': 'ok', 'message': '学生添加成功。'})


@app.route('/student/edit/<int:sid>', methods=['POST'])
@login_required
@role_required('teacher', 'admin')
def student_edit(sid):
    student = Student.query.get_or_404(sid)
    data = request.get_json()
    student.class_name = data.get('class_name', student.class_name)
    student.name = data.get('name', student.name)
    student.gender = data.get('gender', student.gender)
    student.student_number = data.get('student_number', student.student_number)
    if data.get('selected_courses') is not None:
        student.selected_courses = data.get('selected_courses')
    db.session.commit()
    return jsonify({'status': 'ok', 'message': '学生信息已更新。'})


@app.route('/student/reset-password/<int:sid>', methods=['POST'])
@login_required
@role_required('teacher', 'admin')
def student_reset_password(sid):
    student = Student.query.get_or_404(sid)
    data = request.get_json()
    new_pwd = data.get('new_password', '').strip()
    if len(new_pwd) < 6:
        return jsonify({'status': 'error', 'message': '密码长度不能少于6位。'}), 400
    student.set_password(new_pwd)
    db.session.commit()
    return jsonify({'status': 'ok', 'message': '密码已重置成功。'})


@app.route('/student/delete/<int:sid>', methods=['POST'])
@login_required
@role_required('teacher', 'admin')
def student_delete(sid):
    student = Student.query.get_or_404(sid)
    db.session.delete(student)
    db.session.commit()
    return jsonify({'status': 'ok', 'message': '学生已删除。'})


# ---------- Teacher management (管理员) ----------
@app.route('/admin/teachers')
@login_required
@role_required('admin')
def admin_teachers():
    teachers = Teacher.query.all()
    return render_template('admin_teachers.html', teachers=teachers)


@app.route('/admin/teacher/add', methods=['POST'])
@login_required
@role_required('admin')
def admin_teacher_add():
    data = request.get_json()
    name = data.get('name', '').strip()
    gender = data.get('gender', '').strip()
    employee_id = data.get('employee_id', '').strip()
    password = data.get('password', '').strip()

    if not all([name, gender, employee_id, password]):
        return jsonify({'status': 'error', 'message': '所有字段均为必填。'}), 400
    if Teacher.query.filter_by(employee_id=employee_id).first():
        return jsonify({'status': 'error', 'message': '该教职工号已存在。'}), 400

    teacher = Teacher(name=name, gender=gender, employee_id=employee_id)
    teacher.set_password(password)
    db.session.add(teacher)
    db.session.commit()
    return jsonify({'status': 'ok', 'message': '教师添加成功。'})


@app.route('/admin/teacher/edit/<int:tid>', methods=['POST'])
@login_required
@role_required('admin')
def admin_teacher_edit(tid):
    teacher = Teacher.query.get_or_404(tid)
    data = request.get_json()
    teacher.name = data.get('name', teacher.name)
    teacher.gender = data.get('gender', teacher.gender)
    teacher.employee_id = data.get('employee_id', teacher.employee_id)
    db.session.commit()
    return jsonify({'status': 'ok', 'message': '教师信息已更新。'})


@app.route('/admin/teacher/reset-password/<int:tid>', methods=['POST'])
@login_required
@role_required('admin')
def admin_teacher_reset_password(tid):
    teacher = Teacher.query.get_or_404(tid)
    data = request.get_json()
    new_pwd = data.get('new_password', '').strip()
    if len(new_pwd) < 6:
        return jsonify({'status': 'error', 'message': '密码长度不能少于6位。'}), 400
    teacher.set_password(new_pwd)
    db.session.commit()
    return jsonify({'status': 'ok', 'message': '密码已重置成功。'})


@app.route('/admin/teacher/delete/<int:tid>', methods=['POST'])
@login_required
@role_required('admin')
def admin_teacher_delete(tid):
    teacher = Teacher.query.get_or_404(tid)
    db.session.delete(teacher)
    db.session.commit()
    return jsonify({'status': 'ok', 'message': '教师已删除。'})


# ---------- Guest management (管理员) ----------
@app.route('/admin/guests')
@login_required
@role_required('admin')
def admin_guests():
    guests = Guest.query.all()
    return render_template('admin_guests.html', guests=guests)


@app.route('/admin/guest/add', methods=['POST'])
@login_required
@role_required('admin')
def admin_guest_add():
    data = request.get_json()
    phone = data.get('phone', '').strip()
    password = data.get('password', '').strip()

    if not phone or len(phone) != 11 or not phone.isdigit():
        return jsonify({'status': 'error', 'message': '请输入正确的11位手机号。'}), 400
    if Guest.query.filter_by(phone_number=phone).first():
        return jsonify({'status': 'error', 'message': '该手机号已存在。'}), 400

    guest = Guest(phone_number=phone)
    guest.set_password(password)
    db.session.add(guest)
    db.session.commit()
    return jsonify({'status': 'ok', 'message': '路人添加成功。'})


@app.route('/admin/guest/reset-password/<int:gid>', methods=['POST'])
@login_required
@role_required('admin')
def admin_guest_reset_password(gid):
    guest = Guest.query.get_or_404(gid)
    if guest.phone_number == '11111111112':
        return jsonify({'status': 'error', 'message': '不能在此处修改管理员密码，请使用"修改管理员密码"功能。'}), 400
    data = request.get_json()
    new_pwd = data.get('new_password', '').strip()
    if len(new_pwd) < 6:
        return jsonify({'status': 'error', 'message': '密码长度不能少于6位。'}), 400
    guest.set_password(new_pwd)
    db.session.commit()
    return jsonify({'status': 'ok', 'message': '密码已重置成功。'})


@app.route('/admin/guest/delete/<int:gid>', methods=['POST'])
@login_required
@role_required('admin')
def admin_guest_delete(gid):
    guest = Guest.query.get_or_404(gid)
    if guest.phone_number == '11111111112':
        return jsonify({'status': 'error', 'message': '不能删除超级管理员账号。'}), 400
    db.session.delete(guest)
    db.session.commit()
    return jsonify({'status': 'ok', 'message': '路人已删除。'})


@app.route('/admin/change-password', methods=['POST'])
@login_required
@role_required('admin')
def admin_change_password():
    data = request.get_json()
    old_pwd = data.get('old_password', '')
    new_pwd = data.get('new_password', '')

    if not current_user.check_password(old_pwd):
        return jsonify({'status': 'error', 'message': '原密码错误。'}), 400
    if len(new_pwd) < 6:
        return jsonify({'status': 'error', 'message': '新密码长度不能少于6位。'}), 400

    current_user.set_password(new_pwd)
    db.session.commit()
    return jsonify({'status': 'ok', 'message': '管理员密码修改成功。'})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
