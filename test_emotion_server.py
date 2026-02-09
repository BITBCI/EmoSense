"""
云端情绪识别测试服务器
这是一个简单的Flask服务器示例，用于测试与上位机的通信

运行方式:
    python test_emotion_server.py

注意：这只是一个测试服务器，返回随机的情绪结果
实际部署时，请替换为您的真实多模态情绪识别算法
"""

from flask import Flask, request, jsonify
from datetime import datetime
import numpy as np
import random

app = Flask(__name__)

# 模拟的情绪类别和置信度（使用英文key，由客户端根据语言设置翻译）
EMOTIONS = ["happy", "sad", "neutral"]


@app.route('/api/emotion', methods=['POST'])
def analyze_emotion():
    """
    情绪识别API端点
    接收多模态生理信号数据，返回情绪识别结果
    """
    try:
        # 获取请求数据
        data = request.json
        
        # 验证必要字段
        required_fields = ['timestamp', 'sample_rate', 'data_length', 
                          'eeg_data', 'ppg_red_data', 'ppg_ir_data', 'imu_data']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "status": "error",
                    "error_code": "INVALID_DATA",
                    "message": f"缺少必要字段: {field}",
                    "timestamp": datetime.now().isoformat()
                }), 400
        
        # 提取各模态数据
        eeg = np.array(data['eeg_data'])
        ppg_red = np.array(data['ppg_red_data'])
        ppg_ir = np.array(data['ppg_ir_data'])
        imu = np.array(data['imu_data'])
        
        print(f"\n收到数据:")
        print(f"  - 采样率: {data['sample_rate']} Hz")
        print(f"  - 数据长度: {data['data_length']} 点")
        print(f"  - EEG数据: {len(eeg)} 点, 范围 [{eeg.min():.1f}, {eeg.max():.1f}]")
        print(f"  - PPG红光: {len(ppg_red)} 点, 范围 [{ppg_red.min():.1f}, {ppg_red.max():.1f}]")
        print(f"  - PPG红外: {len(ppg_ir)} 点, 范围 [{ppg_ir.min():.1f}, {ppg_ir.max():.1f}]")
        print(f"  - IMU数据: {len(imu)} 点")
        
        # ============================================================
        # TODO: 在这里调用您的真实多模态情绪识别算法
        # ============================================================
        # 示例：
        # emotion, confidence, scores = your_emotion_model.predict(
        #     eeg=eeg, 
        #     ppg_red=ppg_red, 
        #     ppg_ir=ppg_ir, 
        #     imu=imu
        # )
        
        # 以下是模拟代码，仅用于测试
        # 计算一些简单特征作为示例
        eeg_mean = np.mean(eeg)
        ppg_std = np.std(ppg_red)
        
        # 基于简单规则的情绪判断（仅作演示）
        if ppg_std > 50000:  # 高变异性可能表示兴奋
            emotion = "开心"
            happy_score = 0.7 + random.uniform(0, 0.2)
        elif eeg_mean < 1000:  # 低EEG可能表示低唤醒
            emotion = "悲伤"
            happy_score = 0.1 + random.uniform(0, 0.2)
        else:
            emotion = "中性"
            happy_score = 0.3 + random.uniform(0, 0.2)
        
        # 生成各情绪的得分
        sad_score = random.uniform(0.1, 0.3) if emotion != "悲伤" else 0.7 + random.uniform(0, 0.2)
        neutral_score = 1.0 - happy_score - sad_score
        
        # 归一化
        total = happy_score + sad_score + neutral_score
        happy_score /= total
        sad_score /= total
        neutral_score /= total
        
        # 选择最高得分的情绪
        scores = {"开心": happy_score, "悲伤": sad_score, "中性": neutral_score}
        emotion = max(scores, key=scores.get)
        confidence = scores[emotion]
        
        print(f"\n识别结果:")
        print(f"  - 情绪: {emotion}")
        print(f"  - 置信度: {confidence:.2%}")
        print(f"  - 详细得分: {scores}")
        
        # 返回结果
        return jsonify({
            "status": "success",
            "emotion": emotion,
            "confidence": float(confidence),
            "details": {
                "happy_score": float(happy_score),
                "sad_score": float(sad_score),
                "neutral_score": float(neutral_score)
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"错误: {str(e)}")
        return jsonify({
            "status": "error",
            "error_code": "PROCESSING_ERROR",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({
        "status": "ok",
        "service": "情绪识别服务",
        "timestamp": datetime.now().isoformat()
    })


if __name__ == '__main__':
    print("=" * 60)
    print("云端情绪识别测试服务器")
    print("=" * 60)
    print("服务器地址: http://0.0.0.0:5000")
    print("API端点: http://0.0.0.0:5000/api/emotion")
    print("\n注意: 这是测试服务器，返回模拟结果")
    print("实际部署时，请替换为真实的情绪识别算法")
    print("=" * 60)
    print()
    
    # 启动服务器
    app.run(
        host='0.0.0.0',  # 允许外部访问
        port=5000,
        debug=True
    )
