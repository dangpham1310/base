from flask import Blueprint, jsonify, request, Response
from models import Users, db
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import re
from datetime import datetime, timedelta
from flask import current_app
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

# Biến toàn cục lưu trạng thái online
online_users = {}
ONLINE_TIMEOUT_SECONDS = 60  # Thời gian timeout để coi là offline

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    # Kiểm tra các trường cần thiết
    email = data.get("email")
    password = data.get("password")
    name = data.get("name")
    phone = data.get("phone")

    if not all([email, password, name, phone]):
        return jsonify({"message": "Name, email, password, and phone are required"}), 400

    # Kiểm tra định dạng email
    if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email):
        return jsonify({"message": "Invalid email format"}), 400

    # Kiểm tra mật khẩu đủ mạnh
    if len(password) < 6:
        return jsonify({"message": "Password must be at least 6 characters long"}), 400

    # Kiểm tra số điện thoại
    if not re.match(r'^\+?[0-9]{10,15}$', phone):
        return jsonify({"message": "Invalid phone number format"}), 400

    # Kiểm tra email đã tồn tại
    existing_user = Users.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"message": "User with this email already exists"}), 400

    # Tạo người dùng mới
    new_user = Users(email=email, name=name, phone=phone)
    new_user.set_password(password)  # Hash mật khẩu
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
 
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = Users.query.filter_by(email=email).first()

    if user and user.check_password(password):
        # Tạo access token
        access_token = create_access_token(identity=user.email)
        print(access_token)
        return jsonify({"access_token": access_token}), 200

    return jsonify({"message": "Invalid credentials"}), 401

@auth_bp.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify({"message": f"Welcome {current_user}!"}), 200

@auth_bp.route('/online', methods=['POST'])
@jwt_required()
def online():
    current_user = get_jwt_identity()
    now = datetime.utcnow()
    online_users[current_user] = now
    return jsonify({"message": f"{current_user} is online"}), 200

@auth_bp.route('/is_online/<email>', methods=['GET'])
def is_online(email):
    """
    Kiểm tra trạng thái online của user qua email
    ---
    get:
      tags:
        - Authentication
      summary: Kiểm tra trạng thái online của user
      description: |
        Kiểm tra xem user với email chỉ định có đang online không.  
        Trả về true nếu user còn hoạt động trong khoảng thời gian timeout, ngược lại trả về false.
      parameters:
        - in: path
          name: email
          required: true
          schema:
            type: string
          description: Email của user cần kiểm tra trạng thái online
      responses:
        '200':
          description: Trạng thái online của user
          content:
            application/json:
              schema:
                type: object
                properties:
                  email:
                    type: string
                    example: testuser@example.com
                  online:
                    type: boolean
                    example: true
    """
    now = datetime.utcnow()
    last_ping = online_users.get(email)
    if last_ping and (now - last_ping) < timedelta(seconds=ONLINE_TIMEOUT_SECONDS):
        return jsonify({"email": email, "online": True}), 200
    return jsonify({"email": email, "online": False}), 200

@auth_bp.route('/stream_online', methods=['GET'])
@jwt_required()
def stream_online():
    """
    Stream trạng thái online của user hiện tại (SSE)
    ---
    get:
      tags:
        - Authentication
      summary: Stream trạng thái online của user hiện tại
      description: |
        Kết nối tới endpoint này để nhận stream trạng thái online của user hiện tại.  
        Server sẽ gửi ping mỗi 5 giây với thông tin user đang online.  
        Yêu cầu xác thực bằng JWT Bearer Token.
      security:
        - bearerAuth: []
      responses:
        '200':
          description: Stream trạng thái online (SSE)
          content:
            text/event-stream:
              schema:
                type: string
                example: |
                  data: testuser@example.com is online

                  data: testuser@example.com is online

        '401':
          description: Không có hoặc token không hợp lệ
          content:
            application/json:
              schema:
                type: object
                properties:
                  msg:
                    type: string
                    example: Missing Authorization Header
    """
    current_user = get_jwt_identity()

    def event_stream():
        try:
            online_users[current_user] = datetime.utcnow()
            while True:
                # Cập nhật trạng thái online mỗi lần gửi ping
                online_users[current_user] = datetime.utcnow()
                yield f"data: {current_user} is online\n\n"
                time.sleep(5)  # Gửi ping mỗi 5 giây
        except GeneratorExit:
            # Khi client disconnect
            if current_user in online_users:
                del online_users[current_user]
    return Response(event_stream(), mimetype="text/event-stream")
