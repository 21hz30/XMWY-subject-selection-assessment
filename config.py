import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ENV_FILE = os.path.join(BASE_DIR, '.env')


def load_local_env():
    if not os.path.exists(ENV_FILE):
        return

    with open(ENV_FILE, 'r', encoding='utf-8') as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue

            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()

            if value and len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]

            os.environ.setdefault(key, value)


load_local_env()


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}

def default_database_path():
    if os.environ.get('VERCEL'):
        return '/tmp/xuanke.db'
    return os.path.join(BASE_DIR, 'xuanke.db')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'xinanweiyu-xuanke-2024-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f'sqlite:///{default_database_path()}')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', os.environ.get('OPENAI_API_KEY', ''))
    DEEPSEEK_BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', os.environ.get('OPENAI_BASE_URL', 'https://api.deepseek.com/v1'))
    DEEPSEEK_MODEL = os.environ.get('DEEPSEEK_MODEL', os.environ.get('OPENAI_MODEL', 'deepseek-chat'))
    DEEPSEEK_TIMEOUT_SECONDS = float(os.environ.get('DEEPSEEK_TIMEOUT_SECONDS', os.environ.get('OPENAI_TIMEOUT_SECONDS', '20')))
    DEEPSEEK_SSL_VERIFY = env_bool('DEEPSEEK_SSL_VERIFY', True)
