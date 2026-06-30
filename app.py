import itertools
import json
import random
import ssl
import urllib.error
import urllib.request
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from config import Config
from models import db, Student, Teacher

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

SUBJECT_ORDER = ['物理', '化学', '生物', '历史', '地理', '政治']
SUBJECT_RANK = {subject: index for index, subject in enumerate(SUBJECT_ORDER)}
SUBJECT_META = {
    '物理': {'icon': 'bi-lightning-charge-fill', 'color': 'physics'},
    '化学': {'icon': 'bi-eyedropper', 'color': 'chemistry'},
    '生物': {'icon': 'bi-flower1', 'color': 'biology'},
    '历史': {'icon': 'bi-clock-history', 'color': 'history'},
    '地理': {'icon': 'bi-globe-asia-australia', 'color': 'geography'},
    '政治': {'icon': 'bi-bank', 'color': 'politics'},
}

DIMENSION_LABELS = {
    'academic': '学业表现',
    'interest': '兴趣倾向',
    'practice': '实践经历',
    'confidence': '学习信心',
}

TIER_COPY = {
    'T1': {
        'label': '高覆盖组合',
        'summary': '这一组合位于高覆盖梯队，在大学专业报考范围和组合稳定性上都更占优。',
    },
    'T2': {
        'label': '均衡组合',
        'summary': '这一组合兼顾个人优势与专业覆盖，属于可持续发展的稳健选择。',
    },
    'T3': {
        'label': '边缘可选组合',
        'summary': '这一组合可以成立，但部分专业方向会明显收窄，需要结合目标专业谨慎判断。',
    },
    'T4': {
        'label': '高风险组合',
        'summary': '这一组合专业覆盖面较窄，系统会保留结果但会明确提示其风险。',
    },
}

COMBO_NOTES = {
    ('物理', '化学', '生物'): '传统理科路径最完整，对理工、医学与生命科学方向都较友好。',
    ('物理', '化学', '地理'): '保留理工主干，同时兼顾地理信息、城乡规划与空间分析方向。',
    ('物理', '化学', '历史'): '在保住理工覆盖面的同时，为历史、社科与综合评价方向留出弹性。',
    ('物理', '化学', '政治'): '既保留理工基础，也兼顾法学、公安学类和公共事务相关方向。',
    ('历史', '地理', '政治'): '纯文综覆盖完整，更适合目标明确偏向人文社科的学生。',
    ('化学', '生物', '地理'): '适合医药、环境与地理交叉兴趣较强，但不强求物理路径的学生。',
    ('化学', '生物', '政治'): '兼顾医药生物基础与公共议题兴趣，适合方向较综合的学生。',
    ('物理', '生物', '地理'): '有物理基础，但由于缺少化学，理工农医专业覆盖会受限。',
    ('物理', '生物', '政治'): '保留物理逻辑优势，同时体现社会议题兴趣，但专业口径不如物化双选宽。',
    ('历史', '地理', '生物'): '文理混合特征明显，适合兴趣跨度较大的学生。',
    ('历史', '政治', '生物'): '兼顾生命科学兴趣与人文表达能力，适合跨学科取向学生。',
    ('物理', '生物', '历史'): '个人兴趣可以支撑，但缺少化学会显著限制大量理工方向。',
    ('物理', '地理', '历史'): '空间分析与人文理解较强，但理工专业报考面明显收窄。',
    ('物理', '地理', '政治'): '对地理与公共议题有优势，但理工主线不如物化双选稳定。',
    ('化学', '生物', '历史'): '保留化生优势，适合生命科学兴趣明确、同时偏好人文阅读的学生。',
    ('化学', '地理', '政治'): '兼顾资源环境、地理与公共议题，但缺物理会影响多数工科方向。',
    ('生物', '地理', '政治'): '更适合兴趣明显偏综合文理、且接受专业覆盖收窄的学生。',
    ('物理', '历史', '政治'): '该组合不利于形成稳定的专业覆盖面，建议慎重选择。',
}

ADJ = {
    '物理': ['化学', '地理'],
    '化学': ['物理', '生物'],
    '生物': ['化学'],
    '地理': ['物理', '历史', '政治'],
    '历史': ['地理', '政治'],
    '政治': ['历史', '地理']
}

TIER_MAP = {
    ('物理', '化学', '生物'): 'T1',
    ('物理', '化学', '地理'): 'T1',
    ('物理', '化学', '历史'): 'T1',
    ('物理', '化学', '政治'): 'T1',
    ('地理', '历史', '政治'): 'T1',
    ('化学', '生物', '地理'): 'T2',
    ('化学', '生物', '政治'): 'T2',
    ('物理', '生物', '地理'): 'T2',
    ('物理', '生物', '政治'): 'T2',
    ('历史', '地理', '生物'): 'T2',
    ('历史', '政治', '生物'): 'T2',
    ('物理', '生物', '历史'): 'T3',
    ('物理', '地理', '历史'): 'T3',
    ('物理', '地理', '政治'): 'T3',
    ('化学', '生物', '历史'): 'T3',
    ('化学', '地理', '政治'): 'T3',
    ('生物', '地理', '政治'): 'T3',
    ('物理', '历史', '政治'): 'T4',
    ('物理', '历史', '生物'): 'T4',
    ('物理', '政治', '生物'): 'T4',
}

TIER_BONUS = {'T1': 0.15, 'T2': 0.10, 'T3': 0.05, 'T4': 0}


def normalize_combo(combo):
    return tuple(sorted(combo, key=lambda subject: SUBJECT_RANK[subject]))


COMBO_NOTES = {normalize_combo(key): value for key, value in COMBO_NOTES.items()}
TIER_MAP = {normalize_combo(key): value for key, value in TIER_MAP.items()}


def get_tier(combo):
    return TIER_MAP.get(normalize_combo(combo), 'T4')


def is_phys_chem(combo):
    return '物理' in combo and '化学' in combo


def count_edges(combo):
    cnt = 0
    for i in range(3):
        for j in range(i + 1, 3):
            if combo[j] in ADJ.get(combo[i], []):
                cnt += 1
    return cnt


def subject_reason(subject, profile):
    ranking = sorted(profile['dimensions'].items(), key=lambda item: item[1], reverse=True)
    lead_key, lead_score = ranking[0]
    second_key, second_score = ranking[1]
    lead_label = DIMENSION_LABELS[lead_key]
    second_label = DIMENSION_LABELS[second_key]

    snippets = []
    if lead_key == 'academic':
        snippets.append(f"{subject}的{lead_label}最突出，说明你在这门课上的成绩基础和稳定性更能支撑长期学习。")
    elif lead_key == 'interest':
        snippets.append(f"{subject}的{lead_label}最强，说明你不是只会做题，而是真的愿意持续投入这门学科。")
    elif lead_key == 'practice':
        snippets.append(f"{subject}的{lead_label}表现亮眼，相关活动、竞赛或课题经历为这门学科提供了额外支持。")
    else:
        snippets.append(f"{subject}的{lead_label}较高，说明你对后续学习难度和节奏有比较稳定的心理预期。")

    if second_score >= 3.8:
        snippets.append(f"同时，{second_label}也处在较高水平，这让它不仅适合当前，也更适合作为长期选科。")
    elif profile['raw_score'] >= 4.0:
        snippets.append("综合分保持在高位，说明这不是单一维度拉起来的结果，而是整体匹配度较好。")
    else:
        snippets.append("它未必是最轻松的一门，但从综合表现看，仍然值得放进你的优先选择里。")

    return ''.join(snippets)


def combo_warning(combo, tier):
    combo_set = set(combo)
    if tier == 'T4':
        return '该组合专业覆盖率偏低，尤其对理工农医方向限制明显，系统不建议作为优先方案。'
    if '物理' in combo_set and '化学' not in combo_set:
        return '该组合包含物理但缺少化学。按照文档思路，这会明显压缩大量理工农医专业的报考空间。'
    if combo_set == {'历史', '地理', '政治'}:
        return '这是纯文综组合，人文社科覆盖完整，但绝大多数理工农医专业将不再可选。'
    if '化学' in combo_set and '物理' not in combo_set:
        return '该组合保留了部分化学、生物相关方向，但缺少物理后，多数工科路径会明显收窄。'
    return '这组方案整体风险可控，但最终仍建议结合目标大学和目标专业再做一次核对。'


def parse_json_object(text):
    cleaned = text.strip()
    if cleaned.startswith('```'):
        parts = cleaned.split('```')
        cleaned = ''.join(part for part in parts if not part.strip().startswith('json')).strip()
    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError:
        return None


def extract_response_text(payload):
    if isinstance(payload.get('output_text'), str) and payload['output_text'].strip():
        return payload['output_text'].strip()

    chunks = []
    for item in payload.get('output', []):
        for content in item.get('content', []):
            text = content.get('text')
            if text:
                chunks.append(text)
    return '\n'.join(chunks).strip()


def extract_chat_completion_text(payload):
    choices = payload.get('choices', [])
    if not choices:
        return ''
    message = choices[0].get('message', {})
    content = message.get('content', '')
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        chunks = []
        for item in content:
            if isinstance(item, dict) and item.get('text'):
                chunks.append(item['text'])
        return '\n'.join(chunks).strip()
    return ''


def post_json(url, payload, timeout, ssl_context, api_key):
    request_obj = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    with urllib.request.urlopen(
        request_obj,
        timeout=timeout,
        context=ssl_context,
    ) as response:
        return json.loads(response.read().decode('utf-8'))


def generate_llm_report_copy(report_payload, raw_scores, subject_profiles):
    api_key = app.config.get('DEEPSEEK_API_KEY')
    if not api_key:
        return report_payload

    top_subjects = []
    for subject in report_payload['subjects']:
        profile = subject_profiles[subject['name']]
        top_subjects.append({
            'subject': subject['name'],
            'raw_score': subject['raw_score'],
            'academic': profile['dimensions']['academic'],
            'interest': profile['dimensions']['interest'],
            'practice': profile['dimensions']['practice'],
            'confidence': profile['dimensions']['confidence'],
        })

    prompt_payload = {
        'top_combo': report_payload['top_combo'],
        'tier': report_payload['tier'],
        'tier_label': report_payload['tier_label'],
        'top_score': report_payload['top_score'],
        'has_phys_chem': report_payload['has_phys_chem'],
        'warning_seed': report_payload['warning'],
        'ranked_subject_scores': raw_scores,
        'top_subject_breakdown': top_subjects,
        'alternatives': report_payload['alternatives'],
    }

    system_prompt = (
        '你是一名熟悉上海新高考选科逻辑的资深升学顾问。'
        '请根据结构化数据，为高中生生成简洁、可信、具体的中文解释。'
        '不要写套话，不要提“模型”或“AI”，不要编造专业覆盖率数字。'
        '请严格只输出 JSON 对象，包含 hero_summary、combo_summary、warning 三个字段。'
    )
    user_prompt = (
        '请为“最推荐方案”生成文案。\n'
        '要求：\n'
        '1. hero_summary：45-90字，适合放在顶部摘要区，语气明确。\n'
        '2. combo_summary：90-160字，说明为什么推荐这个组合，重点结合学生优势和组合结构。\n'
        '3. warning：40-90字，给出温和但明确的风险提醒。\n'
        '4. 必须基于输入数据，避免空泛赞美。\n'
        '5. 输出必须是合法 JSON。\n\n'
        f'数据：{json.dumps(prompt_payload, ensure_ascii=False)}'
    )

    responses_payload = {
        'model': app.config.get('DEEPSEEK_MODEL'),
        'input': [
            {
                'role': 'system',
                'content': [{'type': 'input_text', 'text': system_prompt}],
            },
            {
                'role': 'user',
                'content': [{'type': 'input_text', 'text': user_prompt}],
            },
        ],
    }
    chat_payload = {
        'model': app.config.get('DEEPSEEK_MODEL'),
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        'temperature': 0.7,
    }
    base_url = app.config.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1').rstrip('/')
    ssl_context = None
    if not app.config.get('DEEPSEEK_SSL_VERIFY', True):
        ssl_context = ssl._create_unverified_context()

    llm_text = ''
    try:
        response_payload = post_json(
            f'{base_url}/responses',
            responses_payload,
            app.config.get('DEEPSEEK_TIMEOUT_SECONDS', 20),
            ssl_context,
            api_key,
        )
        llm_text = extract_response_text(response_payload)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        try:
            response_payload = post_json(
                f'{base_url}/chat/completions',
                chat_payload,
                app.config.get('DEEPSEEK_TIMEOUT_SECONDS', 20),
                ssl_context,
                api_key,
            )
            llm_text = extract_chat_completion_text(response_payload)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
            return report_payload

    parsed = parse_json_object(llm_text)
    if not parsed:
        return report_payload

    enriched = dict(report_payload)
    hero_summary = parsed.get('hero_summary', '').strip()
    combo_summary = parsed.get('combo_summary', '').strip()
    warning = parsed.get('warning', '').strip()

    if hero_summary:
        enriched['hero_summary'] = hero_summary
    if combo_summary:
        enriched['combo_summary'] = combo_summary
    if warning:
        enriched['warning'] = warning
    return enriched


def build_report_payload(raw_scores, subject_profiles, results):
    ranked_subjects = sorted(raw_scores.items(), key=lambda item: item[1], reverse=True)
    top_results = results[:3]
    best = top_results[0]
    combo = list(best['combo'])
    best_sorted_subjects = sorted(combo, key=lambda subject: raw_scores[subject], reverse=True)
    tier_info = TIER_COPY[best['tier']]

    report_subjects = []
    for subject in best_sorted_subjects:
        profile = subject_profiles[subject]
        report_subjects.append({
            'name': subject,
            'raw_score': profile['raw_score'],
            'meta': SUBJECT_META[subject],
            'dimensions': profile['dimensions'],
            'reason': subject_reason(subject, profile),
        })

    alternatives = []
    for index, item in enumerate(top_results, start=1):
        sorted_combo = normalize_combo(item['combo'])
        alternatives.append({
            'rank': index,
            'combo': list(item['combo']),
            'score': item['score'],
            'tier': item['tier'],
            'tier_label': TIER_COPY[item['tier']]['label'],
            'summary': COMBO_NOTES.get(sorted_combo, TIER_COPY[item['tier']]['summary']),
            'has_phys_chem': is_phys_chem(item['combo']),
        })

    report_card_subjects = sorted(
        [
            {
                'name': subject,
                'score': score,
                'meta': SUBJECT_META[subject],
            }
            for subject, score in ranked_subjects
        ],
        key=lambda item: item['score'],
        reverse=True,
    )

    summary = '这组推荐同时考虑了你的单科综合得分与组合覆盖面。'
    if is_phys_chem(combo):
        summary += '它保住了“物理+化学”这一核心组合，因此在专业选择的安全边界上更稳。'
    else:
        summary += '虽然它不包含物化双选，但在你的个人优势分布下，仍然具备成立理由。'

    report_payload = {
        'top_combo': combo,
        'top_score': best['score'],
        'tier': best['tier'],
        'tier_label': tier_info['label'],
        'hero_summary': summary,
        'combo_summary': COMBO_NOTES.get(normalize_combo(combo), tier_info['summary']),
        'warning': combo_warning(combo, best['tier']),
        'has_phys_chem': is_phys_chem(combo),
        'edges': best['edges'],
        'subjects': report_subjects,
        'all_subject_scores': report_card_subjects,
        'alternatives': alternatives,
    }
    return generate_llm_report_copy(report_payload, raw_scores, subject_profiles)


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
        report_data = session.get('report_data')
        return render_template('dashboard.html', role=role, report_data=report_data)
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
    subject_profiles = {}
    i = 0
    for sub in sub_list:
        raw_scores[sub] = scores_tmp[i]
        i += 1

    subject_profiles = {
        '物理': {
            'raw_score': physics_raw,
            'dimensions': {
                'academic': physics_score,
                'interest': round(physics_interest, 3),
                'practice': li_practice,
                'confidence': physics_confidence,
            },
        },
        '化学': {
            'raw_score': chemistry_raw,
            'dimensions': {
                'academic': chemistry_score,
                'interest': round(chemistry_interest, 3),
                'practice': li_practice,
                'confidence': chemistry_confidence,
            },
        },
        '生物': {
            'raw_score': biology_raw,
            'dimensions': {
                'academic': biology_score,
                'interest': round(biology_interest, 3),
                'practice': li_practice,
                'confidence': biology_confidence,
            },
        },
        '历史': {
            'raw_score': history_raw,
            'dimensions': {
                'academic': history_score,
                'interest': round(history_interest, 3),
                'practice': wen_practice,
                'confidence': history_confidence,
            },
        },
        '地理': {
            'raw_score': geography_raw,
            'dimensions': {
                'academic': geography_score,
                'interest': round(geography_interest, 3),
                'practice': wen_practice,
                'confidence': geography_confidence,
            },
        },
        '政治': {
            'raw_score': politics_raw,
            'dimensions': {
                'academic': politics_score,
                'interest': round(politics_interest, 3),
                'practice': wen_practice,
                'confidence': politics_confidence,
            },
        },
    }
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
    report_payload = build_report_payload(raw_scores, subject_profiles, results)
    session['report_data'] = report_payload
    return jsonify({
        'status': 'ok',
        'results': results,
        'recommendation': recommendation,
        'report': report_payload
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
