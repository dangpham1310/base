import redis
from config import Config
import json

# Khởi tạo Redis connection
redis_client = redis.Redis(
    host=Config.REDIS_HOST,
    port=Config.REDIS_PORT,
    db=Config.REDIS_DB,
    decode_responses=True
)

def get_redis_key(license_plate):
    """Tạo key cho Redis"""
    return f"{Config.REDIS_PREFIX}{license_plate}"

def load_blacklist_to_redis(blacklist_items):
    """Load danh sách blacklist vào Redis"""
    try:
        # Xóa tất cả các key cũ với prefix blacklist:
        for key in redis_client.scan_iter(f"{Config.REDIS_PREFIX}*"):
            redis_client.delete(key)
        
        # Thêm các bản ghi mới
        for item in blacklist_items:
            key = get_redis_key(item.license_plate)
            value = {
                'id': str(item.id),
                'license_plate': item.license_plate,
                'note': item.note
            }
            redis_client.set(key, json.dumps(value))
        return True
    except Exception as e:
        print(f"Lỗi khi load blacklist vào Redis: {str(e)}")
        return False

def add_blacklist_to_redis(blacklist_item):
    """Thêm một bản ghi blacklist vào Redis"""
    try:
        key = get_redis_key(blacklist_item.license_plate)
        value = {
            'id': str(blacklist_item.id),
            'license_plate': blacklist_item.license_plate,
            'note': blacklist_item.note,
        }
        redis_client.set(key, json.dumps(value))
        return True
    except Exception as e:
        print(f"Lỗi khi thêm blacklist vào Redis: {str(e)}")
        return False

def remove_blacklist_from_redis(license_plate):
    """Xóa một bản ghi blacklist khỏi Redis"""
    try:
        key = get_redis_key(license_plate)
        redis_client.delete(key)
        return True
    except Exception as e:
        print(f"Lỗi khi xóa blacklist khỏi Redis: {str(e)}")
        return False

def check_license_plate_in_redis(license_plate):
    """Kiểm tra biển số xe có trong blacklist không"""
    try:
        key = get_redis_key(license_plate)
        data = redis_client.get(key)
        return json.loads(data) if data else None
    except Exception as e:
        print(f"Lỗi khi kiểm tra biển số xe trong Redis: {str(e)}")
        return None

def get_all_blacklist_from_redis():
    """Lấy tất cả các cặp key-value trong Redis"""
    try:
        result = []
        for key in redis_client.scan_iter(f"{Config.REDIS_PREFIX}*"):
            data = redis_client.get(key)
            if data:
                result.append({
                    'key': key,
                    'value': json.loads(data)
                })
        return result
    except Exception as e:
        print(f"Lỗi khi lấy dữ liệu từ Redis: {str(e)}")
        return None 