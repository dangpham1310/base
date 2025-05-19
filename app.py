from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from routes.authentication import auth_bp
from routes.camera import camera_bp
from routes.detected_object import detected_object_bp
from models import db, Users
from config import Config
from flasgger import Swagger
from routes.blacklist import blacklist_bp
from routes.webhook import webhook_bp
app = Flask(__name__)
app.config.from_object(Config)

# Cấu hình Swagger
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,  # all in
            "model_filter": lambda tag: True,  # all in
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
    "openapi": "3.0.2"
}

swagger_template = {
    "openapi": "3.0.2",
    "info": {
        "title": "Flask API",
        "description": "API Documentation using Swagger",
        "version": "1.0.0",
        "contact": {
            "name": "API Support",
            "url": "https://api.tandoan.asia",
        }
    },
    "components": {
        "securitySchemes": {
            "Bearer": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            }
        }
    },
    "security": [
        {
            "Bearer": []
        }
    ]
}

swagger = Swagger(app, template=swagger_template, config=swagger_config)

# Khởi tạo SQLAlchemy
db.init_app(app)

# Khởi tạo Flask-Migrate
migrate = Migrate(app, db)

# Khởi tạo JWTManager
jwt = JWTManager(app)

# Callback để lấy user từ JWT token
@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    return Users.query.filter_by(email=identity).first()

# Đăng ký Blueprint
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(camera_bp, url_prefix='/camera')
app.register_blueprint(detected_object_bp, url_prefix='/detected_object')
app.register_blueprint(blacklist_bp, url_prefix='/blacklist')
app.register_blueprint(webhook_bp, url_prefix='/webhook')
# Tạo database khi chạy ứng dụng
with app.app_context():
    db.create_all()
    
@app.route('/api/hello', methods=['GET'])
def hello():
    """
    Hello World API endpoint
    ---
    get:
      tags:
        - Hello World
      summary: Hello World endpoint
      description: Returns a simple hello world message
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                type: object
                properties:
                  message:
                    type: string
                    example: Hello, World!
    """
    return {"message": "Hello, World!"}

if __name__ == '__main__':
    app.run(debug=True,port=5000,host='0.0.0.0')
