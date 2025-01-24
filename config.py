class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'your-secret-key'
    JWT_SECRET_KEY = 'your-jwt-secret-key'  # Thêm khóa bí mật cho JWT
