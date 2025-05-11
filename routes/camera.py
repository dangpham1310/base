from flask import Blueprint, request, jsonify, send_file
from datetime import datetime
import uuid
from flask_jwt_extended import jwt_required, get_current_user
from models import db, Camera, DetectedObject
from io import BytesIO
import os
from pathlib import Path
from typing import Optional
from PIL import Image
import numpy as np


def find_frame_path(
    id_frame: str,
    base_dir: Path = Path("/app/screens")
    # base_dir: Path = Path("/home/tado/Desktop/TuanAn/Plate_app_TuanAn/screens")
) -> Optional[Path]:
    target_name = f"{id_frame}.jpg"
    for day_folder in base_dir.iterdir():
        if not day_folder.is_dir():
            continue
        for minute_folder in day_folder.iterdir():
            if not minute_folder.is_dir():
                continue
            candidate = minute_folder / target_name
            if candidate.exists():
                return candidate.resolve()
    return None

def find_frame_crop(
    id_frame: str,
    base_dir: Path = Path("/app/plates")
    # base_dir: Path = Path("/home/tado/Desktop/TuanAn/Plate_app_TuanAn/plates")
) -> Optional[Path]:
    target_name = f"{id_frame}.jpg"
    for day_folder in base_dir.iterdir():
        if not day_folder.is_dir():
            continue
        for minute_folder in day_folder.iterdir():
            if not minute_folder.is_dir():
                continue
            candidate = minute_folder / target_name
            if candidate.exists():
                return candidate.resolve()
    return None


camera_bp = Blueprint('camera', __name__)



@camera_bp.route('/admin', methods=['GET'])
def get_all_camera_with_admin():

    cameras = Camera.query.filter_by(deleted_at=None).all()
    
    return jsonify([{
        'id': camera.id,
        'stream_id': camera.stream_id,
        'stream_url': camera.stream_url,
        'stream_name': camera.stream_name,
        'location': camera.location,
        'zone': camera.zone,
        'max_tracking_time': camera.max_tracking_time,
        'config_json': camera.config_json,
        'status': camera.status,
        'created_at': camera.created_at.isoformat() if camera.created_at else None,
        'updated_at': camera.updated_at.isoformat() if camera.updated_at else None,
        'created_by': camera.created_by,
        'updated_by': camera.updated_by
    } for camera in cameras])


@camera_bp.route('/', methods=['GET'])
@jwt_required()
def get_cameras():
    cameras = Camera.query.filter_by(deleted_at=None).all()
    return jsonify([{
        'stream_id': str(camera.stream_id),
        'stream_url': camera.stream_url,
        'stream_name': camera.stream_name,
        'created_at': camera.created_at.isoformat() if camera.created_at else None,
        'updated_at': camera.updated_at.isoformat() if camera.updated_at else None,
        'status': camera.status,
        'zone': camera.zone,
        'max_tracking_time': camera.max_tracking_time
    } for camera in cameras])

@camera_bp.route('/create', methods=['POST'])
@jwt_required()
def create_camera():
    data = request.get_json()
    if not data.get('stream_name') or not data.get('stream_url'):
        return jsonify({'error': 'Thiếu thông tin bắt buộc'}), 400

    current_user = get_current_user()
    current_time = datetime.utcnow()

    # Chuyển đổi zone thành string nếu được cung cấp
    zone = data.get('zone')
    if zone:
        zone = str(zone)  # Chuyển list thành string để lưu vào SQLite
    else:
        zone = None

    # Tạo camera mới
    camera = Camera(
        stream_id=str(uuid.uuid4()),
        stream_name=data['stream_name'],
        stream_url=data['stream_url'],
        status=data.get('status', True),
        zone=zone,
        max_tracking_time=float(data.get('max_tracking_time', 30.0)),
        created_at=current_time,
        updated_at=current_time,
        created_by=current_user.id
    )

    db.session.add(camera)
    db.session.commit()

    # Chuyển đổi zone từ string về list để trả về
    zone_list = eval(camera.zone) if camera.zone else []
    return jsonify({
        'stream_id': camera.stream_id,
        'stream_url': camera.stream_url,
        'stream_name': camera.stream_name,
        'created_at': camera.created_at.isoformat() if camera.created_at else None,
        'updated_at': camera.updated_at.isoformat() if camera.updated_at else None,
        'status': camera.status,
        'zone': zone_list,
        'max_tracking_time': camera.max_tracking_time
    }), 200


@camera_bp.route('/update/<uuid:stream_id>', methods=['PATCH'])
@jwt_required()
def update_camera(stream_id):
   
    camera = Camera.query.filter_by(stream_id=stream_id, deleted_at=None).first()
    if not camera:
        return jsonify({'error': 'Camera không tồn tại'}), 404

    data = request.get_json()
    current_user = get_current_user()
    
    if 'stream_name' in data:
        camera.stream_name = data['stream_name']
    if 'stream_url' in data:
        camera.stream_url = data['stream_url']
    if 'status' in data:
        camera.status = data['status']
    if 'zone' in data:
        camera.zone = data['zone']
    if 'max_tracking_time' in data:
        camera.max_tracking_time = data['max_tracking_time']

    camera.updated_at = datetime.utcnow()
    camera.updated_by = current_user.id

    db.session.commit()

    return jsonify({
        'stream_id': str(camera.stream_id),
        'stream_url': camera.stream_url,
        'stream_name': camera.stream_name,
        'created_at': camera.created_at.isoformat() if camera.created_at else None,
        'updated_at': camera.updated_at.isoformat() if camera.updated_at else None,
        'status': camera.status,
        'zone': camera.zone,
        'max_tracking_time': camera.max_tracking_time
    })

@camera_bp.route('/delete/<string:stream_id>', methods=['DELETE'])
@jwt_required()
def delete_camera(stream_id):
    
    camera = Camera.query.filter_by(stream_id=stream_id).first()
    if not camera:
        return jsonify({'error': 'Camera không tồn tại'}), 404
    current_user = get_current_user()
    camera.deleted_at = datetime.utcnow()
    camera.deleted_by = current_user.id
    db.session.commit()
    return "Delete Successful"

@camera_bp.route('/get_by/<uuid:stream_id>', methods=['GET'])
@jwt_required()
def get_camera_by_id(stream_id):
 
    camera = Camera.query.filter_by(stream_id=stream_id, deleted_at=None).first()
    if not camera:
        return jsonify({'error': 'Camera không tồn tại'}), 404
    
    return jsonify({
        'stream_id': str(camera.stream_id),
        'stream_url': camera.stream_url,
        'stream_name': camera.stream_name,
        'created_at': camera.created_at.isoformat() if camera.created_at else None,
        'updated_at': camera.updated_at.isoformat() if camera.updated_at else None,
        'status': camera.status,
        'zone': camera.zone,
        'max_tracking_time': camera.max_tracking_time
    })

@camera_bp.route('/get_zone/<uuid:stream_id>', methods=['GET'])
@jwt_required()
def get_camera_zone(stream_id):
  
    camera = Camera.query.filter_by(stream_id=stream_id, deleted_at=None).first()
    if not camera:
        return jsonify({'error': 'Camera không tồn tại'}), 404
    
    return jsonify({
        'zone': camera.zone
    })

@camera_bp.route('/update_zone/<uuid:stream_id>', methods=['PATCH'])
@jwt_required()
def update_camera_zone(stream_id):
   
    camera = Camera.query.filter_by(stream_id=stream_id, deleted_at=None).first()
    if not camera:
        return jsonify({'error': 'Camera không tồn tại'}), 404

    data = request.get_json()
    current_user = get_current_user()
    
    if 'zone' not in data:
        return jsonify({'error': 'Thiếu thông tin zone'}), 400

    camera.zone = data['zone']
    camera.updated_at = datetime.utcnow()
    camera.updated_by = current_user.id

    db.session.commit()

    return jsonify({
        'stream_id': str(camera.stream_id),
        'stream_url': camera.stream_url,
        'stream_name': camera.stream_name,
        'created_at': camera.created_at.isoformat() if camera.created_at else None,
        'updated_at': camera.updated_at.isoformat() if camera.updated_at else None,
        'status': camera.status,
        'zone': camera.zone,
        'max_tracking_time': camera.max_tracking_time
    })

@camera_bp.route('/enable/<uuid:stream_id>', methods=['PATCH'])
@jwt_required()
def enable_camera(stream_id):
   
    camera = Camera.query.filter_by(stream_id=stream_id, deleted_at=None).first()
    if not camera:
        return jsonify({'error': 'Camera không tồn tại'}), 404

    current_user = get_current_user()
    
    # Đảo ngược trạng thái của camera
    camera.status = not camera.status
    camera.updated_at = datetime.utcnow()
    camera.updated_by = current_user.id

    db.session.commit()

    return jsonify({
        'stream_id': str(camera.stream_id),
        'stream_url': camera.stream_url,
        'stream_name': camera.stream_name,
        'created_at': camera.created_at.isoformat() if camera.created_at else None,
        'updated_at': camera.updated_at.isoformat() if camera.updated_at else None,
        'status': camera.status,
        'zone': camera.zone,
        'max_tracking_time': camera.max_tracking_time
    })

@camera_bp.route('/disable/<uuid:stream_id>', methods=['PATCH'])
@jwt_required()
def disable_camera(stream_id):
  
    camera = Camera.query.filter_by(stream_id=stream_id, deleted_at=None).first()
    if not camera:
        return jsonify({'error': 'Camera không tồn tại'}), 404

    current_user = get_current_user()
    
    # Tắt camera
    camera.status = False
    camera.updated_at = datetime.utcnow()
    camera.updated_by = current_user.id

    db.session.commit()

    return jsonify({
        'stream_id': str(camera.stream_id),
        'stream_url': camera.stream_url,
        'stream_name': camera.stream_name,
        'created_at': camera.created_at.isoformat() if camera.created_at else None,
        'updated_at': camera.updated_at.isoformat() if camera.updated_at else None,
        'status': camera.status,
        'zone': camera.zone,
        'max_tracking_time': camera.max_tracking_time
    })

@camera_bp.route('/images/<string:frame_uuid>', methods=['GET'])
def get_image(frame_uuid):
    """
    Lấy ảnh theo frame_uuid
    ---
    get:
      tags:
        - Camera
      summary: Lấy ảnh từ frame_uuid
      description: Trả về ảnh gốc hoặc ảnh đã được cắt (crop) dựa vào bbox của DetectedObject
      parameters:
        - in: path
          name: frame_uuid
          required: true
          schema:
            type: string
            format: uuid
          description: UUID của frame cần lấy ảnh
        - in: query
          name: crop
          required: false
          schema:
            type: boolean
            default: false
          description: Cắt ảnh theo bbox từ DetectedObject nếu true
      responses:
        '200':
          description: Trả về ảnh thành công
          content:
            image/jpeg:
              schema:
                type: string
                format: binary
        '404':
          description: Không tìm thấy ảnh hoặc DetectedObject
          content:
            application/json:
              schema:
                type: object
                properties:
                  error:
                    type: string
                    example: Image not found
        '500':
          description: Lỗi server
          content:
            application/json:
              schema:
                type: object
                properties:
                  error:
                    type: string
    """
   
    # Tìm đường dẫn ảnh
    frame_path = find_frame_path(frame_uuid)
    print(frame_path)
    if not frame_path or not os.path.exists(frame_path):
        return jsonify({'error': 'Image not found'}), 404

    # Đọc ảnh bằng PIL
    img = Image.open(frame_path)
    
    # Kiểm tra nếu cần crop
    crop = request.args.get('crop', 'false').lower() == 'true'
    if crop:
        # Tìm DetectedObject theo frame_id
        # detected_obj = DetectedObject.query.filter_by(frame_id=frame_uuid).first()
        # if not detected_obj or not detected_obj.bbox:
        #     return jsonify({'error': 'DetectedObject hoặc bbox không tìm thấy'}), 404
            
        # # Lấy bbox từ DetectedObject và chuyển về list
        # bbox = detected_obj.bbox
        # print("bbox: ", bbox)
        
        # # bbox là x y x y
        # x1, y1, x2, y2 = bbox
        # img = img.crop((x1, y1, x2, y2))
        frame_crop_path = find_frame_crop(frame_uuid)
        if not frame_crop_path or not os.path.exists(frame_crop_path):
            return jsonify({'error': 'Image not found'}), 404
        img = Image.open(frame_crop_path)

        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_byte_arr.seek(0)
        
        # Trả về ảnh
        return send_file(
            img_byte_arr,
            mimetype='image/jpeg',
            as_attachment=False,
            download_name=f"{frame_uuid}.jpg"
        )
    
    # Chuyển ảnh sang bytes
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    
    # Trả về ảnh
    return send_file(
        img_byte_arr,
        mimetype='image/jpeg',
        as_attachment=False,
        download_name=f"{frame_uuid}.jpg"
    )



