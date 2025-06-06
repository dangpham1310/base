from flask import Blueprint, request, jsonify
from models import db, DetectedObject, Camera
from datetime import datetime
import uuid
from flask_jwt_extended import jwt_required, get_current_user
from sqlalchemy import desc, asc
from utils.redis_helper import check_license_plate_in_redis
import requests
from pathlib import Path
from typing import Optional
detected_object_bp = Blueprint('detected_object', __name__)

# get all camera with admin

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


@detected_object_bp.route('/data_detected/', methods=['GET'])
def get_data_detected():
    """
    Lấy danh sách các đối tượng đã phát hiện (filter/search)
    ---
    get:
      tags:
        - DetectedObject
      summary: Lấy danh sách các đối tượng đã phát hiện với bộ lọc
      description: |
        Cho phép tìm kiếm và lọc danh sách các đối tượng đã được phát hiện (ví dụ: biển số xe) 
        dựa trên nhiều tiêu chí như stream_id, khoảng thời gian, và nội dung biển số.
      parameters:
        - in: query
          name: page
          schema:
            type: integer
            default: 1
          description: Số trang hiện tại để phân trang.
        - in: query
          name: page_size
          schema:
            type: integer
            default: 10
          description: Số lượng mục trên mỗi trang.
        - in: query
          name: stream_ids
          schema:
            type: string
          description: Danh sách các stream_id (UUID), cách nhau bởi dấu phẩy (VD: "uuid1,uuid2").
        - in: query
          name: start_time
          schema:
            type: string
            format: date-time
          description: Thời gian bắt đầu tìm kiếm (ISO 8601, VD: "2024-03-20T10:00:00Z").
        - in: query
          name: end_time
          schema:
            type: string
            format: date-time
          description: Thời gian kết thúc tìm kiếm (ISO 8601, VD: "2024-03-20T18:00:00Z").
        - in: query
          name: license_plate
          schema:
            type: string
          description: |
            Biển số xe cần tìm. Hỗ trợ tìm kiếm chứa ký tự (không phân biệt hoa thường). 
            Ví dụ: "59A123" hoặc "%A123%" để tìm các biển số chứa "A123".
        - in: query
          name: sort
          schema:
            type: string
            enum: [asc, desc]
            default: desc
          description: Thứ tự sắp xếp theo thời gian tạo (`time_created`).
      responses:
        '200':
          description: Thành công. Trả về danh sách các đối tượng khớp.
          content:
            application/json:
              schema:
                type: object
                properties:
                  total:
                    type: integer
                    description: Tổng số mục tìm được.
                  page:
                    type: integer
                    description: Trang hiện tại.
                  page_size:
                    type: integer
                    description: Số mục trên trang.
                  items:
                    type: array
                    items:
                      type: object
                      properties:
                        id:
                          type: string
                          format: uuid
                          description: ID của đối tượng phát hiện.
                        stream_id:
                          type: string
                          format: uuid
                          description: ID của camera stream.
                        frame_id:
                          type: string
                          format: uuid
                          description: ID của khung hình chứa đối tượng.
                        license_plate:
                          type: string
                          description: Biển số xe đã phát hiện.
                        time_created:
                          type: string
                          format: date-time
                          description: Thời gian phát hiện đối tượng.
                        bbox:
                          type: array
                          items:
                            type: integer
                          description: Tọa độ bounding box của đối tượng [x, y, width, height].
                          example: [100, 150, 50, 30]
        '400':
          description: Lỗi do định dạng tham số không hợp lệ (ví dụ: start_time, end_time).
          content:
            application/json:
              schema:
                type: object
                properties:
                  error:
                    type: string
                    example: "Định dạng start_time không hợp lệ. Sử dụng định dạng ISO (VD: 2024-03-20T10:00:00Z)"
        '500':
          description: Lỗi server.
          content:
            application/json:
              schema:
                type: object
                properties:
                  error:
                    type: string
                    example: "Đã xảy ra lỗi trong quá trình xử lý yêu cầu."
                  details:
                    type: string
                    example: "<chi tiết lỗi cụ thể>"
    """
    try:
        # Lấy các tham số từ query string
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        stream_ids = request.args.get('stream_ids', None)
        start_time = request.args.get('start_time', None)
        end_time = request.args.get('end_time', None)
        license_plate = request.args.get('license_plate', None)
        sort = request.args.get('sort', 'desc')

        print("Stream ids:", stream_ids)
        print("License plate:", license_plate)
        print("Time range:", start_time, "to", end_time)

        # Tạo query cơ bản
        query = DetectedObject.query

        # Xử lý filter stream_ids nếu có
        if stream_ids:
            # Tách chuỗi stream_ids thành list nếu có nhiều ID
            stream_id_list = [id.strip() for id in stream_ids.split(',')]
            query = query.filter(DetectedObject.stream_id.in_(stream_id_list))

        # Xử lý filter license_plate nếu có
        if license_plate:
            query = query.filter(DetectedObject.license_plate.ilike(f'%{license_plate}%'))

        # Xử lý filter thời gian
        if start_time:
            try:
                start_datetime = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                query = query.filter(DetectedObject.time_created >= start_datetime)
            except ValueError:
                return jsonify({
                    'error': 'Định dạng start_time không hợp lệ. Sử dụng định dạng ISO (VD: 2024-03-20T10:00:00Z)'
                }), 400

        if end_time:
            try:
                end_datetime = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                query = query.filter(DetectedObject.time_created <= end_datetime)
            except ValueError:
                return jsonify({
                    'error': 'Định dạng end_time không hợp lệ. Sử dụng định dạng ISO (VD: 2024-03-20T10:00:00Z)'
                }), 400

        # Áp dụng sắp xếp
        query = query.order_by(
            asc(DetectedObject.time_created) if sort.lower() == 'asc' 
            else desc(DetectedObject.time_created)
        )

        # Thực thi query với phân trang
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()

        print("Total items found:", total)

        # Format kết quả trả về
        result = {
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': [{
                'id': str(item.id),
                'stream_id': item.stream_id,
                'frame_id': item.frame_id,
                'license_plate': item.license_plate,
                'time_created': item.time_created.isoformat(),
                'bbox': item.bbox
            } for item in items]
        }

        return jsonify(result)

    except Exception as e:
        print("Error:", str(e))
        return jsonify({
            'error': 'Đã xảy ra lỗi trong quá trình xử lý yêu cầu.',
            'details': str(e)
        }), 500

#viết cho tôi hàm gửi telegram
# Here is the token for bot QLNV @Quan_Ly_Nhan_Vien_bot:
# 7910124964:AAGSO1rdFMMvtKxRviYxEo7iTcH2BQtP9WE


def send_telegram_message(chat_id: int, license_plate: str, frame_id: str):
    token = '7910124964:AAGSO1rdFMMvtKxRviYxEo7iTcH2BQtP9WE'
    frame_path = find_frame_path(frame_id)  # Đảm bảo đường dẫn ảnh tồn tại
    caption = f"Biển Số Xe {license_plate} đã được phát hiện."
    
    url = f'https://api.telegram.org/bot{token}/sendPhoto'
    with open(frame_path, 'rb') as photo:
        files = {'photo': photo}
        data = {
            'chat_id': chat_id,
            'caption': caption,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, data=data, files=files)

    if response.status_code == 200:
        print('Photo sent successfully')
    else:
        print(f'Failed to send photo: {response.text}')




@detected_object_bp.route('/data_detected/create', methods=['POST'])
def create_data_detected():

    data = request.get_json()


    required_fields = ['stream_id', 'frame_id', 'bbox', 'license_plate']

    camera = Camera.query.filter_by(stream_id=data["stream_id"]).first()

    if not camera:
        print("Invalid stream_id: ", data['stream_id'])
        return jsonify({'error': 'Invalid stream_id'}), 422

    # Convert bbox từ string thành list số nguyên
    bbox_str = data['bbox'][0]  # Lấy string đầu tiên từ list
    x, y, w, h = map(int, bbox_str.split(','))  # Convert thành x,y,w,h
    
    # Tính toán tọa độ cho crop (left, top, right, bottom)
    bbox = [x, y, w,h ]
    print("Original bbox (x,y,w,h):", [x, y, w, h])


    # Create new detected object
    detected_object = DetectedObject(
        id_camera=camera.id,
        stream_id=data["stream_id"],
        frame_id=data["frame_id"],
        bbox=bbox,  # Lưu bbox dạng [left, top, right, bottom]
        license_plate=data['license_plate']
    )

    db.session.add(detected_object)
    db.session.commit()
    print("Đã add vào database")

    if check_license_plate_in_redis(data['license_plate']):
        print("License plate is in redis: ", data['license_plate'])
        send_telegram_message(chat_id=-4646244350, license_plate=data['license_plate'], frame_id=data['frame_id'])
        return jsonify({'error': 'License plate is in redis'}), 200

    return jsonify({
        'id': str(detected_object.id),
        'stream_id': detected_object.stream_id,
        'frame_id': detected_object.frame_id,
        'bbox': detected_object.bbox,
        'license_plate': detected_object.license_plate,
        'time_created': detected_object.time_created.isoformat()
    })


@detected_object_bp.route('/data_detected/update/<string:id>', methods=['PUT'])
@jwt_required()
def update_data_detected(id):

    try:
        # Tìm detected object theo id
        detected_object = DetectedObject.query.filter_by(id=id, deleted_at=None).first()
        if not detected_object:
            return jsonify({'error': 'Detected object not found'}), 404

        data = request.get_json()
        current_user = get_current_user()

        # Cập nhật stream_id nếu có và validate
        if 'stream_id' in data:
            try:
                stream_id = uuid.UUID(data['stream_id'])
                # Kiểm tra stream_id tồn tại
                camera = Camera.query.filter_by(stream_id=stream_id, deleted_at=None).first()
                if not camera:
                    return jsonify({'error': 'Invalid stream_id'}), 422
                detected_object.stream_id = stream_id
            except ValueError:
                return jsonify({'error': 'Invalid UUID format for stream_id'}), 422

        # Cập nhật frame_id nếu có
        if 'frame_id' in data:
            try:
                frame_id = uuid.UUID(data['frame_id'])
                detected_object.frame_id = frame_id
            except ValueError:
                return jsonify({'error': 'Invalid UUID format for frame_id'}), 422

        # Cập nhật các trường khác
        if 'object_type' in data:
            detected_object.object_type = data['object_type']
        if 'bbox' in data:
            detected_object.bbox = data['bbox']
        if 'time' in data:
            detected_object.detected_time = datetime.fromisoformat(data['time'].replace('Z', '+00:00'))
        if 'license_plate' in data:
            detected_object.license_plate = data['license_plate']

        # Cập nhật thông tin người sửa và thời gian
        detected_object.updated_at = datetime.utcnow()
        detected_object.updated_by = current_user.id

        db.session.commit()

        # Trả về object đã cập nhật
        return jsonify({
            'id': detected_object.id,
            'stream_id': str(detected_object.stream_id),
            'object_type': detected_object.object_type,
            'frame_id': str(detected_object.frame_id),
            'bbox': detected_object.bbox,
            'time': detected_object.detected_time.isoformat(),
            'license_plate': detected_object.license_plate
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 422
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@detected_object_bp.route('/data_detected/delete', methods=['DELETE'])
@jwt_required()
def delete_data_detected():

    try:
        # Lấy các tham số từ query string
        object_id = request.args.get('id', None)
        stream_ids = request.args.get('stream_ids', None)
        start_time = request.args.get('start_time', None)
        end_time = request.args.get('end_time', None)

        # Tạo query base
        query = DetectedObject.query.filter_by(deleted_at=None)


        # Lọc theo id
        if object_id:
            query = query.filter(DetectedObject.id == object_id)

        # Lọc theo stream_ids
        if stream_ids:
            try:
                stream_id_list = [uuid.UUID(id.strip()) for id in stream_ids.split(',')]
                query = query.filter(DetectedObject.stream_id.in_(stream_id_list))
            except ValueError:
                return jsonify({'error': 'Invalid UUID format in stream_ids'}), 422

        # Lọc theo thời gian
        if start_time:
            try:
                start_datetime = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                query = query.filter(DetectedObject.detected_time >= start_datetime)
            except ValueError:
                return jsonify({'error': 'Invalid start_time format'}), 422

        if end_time:
            try:
                end_datetime = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                query = query.filter(DetectedObject.detected_time <= end_datetime)
            except ValueError:
                return jsonify({'error': 'Invalid end_time format'}), 422

        # Lấy danh sách các objects cần xóa
        objects_to_delete = query.all()
        if not objects_to_delete:
            return jsonify({'message': 'No objects found to delete'}), 200

        current_user = get_current_user()
        current_time = datetime.utcnow()

        # Thực hiện soft delete
        for obj in objects_to_delete:
            obj.deleted_at = current_time
            obj.deleted_by = current_user.id

        db.session.commit()

        return jsonify({'message': f'Successfully deleted {len(objects_to_delete)} objects'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

