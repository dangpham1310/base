# API Documentation cho Blacklist Service

## Base URL
```
/blacklist
```

## Endpoints

### 1. Reload Blacklist vào Redis
```http
GET /reload-redis
```

**Mô tả:** Load lại toàn bộ blacklist từ database vào Redis cache

**Response:**
- Success (200):
```json
{
    "status": true,
    "message": "Đã load lại blacklist vào Redis thành công"
}
```
- Error (500):
```json
{
    "status": false,
    "message": "Lỗi khi load blacklist vào Redis"
}
```

### 2. Thêm Biển Số Xe vào Blacklist
```http
POST /add
```

**Authentication:** Required (JWT Token)

**Request Body:**
```json
{
    "license_plate": "string",
    "note": "string"
}
```

**Response:**
- Success (200):
```json
{
    "status": true,
    "message": "Thêm vào danh sách đen thành công",
    "data": {
        "id": "uuid",
        "license_plate": "string",
        "note": "string"
    }
}
```
- Error (400):
```json
{
    "status": false,
    "message": "Biển số xe không được để trống"
}
```

### 3. Xóa Biển Số Xe khỏi Blacklist
```http
DELETE /<uuid:id>
```

**Authentication:** Required (JWT Token)

**Parameters:**
- `id`: UUID của bản ghi cần xóa

**Response:**
- Success (200):
```json
{
    "status": true,
    "message": "Xóa thành công",
    "data": {
        "id": "uuid"
    }
}
```
- Error (404):
```json
{
    "status": false,
    "message": "Không tìm thấy bản ghi"
}
```

### 4. Kiểm tra Biển Số Xe trong Blacklist
```http
GET /check/<license_plate>
```

**Parameters:**
- `license_plate`: Biển số xe cần kiểm tra

**Response:**
- Success (200):
```json
{
    "status": true,
    "message": "Biển số xe nằm trong blacklist",
    "data": {
        "id": "uuid",
        "license_plate": "string",
        "note": "string"
    }
}
```
- Not Found (404):
```json
{
    "status": false,
    "message": "Biển số xe không nằm trong blacklist"
}
```

### 5. Lấy Danh Sách Blacklist theo Người Tạo
```http
GET /get-by-creator
```

**Authentication:** Required (JWT Token)

**Response:**
- Success (200):
```json
{
    "status": true,
    "message": "Lấy danh sách thành công",
    "data": [
        {
            "id": "uuid",
            "license_plate": "string",
            "note": "string",
            "created_at": "YYYY-MM-DD HH:MM:SS"
        }
    ]
}
```

### 6. Lấy Tất Cả Blacklist từ Redis
```http
GET /redis/get-all
```

**Response:**
- Success (200):
```json
{
    "status": true,
    "message": "Lấy dữ liệu từ Redis thành công",
    "data": {
        // Danh sách các cặp key-value từ Redis
    }
}
```
- Error (500):
```json
{
    "status": false,
    "message": "Lỗi khi lấy dữ liệu từ Redis"
}
```

## Lưu ý
- Tất cả các response lỗi đều trả về format:
```json
{
    "status": false,
    "message": "Thông báo lỗi"
}
```
- Các endpoint yêu cầu xác thực cần gửi kèm JWT token trong header:
```
Authorization: Bearer <token>
``` 