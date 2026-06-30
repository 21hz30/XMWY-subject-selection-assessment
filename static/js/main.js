const XNWY_SUBJECT_STYLES = {
    '物理': { colorClass: 'physics', icon: 'bi-lightning-charge-fill' },
    '化学': { colorClass: 'chemistry', icon: 'bi-beaker-fill' },
    '生物': { colorClass: 'biology', icon: 'bi-flower1' },
    '历史': { colorClass: 'history', icon: 'bi-clock-history' },
    '地理': { colorClass: 'geography', icon: 'bi-globe-asia-australia' },
    '政治': { colorClass: 'politics', icon: 'bi-bank' },
};

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function metricRow(label, score) {
    const width = Math.max(0, Math.min(100, (score / 5) * 100));
    return `
        <div class="metric-row">
            <div class="metric-label">
                <span>${escapeHtml(label)}</span>
                <strong>${score.toFixed(2)}</strong>
            </div>
            <div class="metric-track">
                <div class="metric-fill" style="width:${width}%"></div>
            </div>
        </div>
    `;
}

function subjectPill(subject) {
    const meta = XNWY_SUBJECT_STYLES[subject] || { colorClass: 'history', icon: 'bi-book' };
    return `
        <span class="subject-pill ${meta.colorClass}">
            <i class="bi ${meta.icon}"></i>
            ${escapeHtml(subject)}
        </span>
    `;
}

function comboBadges(combo) {
    return combo.map(subjectPill).join('');
}

function renderReport(container, report) {
    if (!container || !report) return;

    const subjectCards = report.subjects.map((subject) => {
        const metrics = [
            ['学业表现', subject.dimensions.academic],
            ['兴趣倾向', subject.dimensions.interest],
            ['实践经历', subject.dimensions.practice],
            ['学习信心', subject.dimensions.confidence],
        ].map(([label, score]) => metricRow(label, score)).join('');

        return `
            <article class="subject-report-card">
                <div class="subject-report-head">
                    ${subjectPill(subject.name)}
                    <span class="subject-score">综合分 ${subject.raw_score.toFixed(2)}</span>
                </div>
                <p class="subject-reason">${escapeHtml(subject.reason)}</p>
                <div class="metric-stack">${metrics}</div>
            </article>
        `;
    }).join('');

    const rankedScores = report.all_subject_scores.map((item, index) => `
        <div class="scoreboard-row">
            <div class="scoreboard-label">
                <span class="scoreboard-rank">${index + 1}</span>
                ${subjectPill(item.name)}
            </div>
            <div class="scoreboard-track">
                <div class="scoreboard-fill ${item.meta.color}" style="width:${(item.score / 5) * 100}%"></div>
            </div>
            <strong>${item.score.toFixed(2)}</strong>
        </div>
    `).join('');

    const alternatives = report.alternatives.map((item) => `
        <article class="alt-card ${item.rank === 1 ? 'is-top' : ''}">
            <div class="alt-rank">方案 ${item.rank}</div>
            <div class="alt-badges">${comboBadges(item.combo)}</div>
            <div class="alt-meta">
                <span>${escapeHtml(item.tier_label)}</span>
                <span>推荐分 ${item.score.toFixed(2)}</span>
                <span>${item.has_phys_chem ? '含物化双选' : '不含物化双选'}</span>
            </div>
            <p class="alt-summary">${escapeHtml(item.summary)}</p>
        </article>
    `).join('');

    container.innerHTML = `
        <section class="report-hero">
            <div class="report-hero-main">
                <div class="report-kicker">最推荐方案</div>
                <h3>${comboBadges(report.top_combo)}</h3>
                <p class="report-summary">${escapeHtml(report.hero_summary)}</p>
            </div>
            <div class="report-hero-side">
                <div class="report-stat">
                    <span>推荐分</span>
                    <strong>${report.top_score.toFixed(2)}</strong>
                </div>
                <div class="report-stat">
                    <span>组合层级</span>
                    <strong>${escapeHtml(report.tier_label)}</strong>
                </div>
                <div class="report-stat">
                    <span>关联边数</span>
                    <strong>${report.edges}</strong>
                </div>
            </div>
        </section>

        <section class="report-grid">
            <article class="report-panel">
                <div class="panel-title">为什么推荐这几门</div>
                <p>${escapeHtml(report.combo_summary)}</p>
                <p class="mb-0">${escapeHtml(report.warning)}</p>
            </article>
            <article class="report-panel">
                <div class="panel-title">组合合理性</div>
                <ul class="report-list">
                    <li>系统先按兴趣、成绩、实践、信心四个维度计算单科综合分，再枚举全部组合排序。</li>
                    <li>${report.has_phys_chem ? '这组方案包含物理+化学，专业覆盖安全边界更稳。' : '这组方案不含物化双选，因此系统会同步展示覆盖面提醒。'}</li>
                    <li>你当前最优解不是单看某一科高分，而是综合个人匹配度与组合覆盖面后的结果。</li>
                </ul>
            </article>
        </section>

        <section class="report-section">
            <div class="section-head">
                <h5>三门学科的推荐理由</h5>
                <p>每门学科都拆开看，避免“只知道结果，不知道为什么”。</p>
            </div>
            <div class="subject-report-grid">${subjectCards}</div>
        </section>

        <section class="report-section">
            <div class="section-head">
                <h5>六科学科画像</h5>
                <p>这是系统对你六门学科综合匹配度的排序。</p>
            </div>
            <div class="scoreboard">${rankedScores}</div>
        </section>

        <section class="report-section">
            <div class="section-head">
                <h5>备选组合对比</h5>
                <p>除了第一方案，也把第二、第三方案保留下来，方便你和家长老师一起比较。</p>
            </div>
            <div class="alt-grid">${alternatives}</div>
        </section>
    `;
}

window.XNWYReport = { renderReport };

document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach((alert) => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    if (csrfMeta) {
        const csrfToken = csrfMeta.getAttribute('content');
        const originalFetch = window.fetch;
        window.fetch = function(url, options = {}) {
            if (options.method && ['POST', 'PUT', 'DELETE', 'PATCH'].includes(options.method.toUpperCase())) {
                options.headers = options.headers || {};
                if (!options.headers['X-CSRFToken'] && !options.headers['x-csrftoken']) {
                    options.headers['X-CSRFToken'] = csrfToken;
                }
            }
            return originalFetch(url, options);
        };
    }
});
