from flask import Blueprint, request, jsonify
from models import db, DetectedObject, Camera, BlackList
from datetime import datetime
import uuid
from flask_jwt_extended import jwt_required, get_current_user
from sqlalchemy import desc, asc, or_
from utils.redis_helper import (
    load_blacklist_to_redis,
    add_blacklist_to_redis,
    remove_blacklist_from_redis,
    check_license_plate_in_redis,
    get_all_blacklist_from_redis
)

blacklist_bp = Blueprint('blacklist', __name__)

@blacklist_bp.route('/reload-redis', methods=['GET'])
def reload_redis():
    """
    Load lại toàn bộ blacklist vào Redis
    ---
    get:
      tags:
        - Blacklist
      summary: Load lại toàn bộ blacklist vào Redis cache
      description: Load lại toàn bộ blacklist từ database vào Redis cache
      responses:
        '200':
          description: Load thành công
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: boolean
                    example: true
                  message:
                    type: string
                    example: Đã load lại blacklist vào Redis thành công
        '500':
          description: Lỗi server
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: boolean
                    example: false
                  message:
                    type: string
                    example: Lỗi khi load blacklist vào Redis
    """
    try:
        blacklist_items = BlackList.query.filter(BlackList.is_deleted == False).all()
        if load_blacklist_to_redis(blacklist_items):
            return jsonify({
                "status": True,
                "message": "Đã load lại blacklist vào Redis thành công"
            }), 200
        else:
            return jsonify({
                "status": False,
                "message": "Lỗi khi load blacklist vào Redis"
            }), 500
    except Exception as e:
        return jsonify({
            "status": False,
            "message": str(e)
        }), 500

@blacklist_bp.route('/add', methods=['POST'])
@jwt_required()
def add_blacklist():
    """
    Thêm biển số xe vào blacklist
    ---
    tags:
      - Blacklist
    summary: Thêm biển số xe vào blacklist
    description: |
      Thêm một biển số xe mới vào danh sách đen (blacklist).
      - Biển số xe là bắt buộc và không được trùng với các biển số đã có trong blacklist
      - Ghi chú (note) là tùy chọn, dùng để mô tả lý do đưa vào blacklist
      - Hệ thống sẽ tự động lưu thông tin người tạo và thời gian tạo
      - Dữ liệu sẽ được lưu vào cả database và Redis cache
    parameters:
      - in: header
        name: Authorization
        description: Bearer token để xác thực
        required: true
        schema:
          type: string
          example: "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - license_plate
            properties:
              license_plate:
                type: string
                description: |
                  Biển số xe cần thêm vào blacklist.
                  Format: <Tỉnh/Thành>-<Số xe>
                  VD: 51F-123.45, 30A-123.45
                minLength: 8
                maxLength: 12
                pattern: '^[0-9]{2}[A-Z]-[0-9]{3}.[0-9]{2}$'
                example: "51F-123.45"
              note:
                type: string
                description: Ghi chú về lý do đưa vào blacklist
                maxLength: 500
                example: "Xe vi phạm nhiều lần"
          examples:
            basic:
              summary: Basic Example
              value:
                license_plate: "51F-123.45"
                note: "Xe vi phạm nhiều lần"
            without_note:
              summary: Without Note
              value:
                license_plate: "30A-123.45"
    responses:
      '200':
        description: Thêm thành công
        content:
          application/json:
            schema:
              type: object
              properties:
                status:
                  type: boolean
                  description: Trạng thái thực hiện request
                  example: true
                message:
                  type: string
                  description: Thông báo kết quả
                  example: Thêm vào danh sách đen thành công
                data:
                  type: object
                  description: Thông tin biển số xe vừa thêm
                  properties:
                    id:
                      type: string
                      format: uuid
                      description: ID duy nhất của bản ghi
                      example: "123e4567-e89b-12d3-a456-426614174000"
                    license_plate:
                      type: string
                      description: Biển số xe
                      example: "51F-123.45"
                    note:
                      type: string
                      description: Ghi chú
                      example: "Xe vi phạm nhiều lần"
                    created_at:
                      type: string
                      format: date-time
                      description: Thời gian tạo
                      example: "2024-03-20T10:30:00Z"
                    created_by:
                      type: string
                      format: uuid
                      description: ID của người tạo
                      example: "123e4567-e89b-12d3-a456-426614174000"
            examples:
              success:
                summary: Success Response
                value:
                  status: true
                  message: "Thêm vào danh sách đen thành công"
                  data:
                    id: "123e4567-e89b-12d3-a456-426614174000"
                    license_plate: "51F-123.45"
                    note: "Xe vi phạm nhiều lần"
                    created_at: "2024-03-20T10:30:00Z"
                    created_by: "123e4567-e89b-12d3-a456-426614174000"
      '400':
        description: Dữ liệu không hợp lệ
        content:
          application/json:
            schema:
              type: object
              properties:
                status:
                  type: boolean
                  example: false
                message:
                  type: string
                  description: Chi tiết lỗi
                  example: Biển số xe không được để trống
            examples:
              missing_license:
                summary: Missing License Plate
                value:
                  status: false
                  message: "Biển số xe không được để trống"
              invalid_format:
                summary: Invalid Format
                value:
                  status: false
                  message: "Format biển số xe không hợp lệ"
      '401':
        description: Chưa xác thực
        content:
          application/json:
            schema:
              type: object
              properties:
                status:
                  type: boolean
                  example: false
                message:
                  type: string
                  example: Missing Authorization Header
      '409':
        description: Xung đột dữ liệu
        content:
          application/json:
            schema:
              type: object
              properties:
                status:
                  type: boolean
                  example: false
                message:
                  type: string
                  example: Biển số xe đã tồn tại trong blacklist
      '500':
        description: Lỗi server
        content:
          application/json:
            schema:
              type: object
              properties:
                status:
                  type: boolean
                  example: false
                message:
                  type: string
                  example: Internal Server Error
    """
    current_user = get_current_user()
    data = request.get_json()
    license_plate = data.get('license_plate')
    note = data.get('note')

    if not license_plate:
        return jsonify({
            "status": False,
            "message": "Biển số xe không được để trống"
        }), 400

    new_blacklist = BlackList(
        license_plate=license_plate,
        note=note,
        created_by=current_user.id
    )
    
    try:
        db.session.add(new_blacklist)
        db.session.commit()
        
        # Thêm vào Redis
        add_blacklist_to_redis(new_blacklist)

        return jsonify({
            "status": True,
            "message": "Thêm vào danh sách đen thành công",
            "data": {
                'id': str(new_blacklist.id),
                'license_plate': new_blacklist.license_plate,
                'note': new_blacklist.note
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": False,
            "message": str(e)
        }), 500

@blacklist_bp.route('/<uuid:id>', methods=['DELETE'])
@jwt_required()
def soft_delete_blacklist(id):
    """
    Xóa biển số xe khỏi blacklist
    ---
    delete:
      tags:
        - Blacklist
      summary: Xóa biển số xe khỏi blacklist
      description: Xóa mềm một biển số xe khỏi danh sách đen
      security:
        - bearerAuth: []
      parameters:
        - in: path
          name: id
          required: true
          schema:
            type: string
            format: uuid
          description: UUID của bản ghi cần xóa
      responses:
        '200':
          description: Xóa thành công
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: boolean
                    example: true
                  message:
                    type: string
                    example: Xóa thành công
                  data:
                    type: object
                    properties:
                      id:
                        type: string
                        format: uuid
                        example: "123e4567-e89b-12d3-a456-426614174000"
        '404':
          description: Không tìm thấy bản ghi
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: boolean
                    example: false
                  message:
                    type: string
                    example: Không tìm thấy bản ghi
    """
    try:
        blacklist = BlackList.query.get(id)
        if not blacklist:
            return jsonify({
                "status": False,
                "message": "Không tìm thấy bản ghi"
            }), 404
        
        if blacklist.is_deleted:
            return jsonify({
                "status": False,
                "message": "Bản ghi đã bị xóa trước đó"
            }), 400

        # Xóa khỏi Redis trước
        remove_blacklist_from_redis(blacklist.license_plate)

        blacklist.is_deleted = True
        blacklist.deleted_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            "status": True,
            "message": "Xóa thành công",
            "data": {
                'id': str(blacklist.id)
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": False,
            "message": str(e)
        }), 500

@blacklist_bp.route('/check/<license_plate>', methods=['GET'])
def check_blacklist(license_plate):
    """
    Kiểm tra biển số xe trong blacklist
    ---
    get:
      tags:
        - Blacklist
      summary: Kiểm tra biển số xe trong blacklist
      description: Kiểm tra một biển số xe có nằm trong danh sách đen hay không
      parameters:
        - in: path
          name: license_plate
          required: true
          schema:
            type: string
          description: Biển số xe cần kiểm tra
          example: "51F-123.45"
      responses:
        '200':
          description: Tìm thấy trong blacklist
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: boolean
                    example: true
                  message:
                    type: string
                    example: Biển số xe nằm trong blacklist
                  data:
                    type: object
                    properties:
                      id:
                        type: string
                        format: uuid
                        example: "123e4567-e89b-12d3-a456-426614174000"
                      license_plate:
                        type: string
                        example: "51F-123.45"
                      note:
                        type: string
                        example: "Xe vi phạm nhiều lần"
        '404':
          description: Không tìm thấy trong blacklist
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: boolean
                    example: false
                  message:
                    type: string
                    example: Biển số xe không nằm trong blacklist
    """
    try:
        # Kiểm tra trong Redis trước
        redis_data = check_license_plate_in_redis(license_plate)
        if redis_data:
            return jsonify({
                "status": True,
                "message": "Biển số xe nằm trong blacklist",
                "data": redis_data
            }), 200

        # Nếu không có trong Redis, kiểm tra trong database
        blacklist = BlackList.query.filter(
            BlackList.license_plate == license_plate,
            BlackList.is_deleted == False
        ).first()

        if blacklist:
            # Thêm vào Redis nếu tìm thấy trong database
            add_blacklist_to_redis(blacklist)
            return jsonify({
                "status": True,
                "message": "Biển số xe nằm trong blacklist",
                "data": {
                    'id': str(blacklist.id),
                    'license_plate': blacklist.license_plate,
                    'note': blacklist.note
                }
            }), 200
        
        return jsonify({
            "status": False,
            "message": "Biển số xe không nằm trong blacklist"
        }), 404

    except Exception as e:
        return jsonify({
            "status": False,
            "message": str(e)
        }), 500

@blacklist_bp.route('/get-by-creator', methods=['GET'])
@jwt_required()
def get_by_creator():
    """
    Lấy danh sách blacklist theo người tạo
    ---
    get:
      tags:
        - Blacklist
      summary: Lấy danh sách blacklist theo người tạo
      description: Lấy danh sách các biển số xe trong blacklist được tạo bởi người dùng hiện tại, sắp xếp theo id giảm dần (id lớn nhất trước)
      security:
        - bearerAuth: []
      responses:
        '200':
          description: Lấy danh sách thành công
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: boolean
                    example: true
                  message:
                    type: string
                    example: Lấy danh sách thành công
                  data:
                    type: array
                    items:
                      type: object
                      properties:
                        id:
                          type: string
                          format: uuid
                          example: "123e4567-e89b-12d3-a456-426614174000"
                        license_plate:
                          type: string
                          example: "51F-123.45"
                        note:
                          type: string
                          example: "Xe vi phạm nhiều lần"
    """
    try:
        current_user = get_current_user()
        blacklist_items = BlackList.query.filter(
            BlackList.created_by == current_user.id,
            BlackList.is_deleted == False
        ).order_by(desc(BlackList.id)).all()

        result = []
        for item in blacklist_items:
            result.append({
                'id': str(item.id),
                'license_plate': item.license_plate,
                'note': item.note
            })

        return jsonify({
            "status": True,
            "message": "Lấy danh sách thành công",
            "data": result
        }), 200

    except Exception as e:
        return jsonify({
            "status": False,
            "message": str(e)
        }), 500

@blacklist_bp.route('/redis/get-all', methods=['GET'])
def get_all_from_redis():
    """
    Lấy tất cả blacklist từ Redis
    ---
    get:
      tags:
        - Blacklist
      summary: Lấy tất cả blacklist từ Redis
      description: Lấy tất cả các cặp key-value trong Redis cache
      responses:
        '200':
          description: Lấy dữ liệu thành công
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: boolean
                    example: true
                  message:
                    type: string
                    example: Lấy dữ liệu từ Redis thành công
                  data:
                    type: object
                    additionalProperties:
                      type: object
                      properties:
                        id:
                          type: string
                          format: uuid
                        license_plate:
                          type: string
                        note:
                          type: string
        '500':
          description: Lỗi server
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: boolean
                    example: false
                  message:
                    type: string
                    example: Lỗi khi lấy dữ liệu từ Redis
    """
    try:
        result = get_all_blacklist_from_redis()
        if result is not None:
            return jsonify({
                "status": True,
                "message": "Lấy dữ liệu từ Redis thành công",
                "data": result
            }), 200
        else:
            return jsonify({
                "status": False,
                "message": "Lỗi khi lấy dữ liệu từ Redis"
            }), 500
    except Exception as e:
        return jsonify({
            "status": False,
            "message": str(e)
        }), 500


    