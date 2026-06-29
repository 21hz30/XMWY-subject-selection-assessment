// 全局工具函数
document.addEventListener('DOMContentLoaded', function() {
    // 自动隐藏 flash 消息
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // CSRF token 设置（所有 AJAX 请求自动携带）
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    if (csrfMeta) {
        const csrfToken = csrfMeta.getAttribute('content');
        // 重写 fetch 以自动添加 CSRF
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
