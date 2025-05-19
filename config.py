class Config:
    SQLALCHEMY_DATABASE_URI = 'postgresql://tado:tado123@postgres:5432/tadodb'
    # SQLALCHEMY_DATABASE_URI = 'postgresql://tado:tado123@localhost:5433/tadodb'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'your-secret-key'
    JWT_SECRET_KEY = 'your-jwt-secret-key'  # Thêm khóa bí mật cho JWT
    
    # Redis Configuration
    REDIS_HOST = 'localhost'
    REDIS_PORT = 6380
    REDIS_DB = 0
    REDIS_PREFIX = 'blacklist:'
