import requests
import time
import pytest

BASE_URL = "http://localhost:5000"  # Đổi lại nếu server chạy port khác
TEST_EMAIL = "testuser@example.com"
TEST_PASSWORD = "testpass123"
TEST_NAME = "Test User"
TEST_PHONE = "+84999999999"

def register_user():
    res = requests.post(f"{BASE_URL}/register", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "name": TEST_NAME,
        "phone": TEST_PHONE
    })
    print("Register:", res.status_code, res.text)
    return res

def login_user():
    res = requests.post(f"{BASE_URL}/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    print("Login:", res.status_code, res.text)
    if res.status_code == 200:
        return res.json()["access_token"]
    return None

def test_register_and_login():
    res = register_user()
    token = login_user()
    print("Token:", token)

def test_stream_online_and_check_status():
    token = login_user()
    if not token:
        print("Không lấy được token!")
        return
    headers = {"Authorization": f"Bearer {token}"}
    # Mở kết nối stream
    with requests.get(f"{BASE_URL}/stream_online", headers=headers, stream=True) as r:
        print("Stream status:", r.status_code)
        # Đọc 2 dòng stream
        lines = []
        for line in r.iter_lines():
            if line:
                lines.append(line.decode())
                print("Stream line:", line.decode())
            if len(lines) >= 2:
                break
        # Kiểm tra trạng thái online
        res = requests.get(f"{BASE_URL}/is_online/{TEST_EMAIL}")
        print("Check online:", res.status_code, res.text)
    # Sau khi disconnect, chờ timeout
    time.sleep(65)
    res = requests.get(f"{BASE_URL}/is_online/{TEST_EMAIL}")
    print("Check offline:", res.status_code, res.text) 