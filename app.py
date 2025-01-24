from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from routes.authentication import auth_bp
from models import db
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Khởi tạo SQLAlchemy
db.init_app(app)

# Khởi tạo JWTManager
jwt = JWTManager(app)

# Đăng ký Blueprint
app.register_blueprint(auth_bp, url_prefix='/auth')

# Tạo database khi chạy ứng dụng
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
