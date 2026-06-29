from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Student(UserMixin, db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    class_name = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    gender = db.Column(db.String(4), nullable=False)
    student_number = db.Column(db.String(8), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    selected_courses = db.Column(db.String(50), nullable=True, default=None)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_role(self):
        return 'student'

    def get_id(self):
        return f'student_{self.id}'


class Teacher(UserMixin, db.Model):
    __tablename__ = 'teachers'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    gender = db.Column(db.String(4), nullable=False)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_role(self):
        return 'teacher'

    def get_id(self):
        return f'teacher_{self.id}'