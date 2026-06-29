import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def default_database_path():
    if os.environ.get('VERCEL'):
        return '/tmp/xuanke.db'
    return os.path.join(BASE_DIR, 'xuanke.db')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'xinanweiyu-xuanke-2024-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f'sqlite:///{default_database_path()}')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
