# -*- coding: utf-8 -*-
from flask import Flask, render_template, request
import itertools

app = Flask(__name__)

# ============================================================
#  工具函数
# ============================================================

def avg(lst):
    return round(sum(lst) / len(lst), 3) if lst else 0

def clamp(v, lo=1, hi=5):
    return max(lo, min(hi, v))


# ============================================================
#  核心算法：计算各学科 raw_score
# ============================================================

def compute_raw_scores(data):
    """
    data: dict，键为 '1'~'69'，值为 1~5 的整数
    返回: dict {学科: raw_score}
    """

    # ---------- 1. 兴趣原始平均分 ----------
    interest_qs = {
        '物理': [1,2,3,4],
        '化学': [5,6,7,8],
        '生物': [9,10,11,12],
        '历史': [13,14,15,16],
        '地理': [17,18,19,20],
        '政治': [21,22,23,24]
    }
    raw_interest = {}
    for sub, qs in interest_qs.items():
        raw_interest[sub] = avg([data[str(q)] for q in qs])

    # ---------- 2. 跨学科修正（乘法，取最高系数） ----------
    # 25、26：双向修正
    # 27、28：单向修正（地生）
    coeff_rules = {
        '25': {5:1.2, 4:1.1, 2:1.1, 1:1.2},
        '26': {5:1.2, 4:1.1, 2:1.1, 1:1.2},
        '27': {5:1.2, 4:1.1},
        '28': {5:1.2, 4:1.1},
    }
    coeff = {sub: 1.0 for sub in interest_qs}

    for qid in ['25','26']:
        sc = data[qid]
        if sc in coeff_rules[qid]:
            val = coeff_rules[qid][sc]
            if sc >= 4:
                for sub in ['物理','化学','生物']:
                    coeff[sub] = max(coeff[sub], val)
            elif sc <= 2:
                for sub in ['历史','地理','政治']:
                    coeff[sub] = max(coeff[sub], val)

    for qid in ['27','28']:
        sc = data[qid]
        if sc in coeff_rules[qid]:
            val = coeff_rules[qid][sc]
            for sub in ['地理','生物']:
                coeff[sub] = max(coeff[sub], val)

    final_interest = {}
    for sub in interest_qs:
        final_interest[sub] = clamp(raw_interest[sub] * coeff[sub])

    # ---------- 3. 学业成绩（29-58） ----------
    academic_qs = {
        '物理': list(range(29,34)),
        '化学': list(range(34,39)),
        '生物': list(range(39,44)),
        '历史': list(range(44,49)),
        '地理': list(range(49,54)),
        '政治': list(range(54,59))
    }
    academic = {}
    for sub, qs in academic_qs.items():
        academic[sub] = avg([data[str(q)] for q in qs])

    # ---------- 4. 学习信心（59-64） ----------
    sub_list = ['物理','化学','生物','历史','地理','政治']
    confidence = {}
    for i, sub in enumerate(sub_list):
        confidence[sub] = data[str(59+i)]

    # ---------- 5. 实践经历（65-69） ----------
    # 原始分
    practice_sci_raw = (data['65'] + data['66']) / 2
    practice_hum_raw = (data['67'] + data['68']) / 2

    # 第69题修正
    q69 = data['69']
    practice_sci = practice_sci_raw
    practice_hum = practice_hum_raw
    if q69 == 1:
        practice_hum = (data['67'] + data['68'] + 5) / 3
    elif q69 == 2:
        practice_hum = (data['67'] + data['68'] + 4) / 3
    elif q69 == 4:
        practice_sci = (data['65'] + data['66'] + 4) / 3
    elif q69 == 5:
        practice_sci = (data['65'] + data['66'] + 5) / 3
    # q69 == 3 不修正

    practice = {}
    for sub in ['物理','化学','生物']:
        practice[sub] = clamp(practice_sci)
    for sub in ['历史','地理','政治']:
        practice[sub] = clamp(practice_hum)

    # ---------- 6. raw_score = 成绩×0.4 + 兴趣×0.35 + 实践×0.15 + 信心×0.10 ----------
    raw_scores = {}
    for sub in sub_list:
        raw_scores[sub] = round(
            academic[sub] * 0.4 +
            final_interest[sub] * 0.35 +
            practice[sub] * 0.15 +
            confidence[sub] * 0.10,
            3
        )
    return raw_scores


# ============================================================
#  学科关联图 & 推荐计算
# ============================================================

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

def recommend(raw_scores):
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
    return results


# ============================================================
#  Flask 路由
# ============================================================

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        data = {}
        for i in range(1, 70):
            key = str(i)
            val = request.form.get(key)
            data[key] = int(val) if val else 3
        raw_scores = compute_raw_scores(data)
        recs = recommend(raw_scores)
        return render_template('result.html',
                               raw_scores=raw_scores,
                               recommendations=recs[:6])
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)