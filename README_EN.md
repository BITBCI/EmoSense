# Multimodal Physiological Signal Acquisition System - Upper Computer

A PyQt5-based physiological signal acquisition and visualization software that supports real-time display of EEG, PPG, IMU data and cloud-based emotion recognition.

## Features

- ✅ Serial communication, real-time data acquisition and visualization
- ✅ EEG brain signals, dual-channel PPG oximetry, IMU attitude display
- ✅ Data recording and export (CSV format with relative timestamps)
- ✅ Cloud-based emotion recognition (Happy😊/Sad😢/Neutral😐)

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Basic Usage
```bash
python main.py
```
- Select serial port, baud rate: 3000000
- Click "Connect" to start acquisition
- Click "Record" to save data

### 3. Cloud-Based Emotion Recognition

#### Configure Server
```bash
python setup_cloud.py  # Configuration wizard
```
Or edit `cloud_config.py`:
```python
CLOUD_CONFIG = {
    "server_url": "http://your-server:5000/api/emotion",
    "timeout": 30
}
```

#### Local Testing
```bash
python test_emotion_server.py  # Start test server
python test_connection.py       # Test connection
```

#### Usage
1. Collect data for at least 5 seconds
2. Click "🌐 Upload to Cloud"
3. View emotion results

## Cloud API Interface

### Request Format
```
POST /api/emotion
Content-Type: application/json
```
```json
{
  "timestamp": "2026-01-31T12:00:00",
  "sample_rate": 500,
  "data_length": 2500,
  "eeg_data": [1234, 1235, ...],
  "ppg_red_data": [585311, ...],
  "ppg_ir_data": [1137662, ...],
  "imu_data": [[q0,q1,q2,q3], ...]
}
```

### Response Format
```json
{
  "status": "success",
  "emotion": "Happy",
  "confidence": 0.85,
  "details": {
    "happy_score": 0.85,
    "sad_score": 0.10,
    "neutral_score": 0.05
  }
}
```

### Flask Server Example
```python
from flask import Flask, request, jsonify
import numpy as np

app = Flask(__name__)

@app.route('/api/emotion', methods=['POST'])
def analyze_emotion():
    data = request.json
    eeg = np.array(data['eeg_data'])
    ppg_red = np.array(data['ppg_red_data'])
    ppg_ir = np.array(data['ppg_ir_data'])
    
    # TODO: Call your emotion recognition model
    # emotion, confidence = your_model.predict(eeg, ppg_red, ppg_ir)
    
    return jsonify({
        "status": "success",
        "emotion": "Happy",
        "confidence": 0.85
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

## Data Format

**CSV Output Format** (relative timestamps, starting from 0 seconds)
```csv
timestamp,ads1118,red_led,ir_led,quat_0,quat_1,quat_2,quat_3
0.000000,1156,585311,1137662,449216056,-667929544,-468222394,-534569319
0.002000,1153,585247,1137594,449216056,-667929544,-468222394,-534569319
```

## Troubleshooting

**Unable to Connect to Server**
```bash
python test_connection.py  # Run diagnostic tool
```
- Check server address and port
- Ensure server is running
- Check firewall settings

**Insufficient Data**
- Wait for at least 5 seconds of data collection
- Confirm device is connected

## Project Structure
```
UpperComputer/
├── main.py                    # Program entry
├── cloud_config.py            # Cloud configuration
├── setup_cloud.py             # Configuration wizard
├── test_emotion_server.py     # Test server
├── test_connection.py         # Connection diagnostics
├── ui/main_window.py          # Main interface
├── core/                      # Core modules
├── utils/                     # Utility functions
└── requirements.txt           # Dependencies list
```

## Development Environment
- Python 3.8+
- PyQt5 5.15+
- Baud rate: 3000000

---

## System Requirements

- Python 3.8+
- PyQt5
- Windows/Linux

## Version History

- v1.0.0 (2025-12-11): Initial release

