from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from uuid import uuid4

def utc7now():
    """Return current UTC+7 time"""
    return datetime.utcnow() + timedelta(hours=7)

db = SQLAlchemy()

class Users(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(50), nullable=False, default='user')  # Default role is 'user'


    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class Camera(db.Model):
    __tablename__ = "cameras"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    stream_id = db.Column(db.String(255),unique=True, nullable=False)
    stream_url = db.Column(db.String(255), nullable=False)
    stream_name = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255), nullable=True)
    zone = db.Column(db.JSON, nullable=True)
    max_tracking_time = db.Column(db.Float, default=0)
    config_json = db.Column(db.JSON, nullable=True)
    # status: 1 - active, 0 - inactive, 2 - deleted
    status = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=utc7now, nullable=False)
    updated_at = db.Column(db.DateTime, default=utc7now, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    
    # Relationship với DetectedObject

    detected_objects = db.relationship('DetectedObject', back_populates='camera', lazy=True)

class DetectedObject(db.Model):
    __tablename__ = "detected_objects"
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid4)
    id_camera = db.Column(db.Integer, db.ForeignKey("cameras.id"), index=True, nullable=False)
    stream_id = db.Column(db.String(255), nullable=False)
    frame_id = db.Column(db.String(255), nullable=False)
    bbox = db.Column(db.JSON)
    license_plate = db.Column(db.String(255), nullable=True)
    time_created = db.Column(db.DateTime, default=utc7now, nullable=False)
    
    # Relationships
    camera = db.relationship("Camera", back_populates="detected_objects")


class BlackList(db.Model):
    __tablename__ = "black_lists"
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid4)
    license_plate = db.Column(db.String(255), nullable=False)
    time_created = db.Column(db.DateTime, default=utc7now, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    note = db.Column(db.String(255), nullable=True)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)




class WebHook(db.Model):
    __tablename__ = "web_hooks"
    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    key = db.Column(db.String(255), nullable=False)
    typeweb = db.Column(db.String(255), nullable=False, default="Telegram")
    time_created = db.Column(db.DateTime, default=utc7now, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    
    
    

class UserCamera(db.Model):
    __tablename__ = "user_camera"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    camera_id = db.Column(db.Integer, db.ForeignKey("cameras.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utc7now, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'camera_id', name='uix_user_camera'),
    )

    user = db.relationship("Users", backref=db.backref("user_cameras", lazy=True))
    camera = db.relationship("Camera", backref=db.backref("user_cameras", lazy=True))




