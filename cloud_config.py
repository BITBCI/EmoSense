"""
云端服务器配置文件
用于配置情绪识别云端服务器的连接信息
"""

# 云端服务器配置
CLOUD_CONFIG = {
    # 云端服务器地址（请修改为您的实际服务器地址）
    "server_url": "http://127.0.0.1:5000/api/emotion",
    
    # 请求超时时间（秒）
    "timeout": 30,
    
    # 上传数据的最大长度（数据点数）
    "max_data_points": 2500,  # 5秒 @ 500Hz
    
    # API 密钥（如果服务器需要认证）
    "api_key": "your-api-key-here",
    
    # 是否启用SSL验证
    "verify_ssl": True
}

# 情绪类别映射（中英文）
EMOTION_MAPPING = {
    "happy": "开心",
    "sad": "悲伤",
    "neutral": "中性",
    "开心": "happy",
    "悲伤": "sad",
    "中性": "neutral"
}

# 情绪显示配置（使用英文key统一管理）
EMOTION_DISPLAY_CONFIG = {
    "happy": {
        "color": "#FF6B6B",
        "bg_color": "#FFE5E5",
        "icon": "😊",
        "lang_key": "emotion_happy"
    },
    "sad": {
        "color": "#4A90E2",
        "bg_color": "#E3F2FD",
        "icon": "😢",
        "lang_key": "emotion_sad"
    },
    "neutral": {
        "color": "#666666",
        "bg_color": "#F0F0F0",
        "icon": "😐",
        "lang_key": "emotion_neutral"
    }
}
