from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class Users(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(50), nullable=False, default='user')  # Default role is 'user'
    licenses = db.relationship('License', backref='user', lazy=True)  # Quan hệ 1-n với License

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class License(db.Model):
    __tablename__ = 'licenses'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    license_key = db.Column(db.String(255), unique=True, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='UnActive')
    issued_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime, nullable=True)
    package = db.Column(db.String(50), nullable=False)
    camera_count = db.Column(db.Integer, nullable=False, default=0)
    history = db.Column(db.JSON, nullable=False, default=[])

