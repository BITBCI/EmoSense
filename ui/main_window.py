"""
主窗口界面
实现串口控制、数据可视化等功能
"""

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QComboBox, QLabel, QGroupBox, 
                             QGridLayout, QTextEdit, QSplitter, QMessageBox,
                             QFileDialog, QCheckBox)
from PyQt5.QtCore import QTimer, Qt, pyqtSlot, QThread, pyqtSignal
from PyQt5.QtGui import QFont
import pyqtgraph as pg
import numpy as np
from datetime import datetime
from scipy import signal, interpolate
import os
import mne
import requests
import json

from core.serial_handler import SerialHandler
from core.data_parser import DataParser
from core.data_buffer import DataBuffer
from utils.file_utils import DataRecorder
from utils.language import LanguageManager

# 尝试导入云端配置，如果不存在则使用默认配置
try:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from cloud_config import CLOUD_CONFIG, EMOTION_DISPLAY_CONFIG
except ImportError:
    # 默认配置
    CLOUD_CONFIG = {
        "server_url": "http://localhost:5000/api/emotion",
        "timeout": 30,
        "max_data_points": 2500
    }
    EMOTION_DISPLAY_CONFIG = {
        "happy": {"color": "#FF6B6B", "bg_color": "#FFE5E5", "icon": "😊", "lang_key": "emotion_happy"},
        "sad": {"color": "#4A90E2", "bg_color": "#E3F2FD", "icon": "😢", "lang_key": "emotion_sad"},
        "neutral": {"color": "#666666", "bg_color": "#F0F0F0", "icon": "😐", "lang_key": "emotion_neutral"}
    }


class UploadWorker(QThread):
    """后台上传线程，避免阻塞UI"""
    upload_success = pyqtSignal(str, float)  # emotion, confidence
    upload_error = pyqtSignal(str)  # error message
    
    def __init__(self, url, data, timeout=5):
        super().__init__()
        self.url = url
        self.data = data
        self.timeout = timeout
    
    def run(self):
        try:
            response = requests.post(
                self.url,
                json=self.data,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                emotion = result.get('emotion', 'unknown')
                confidence = result.get('confidence', 0)
                self.upload_success.emit(emotion, confidence)
            else:
                self.upload_error.emit(f"server_error:{response.status_code}")
                
        except requests.exceptions.Timeout:
            self.upload_error.emit("timeout")
        except requests.exceptions.ConnectionError:
            self.upload_error.emit("connection_error")
        except Exception as e:
            self.upload_error.emit(f"error:{str(e)}")


class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        # 初始化语言管理器
        self.lang_manager = LanguageManager('zh_CN')
        
        self.serial_handler = SerialHandler()
        self.data_parser = DataParser()
        self.data_buffer = DataBuffer(max_points=2500)  # 缓存2500个数据点 (5秒@500Hz)
        self.data_recorder = None
        
        self.is_paused = False
        
        # 信号放大倍数配置（使真实数据与虚拟数据单位统一）
        # 虚拟数据：BrainVision的EEG数据单位是V（伏特），转换为μV（×1,000,000）
        # 真实数据：ADS1118输出ADC原始值（16位，0-65535）
        # 为了使显示范围一致，需要对真实ADC数据进行放大
        self.eeg_scale_factor = 16  # EEG信号放大倍数（ADC原始值）
        self.ppg_scale_factor = 100  # PPG信号缩放倍数（ADC原始值太大，需要缩小）
        
        # 虚拟数据相关
        self.use_virtual_data = False
        self.virtual_eeg_data = None  # Fp1和Fp2的平均值
        self.virtual_ppg_data = None  # PPG通道数据
        self.virtual_data_index = 0
        self.virtual_sample_rate = 1000  # BrainVision数据采样率
        self.virtual_start_time = None  # 虚拟数据开始时间
        self.virtual_time_interval = 1.0 / 500  # 500Hz采样间隔（秒）
        
        # 显示窗口设置
        self.display_window = 5.0  # 固定显示5秒数据
        
        # 云端服务器配置
        self.cloud_server_url = CLOUD_CONFIG.get("server_url", "http://localhost:5000/api/emotion")
        self.cloud_timeout = CLOUD_CONFIG.get("timeout", 30)
        self.current_emotion = "neutral"  # 当前情绪状态：happy/sad/neutral
        self.is_uploading = False  # 是否正在上传
        
        # 云端上传定时器
        self.upload_timer = QTimer()
        self.upload_timer.timeout.connect(self.upload_data_to_cloud)
        self.upload_interval = 2000  # 2秒上传一次
        
        # 上传工作线程（用于后台HTTP请求，避免阻塞UI）
        self.upload_worker = None
        
        # 滤波器设计（假设采样率500Hz）
        self.sample_rate = 500  # Hz
        # EEG带通滤波器: 1-40Hz (避免低频漂移和高频混叠)
        self.eeg_sos = signal.butter(4, [1, 40], btype='band', fs=self.sample_rate, output='sos')
        # PPG低通滤波器: 0.5-8Hz (心率主频段)
        self.ppg_sos = signal.butter(4, [0.5, 8], btype='band', fs=self.sample_rate, output='sos')
        
        self.init_ui()
        self.init_plots()
        self.setup_connections()
        
        # 定时器用于更新UI
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_plots)
        self.update_timer.setInterval(100)  # 100ms更新一次（降低频率减少CPU占用）
        
        # 图表更新计数器，用于降低某些计算的频率
        self.plot_update_counter = 0
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(self.lang_manager.get_text('window_title'))
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)
        
        # 创建可视化区域
        splitter = QSplitter(Qt.Vertical)
        
        # 图表区域
        plot_widget = self.create_plot_area()
        splitter.addWidget(plot_widget)
        
        # 日志区域
        log_widget = self.create_log_area()
        splitter.addWidget(log_widget)
        
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        
        self.log_message(self.lang_manager.get_text('system_init'))
        
    def create_control_panel(self):
        """创建控制面板"""
        group = QGroupBox(self.lang_manager.get_text('control_panel'))
        layout = QHBoxLayout()
        
        # 串口选择
        self.port_label = QLabel(self.lang_manager.get_text('serial_port'))
        layout.addWidget(self.port_label)
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(120)
        layout.addWidget(self.port_combo)
        
        # 刷新按钮
        self.refresh_btn = QPushButton(self.lang_manager.get_text('refresh'))
        self.refresh_btn.clicked.connect(self.refresh_ports)
        layout.addWidget(self.refresh_btn)
        
        # 波特率选择
        self.baudrate_label = QLabel(self.lang_manager.get_text('baudrate'))
        layout.addWidget(self.baudrate_label)
        self.baudrate_combo = QComboBox()
        self.baudrate_combo.addItems(['3000000', '2000000', '1500000', '921600', 
                                      '460800', '115200', '57600', '9600'])
        self.baudrate_combo.setCurrentText('3000000')
        layout.addWidget(self.baudrate_combo)
        
        # 连接按钮
        self.connect_btn = QPushButton(self.lang_manager.get_text('connect'))
        self.connect_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.connect_btn.clicked.connect(self.toggle_connection)
        layout.addWidget(self.connect_btn)
        
        layout.addWidget(QLabel("|"))
        
        # 暂停/继续按钮
        self.pause_btn = QPushButton(self.lang_manager.get_text('pause'))
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.toggle_pause)
        layout.addWidget(self.pause_btn)
        
        # 清空数据按钮
        self.clear_btn = QPushButton(self.lang_manager.get_text('clear'))
        self.clear_btn.clicked.connect(self.clear_data)
        layout.addWidget(self.clear_btn)
        
        layout.addWidget(QLabel("|"))
        
        # 录制按钮
        self.record_btn = QPushButton(self.lang_manager.get_text('record'))
        self.record_btn.clicked.connect(self.toggle_recording)
        layout.addWidget(self.record_btn)
        
        # 导出按钮
        self.export_btn = QPushButton(self.lang_manager.get_text('export'))
        self.export_btn.clicked.connect(self.export_data)
        layout.addWidget(self.export_btn)
        
        layout.addWidget(QLabel("|"))
        
        # 虚拟数据复选框
        self.sdata_checkbox = QCheckBox(self.lang_manager.get_text('virtual_data'))
        self.sdata_checkbox.setToolTip(self.lang_manager.get_text('virtual_data_tooltip'))
        self.sdata_checkbox.stateChanged.connect(self.toggle_virtual_data)
        layout.addWidget(self.sdata_checkbox)
        
        layout.addWidget(QLabel("|"))
        
        # 语言选择
        self.lang_label = QLabel(self.lang_manager.get_text('language'))
        layout.addWidget(self.lang_label)
        
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(['中文', 'English'])
        self.lang_combo.setCurrentIndex(0)
        self.lang_combo.currentIndexChanged.connect(self.change_language)
        layout.addWidget(self.lang_combo)
        
        layout.addWidget(QLabel("|"))
        
        # 情绪状态显示
        emotion_container = QWidget()
        emotion_layout = QVBoxLayout(emotion_container)
        emotion_layout.setContentsMargins(0, 0, 0, 0)
        emotion_layout.setSpacing(2)
        
        self.emotion_title_label = QLabel(self.lang_manager.get_text('emotion_title'))
        self.emotion_title_label.setStyleSheet("font-size: 10px; color: gray;")
        emotion_layout.addWidget(self.emotion_title_label)
        
        self.emotion_label = QLabel(f"😐 {self.lang_manager.get_text('emotion_neutral')}")
        self.emotion_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #666666; "
            "padding: 5px 15px; background-color: #F0F0F0; border-radius: 5px;"
        )
        self.emotion_label.setMinimumWidth(100)
        self.emotion_label.setAlignment(Qt.AlignCenter)
        emotion_layout.addWidget(self.emotion_label)
        
        layout.addWidget(emotion_container)
        
        layout.addWidget(QLabel("|"))
        
        # 上传云端按钮
        self.upload_btn = QPushButton(f'🌐 {self.lang_manager.get_text("upload_start")}')
        self.upload_btn.setStyleSheet(
            "QPushButton { "
            "background-color: #4CAF50; color: white; font-weight: bold; "
            "padding: 5px 15px; border-radius: 5px; font-size: 12px; "
            "} "
            "QPushButton:hover { background-color: #45a049; } "
            "QPushButton:pressed { background-color: #3d8b40; } "
            "QPushButton:disabled { background-color: #cccccc; color: #666666; } "
            "QPushButton:checked { background-color: #f44336; }"
        )
        self.upload_btn.setCheckable(True)  # 设置为可切换按钮
        self.upload_btn.clicked.connect(self.toggle_upload)
        layout.addWidget(self.upload_btn)
        
        layout.addStretch()
        
        # 状态指示
        self.status_label = QLabel(self.lang_manager.get_text('status_disconnected'))
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        # 数据率显示
        self.rate_label = QLabel("0 Hz")
        layout.addWidget(self.rate_label)
        
        group.setLayout(layout)
        return group
        
    def create_plot_area(self):
        """创建图表区域"""
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setSpacing(10)
        
        # 配置pyqtgraph（关闭抗锯齿以提升性能）
        pg.setConfigOptions(antialias=False, useOpenGL=False)
        
        # EEG信号图
        self.eeg_group = QGroupBox(self.lang_manager.get_text('eeg_group'))
        eeg_layout = QVBoxLayout(self.eeg_group)
        self.eeg_plot = pg.PlotWidget()
        self.eeg_plot.setBackground('w')
        self.eeg_plot.setLabel('left', self.lang_manager.get_text('amplitude'), units='μV')
        self.eeg_plot.setLabel('bottom', self.lang_manager.get_text('time'), units='s')
        self.eeg_plot.getAxis('left').enableAutoSIPrefix(False)  # 禁用自动SI前缀
        self.eeg_plot.setTitle('')
        self.eeg_plot.showGrid(x=True, y=True, alpha=0.3)
        self.eeg_plot.setDownsampling(mode='peak')
        self.eeg_plot.setClipToView(True)
        self.eeg_plot.addLegend(offset=(20, 0))
        self.eeg_raw_curve = self.eeg_plot.plot(pen=pg.mkPen(color=(180, 180, 180), width=1), name=self.lang_manager.get_text('raw'))
        self.eeg_filtered_curve = self.eeg_plot.plot(pen=pg.mkPen(color='b', width=2), name=self.lang_manager.get_text('filtered'))
        eeg_layout.addWidget(self.eeg_plot)
        layout.addWidget(self.eeg_group, 0, 0, 1, 2)
        
        # PPG信号图
        self.ppg_group = QGroupBox(self.lang_manager.get_text('ppg_group'))
        ppg_layout = QVBoxLayout(self.ppg_group)
        self.ppg_plot = pg.PlotWidget()
        self.ppg_plot.setBackground('w')
        self.ppg_plot.setLabel('left', self.lang_manager.get_text('amplitude'), units='μV')
        self.ppg_plot.setLabel('bottom', self.lang_manager.get_text('time'), units='s')
        self.ppg_plot.getAxis('left').enableAutoSIPrefix(False)  # 禁用自动SI前缀
        self.ppg_plot.setTitle('')
        self.ppg_plot.showGrid(x=True, y=True, alpha=0.3)
        self.ppg_plot.setDownsampling(mode='peak')
        self.ppg_plot.setClipToView(True)
        self.ppg_plot.addLegend(offset=(20, 0))
        # 红光LED - 原始信号（浅红色）
        self.ppg_red_raw_curve = self.ppg_plot.plot(pen=pg.mkPen(color=(255, 150, 150), width=1), name='Red Raw')
        # 红光LED - 滤波后信号（深红色）
        self.ppg_red_filtered_curve = self.ppg_plot.plot(pen=pg.mkPen(color=(220, 20, 60), width=2), name='Red Filtered')
        # 红外LED - 原始信号（浅紫色）
        self.ppg_ir_raw_curve = self.ppg_plot.plot(pen=pg.mkPen(color=(200, 150, 200), width=1), name='IR Raw')
        # 红外LED - 滤波后信号（深紫色）
        self.ppg_ir_filtered_curve = self.ppg_plot.plot(pen=pg.mkPen(color=(128, 0, 128), width=2), name='IR Filtered')
        ppg_layout.addWidget(self.ppg_plot)
        layout.addWidget(self.ppg_group, 1, 0, 1, 2)
        
        # 四元数/姿态显示
        self.imu_group = QGroupBox(self.lang_manager.get_text('imu_group'))
        imu_layout = QVBoxLayout(self.imu_group)
        self.imu_plot = pg.PlotWidget()
        self.imu_plot.setBackground('w')
        self.imu_plot.setLabel('left', self.lang_manager.get_text('quaternion'))
        self.imu_plot.setLabel('bottom', self.lang_manager.get_text('time'), units='s')
        self.imu_plot.setTitle('')
        self.imu_plot.showGrid(x=True, y=True, alpha=0.3)
        self.imu_plot.setDownsampling(mode='peak')
        self.imu_plot.setClipToView(True)
        self.imu_plot.addLegend(offset=(20, 0))
        self.quat_curves = [
            self.imu_plot.plot(pen=pg.mkPen(color='r', width=2), name='Q0'),
            self.imu_plot.plot(pen=pg.mkPen(color='g', width=2), name='Q1'),
            self.imu_plot.plot(pen=pg.mkPen(color='b', width=2), name='Q2'),
            self.imu_plot.plot(pen=pg.mkPen(color='orange', width=2), name='Q3')
        ]
        imu_layout.addWidget(self.imu_plot)
        layout.addWidget(self.imu_group, 2, 0, 1, 2)
        
        return widget
        
    def create_log_area(self):
        """创建日志区域"""
        self.log_group = QGroupBox(self.lang_manager.get_text('log_area'))
        layout = QVBoxLayout(self.log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        font = QFont("Consolas", 9)
        self.log_text.setFont(font)
        
        layout.addWidget(self.log_text)
        return self.log_group
        
    def init_plots(self):
        """初始化图表"""
        pass
        
    def setup_connections(self):
        """设置信号连接"""
        self.serial_handler.data_received.connect(self.on_data_received)
        self.serial_handler.connection_changed.connect(self.on_connection_changed)
        self.serial_handler.error_occurred.connect(self.on_error)
        
        # 初始刷新串口列表
        self.refresh_ports()
        
    @pyqtSlot()
    def refresh_ports(self):
        """刷新串口列表"""
        ports = self.serial_handler.get_available_ports()
        self.port_combo.clear()
        self.port_combo.addItems(ports)
        
        if ports:
            self.log_message(self.lang_manager.get_text('ports_found').format(len(ports)))
        else:
            self.log_message(self.lang_manager.get_text('no_ports'), 'warning')
            
    @pyqtSlot()
    def toggle_connection(self):
        """切换连接状态"""
        if self.serial_handler.is_connected():
            self.serial_handler.disconnect()
        else:
            port = self.port_combo.currentText()
            baudrate = int(self.baudrate_combo.currentText())
            
            if not port:
                QMessageBox.warning(self, self.lang_manager.get_text('warning'), self.lang_manager.get_text('select_port_warning'))
                return
                
            if self.serial_handler.connect(port, baudrate):
                self.log_message(self.lang_manager.get_text('connected_to').format(port, baudrate), 'success')
                self.update_timer.start()
            else:
                self.log_message(self.lang_manager.get_text('connect_failed').format(port), 'error')
                
    @pyqtSlot(bool)
    def on_connection_changed(self, connected):
        """连接状态改变"""
        if connected:
            self.connect_btn.setText(self.lang_manager.get_text('disconnect'))
            self.connect_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
            self.status_label.setText(self.lang_manager.get_text('status_connected'))
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.pause_btn.setEnabled(True)
            self.port_combo.setEnabled(False)
            self.baudrate_combo.setEnabled(False)
            self.refresh_btn.setEnabled(False)
        else:
            self.connect_btn.setText(self.lang_manager.get_text('connect'))
            self.connect_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            self.status_label.setText(self.lang_manager.get_text('status_disconnected'))
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.pause_btn.setEnabled(False)
            self.port_combo.setEnabled(True)
            self.baudrate_combo.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            self.update_timer.stop()
            
    @pyqtSlot(bytes)
    def on_data_received(self, data):
        """接收到数据"""
        parsed_data = self.data_parser.parse(data)
        
        if parsed_data:
            # 如果启用虚拟数据，替换EEG和PPG数据
            if self.use_virtual_data and self.virtual_eeg_data is not None:
                parsed_data = self.apply_virtual_data(parsed_data)
            
            # 添加到缓冲区
            self.data_buffer.add_data(parsed_data)
            
            # 如果正在录制，保存数据
            if self.data_recorder and self.data_recorder.is_recording:
                self.data_recorder.add_data(parsed_data)
                
    def median_filter(self, data, kernel_size=5):
        """中值滤波，去除脉冲噪声"""
        if len(data) < kernel_size:
            return data
        try:
            return signal.medfilt(data, kernel_size=kernel_size)
        except:
            return data
    
    def gaussian_smooth(self, data, sigma=2):
        """高斯平滑"""
        if len(data) < 10:
            return data
        try:
            # 生成高斯窗口
            window_size = int(6 * sigma)
            if window_size % 2 == 0:
                window_size += 1
            x = np.arange(window_size) - window_size // 2
            gauss = np.exp(-(x**2) / (2 * sigma**2))
            gauss = gauss / gauss.sum()
            return np.convolve(data, gauss, mode='same')
        except:
            return data
    
    def apply_filter(self, data, sos_filter, min_length=30):
        """应用滤波器"""
        if len(data) < min_length:
            return data
        try:
            filtered = signal.sosfiltfilt(sos_filter, data)
            return filtered
        except:
            return data
    
    def savitzky_golay_filter(self, data, window_length=21, polyorder=3):
        """Savitzky-Golay平滑滤波（保留峰值特征）"""
        if len(data) < window_length:
            return data
        try:
            # 确保window_length是奇数
            if window_length % 2 == 0:
                window_length += 1
            return signal.savgol_filter(data, window_length, polyorder)
        except:
            return data
    
    def resample_uniform(self, timestamps, data, target_rate=500):
        """重采样到均匀时间序列，消除采样率抖动"""
        if len(timestamps) < 10 or len(data) < 10:
            return timestamps, data
        try:
            # 创建均匀时间轴
            t_start = timestamps[0]
            t_end = timestamps[-1]
            duration = t_end - t_start
            if duration <= 0:
                return timestamps, data
            
            # 计算目标采样点数
            num_samples = int(duration * target_rate)
            if num_samples < 10:
                return timestamps, data
            
            # 均匀时间轴
            t_uniform = np.linspace(t_start, t_end, num_samples)
            
            # 使用三次样条插值重采样
            f = interpolate.interp1d(timestamps, data, kind='cubic', 
                                    bounds_error=False, fill_value='extrapolate')
            data_uniform = f(t_uniform)
            
            return t_uniform, data_uniform
        except:
            return timestamps, data
    
    @pyqtSlot()
    def update_plots(self):
        """更新图表显示（优化版：减少计算量）"""
        if self.is_paused:
            return
        
        self.plot_update_counter += 1
            
        data = self.data_buffer.get_all_data()
        if not data:
            return
        
        # 仅使用最近的数据点进行绘图（最多2500点 = 5秒 @ 500Hz）
        max_points = 2500
        if len(data) > max_points:
            data = data[-max_points:]
            
        # 更新数据率显示（每5次更新一次，减少UI操作）
        if self.plot_update_counter % 5 == 0:
            self.rate_label.setText("500 Hz")
        
        # 获取时间轴
        timestamps = self.data_buffer.get_timestamps()
        if not timestamps:
            return
        if len(timestamps) > max_points:
            timestamps = timestamps[-max_points:]
        
        # 预计算通用变量
        current_time = timestamps[-1]
        start_time = current_time - self.display_window
        timestamps_arr = np.array(timestamps)
        mask = timestamps_arr >= start_time
        time_window = timestamps_arr[mask]
        relative_time = time_window - start_time
        
        # 更新EEG图（原始信号 + 滤波信号）
        eeg_data = np.array([d.get('ads1118', 0) for d in data])
        if len(eeg_data) > 50:
            eeg_window = eeg_data[mask] if len(eeg_data) == len(mask) else eeg_data[-len(mask):][mask[-len(eeg_data):]]
            
            if len(eeg_window) > 50:
                # 应用放大倍数（如果不是虚拟数据）
                if not self.use_virtual_data:
                    eeg_window = eeg_window * self.eeg_scale_factor
                
                # 原始信号（去直流）
                eeg_raw = eeg_window - np.mean(eeg_window)
                
                # 滤波信号（1-40Hz带通）
                eeg_filtered = self.apply_filter(eeg_raw, self.eeg_sos, min_length=50)
                
                # 绘制信号
                self.eeg_raw_curve.setData(relative_time[:len(eeg_raw)], eeg_raw)
                self.eeg_filtered_curve.setData(relative_time[:len(eeg_filtered)], eeg_filtered)
                
                # 固定X轴范围为0-5秒（仅偶尔更新Y轴范围，减少计算）
                self.eeg_plot.setXRange(0, self.display_window, padding=0)
                if self.plot_update_counter % 3 == 0:
                    y_max = max(np.max(np.abs(eeg_raw)), np.max(np.abs(eeg_filtered))) * 1.1
                    self.eeg_plot.setYRange(-y_max, y_max, padding=0)
            
        # 更新PPG图（红光和红外光两条独立波形）
        ppg_red = np.array([d.get('red_led', 0) for d in data])
        ppg_ir = np.array([d.get('ir_led', 0) for d in data])
        
        if len(ppg_red) > 50 and len(ppg_ir) > 50:
            ppg_red_window = ppg_red[mask] if len(ppg_red) == len(mask) else ppg_red[-len(mask):][mask[-len(ppg_red):]]
            ppg_ir_window = ppg_ir[mask] if len(ppg_ir) == len(mask) else ppg_ir[-len(mask):][mask[-len(ppg_ir):]]
            
            if len(ppg_red_window) > 50 and len(ppg_ir_window) > 50:
                # 应用缩放倍数（仅对实时数据）
                if not self.use_virtual_data:
                    ppg_red_window = ppg_red_window * self.ppg_scale_factor
                    ppg_ir_window = ppg_ir_window * self.ppg_scale_factor
                
                # 红光 - 原始信号（去直流）
                ppg_red_raw = ppg_red_window - np.mean(ppg_red_window)
                # 红光 - 滤波信号（0.5-8Hz带通）
                ppg_red_filtered = self.apply_filter(ppg_red_raw, self.ppg_sos, min_length=50)
                
                # 红外光 - 原始信号（去直流）
                ppg_ir_raw = ppg_ir_window - np.mean(ppg_ir_window)
                # 红外光 - 滤波信号（0.5-8Hz带通）
                ppg_ir_filtered = self.apply_filter(ppg_ir_raw, self.ppg_sos, min_length=50)
                
                # 绘制红光信号
                rel_time_ppg = relative_time[:len(ppg_red_raw)]
                self.ppg_red_raw_curve.setData(rel_time_ppg, ppg_red_raw)
                self.ppg_red_filtered_curve.setData(rel_time_ppg, ppg_red_filtered)
                # 绘制红外光信号
                self.ppg_ir_raw_curve.setData(rel_time_ppg, ppg_ir_raw)
                self.ppg_ir_filtered_curve.setData(rel_time_ppg, ppg_ir_filtered)
                
                # 固定X轴范围为0-5秒
                self.ppg_plot.setXRange(0, self.display_window, padding=0)
                if self.plot_update_counter % 3 == 0:
                    y_max = max(np.max(np.abs(ppg_red_raw)), np.max(np.abs(ppg_ir_raw))) * 1.1
                    self.ppg_plot.setYRange(-y_max, y_max, padding=0)
            
        # 更新四元数图（固定5秒窗）
        quat_data = [d.get('quat', [0, 0, 0, 0]) for d in data]
        if quat_data:
            quat_array = np.array(quat_data)
            quat_window = quat_array[mask] if len(quat_array) == len(mask) else quat_array[-len(mask):][mask[-len(quat_array):]]
            
            if len(quat_window) > 5:
                rel_time_imu = relative_time[:len(quat_window)]
                # 每个四元数分量去除均值，并做简单移动平均平滑
                for i in range(4):
                    quat_component = quat_window[:, i]
                    quat_ac = quat_component - np.mean(quat_component)
                    # 简单的5点移动平均
                    if len(quat_ac) >= 5:
                        quat_smooth = np.convolve(quat_ac, np.ones(5)/5, mode='same')
                    else:
                        quat_smooth = quat_ac
                    
                    self.quat_curves[i].setData(rel_time_imu[:len(quat_smooth)], quat_smooth)
                
                # 固定X轴范围
                self.imu_plot.setXRange(0, self.display_window, padding=0)
                
    @pyqtSlot()
    def toggle_pause(self):
        """暂停/继续显示"""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_btn.setText(self.lang_manager.get_text('continue'))
            self.log_message(self.lang_manager.get_text('paused'))
        else:
            self.pause_btn.setText(self.lang_manager.get_text('pause'))
            self.log_message(self.lang_manager.get_text('continued'))
            
    @pyqtSlot()
    def clear_data(self):
        """清空数据"""
        reply = QMessageBox.question(self, self.lang_manager.get_text('confirm'), self.lang_manager.get_text('confirm_clear'),
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.data_buffer.clear()
            self.log_message(self.lang_manager.get_text('data_cleared'))
            
    @pyqtSlot()
    def toggle_recording(self):
        """切换录制状态"""
        if self.data_recorder and self.data_recorder.is_recording:
            # 停止录制
            filename = self.data_recorder.stop_recording()
            self.record_btn.setText(self.lang_manager.get_text('record'))
            self.record_btn.setStyleSheet("")
            self.log_message(self.lang_manager.get_text('recording_stopped').format(filename), 'success')
            self.data_recorder = None
        else:
            # 开始录制
            self.data_recorder = DataRecorder()
            self.data_recorder.start_recording()
            self.record_btn.setText(self.lang_manager.get_text('stop'))
            self.record_btn.setStyleSheet("background-color: #f44336; color: white;")
            self.log_message(self.lang_manager.get_text('recording_started'), 'success')
            
    @pyqtSlot()
    def export_data(self):
        """导出数据"""
        if not self.data_buffer.get_all_data():
            QMessageBox.warning(self, self.lang_manager.get_text('warning'), self.lang_manager.get_text('no_data_export'))
            return
            
        filename, _ = QFileDialog.getSaveFileName(
            self, self.lang_manager.get_text('export_data_title'), 
            f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            self.lang_manager.get_text('csv_files')
        )
        
        if filename:
            from utils.file_utils import export_to_csv
            if export_to_csv(self.data_buffer.get_all_data(), filename):
                self.log_message(self.lang_manager.get_text('data_exported').format(filename), 'success')
            else:
                self.log_message(self.lang_manager.get_text('export_failed'), 'error')
                
    @pyqtSlot(str)
    def on_error(self, error_msg):
        """处理错误"""
        self.log_message(error_msg, 'error')
        QMessageBox.critical(self, "错误", error_msg)
        
    def toggle_virtual_data(self, state):
        """切换虚拟数据模式"""
        if state == Qt.Checked:
            # 启用虚拟数据
            if self.load_virtual_data():
                self.use_virtual_data = True
                self.virtual_data_index = 0
                self.virtual_start_time = None  # 重置虚拟时间
                self.log_message(self.lang_manager.get_text('virtual_enabled'), 'success')
            else:
                self.sdata_checkbox.setChecked(False)
                self.use_virtual_data = False
                self.log_message(self.lang_manager.get_text('virtual_load_failed'), 'error')
        else:
            # 禁用虚拟数据
            self.use_virtual_data = False
            self.virtual_data_index = 0
            self.virtual_start_time = None
            self.log_message(self.lang_manager.get_text('virtual_disabled'), 'info')
    
    def load_virtual_data(self):
        """加载BrainVision虚拟数据"""
        try:
            # 数据文件路径（使用相对路径）
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(current_dir, "data")
            vhdr_file = os.path.join(data_dir, "mzy_0918_1.vhdr")
            
            # 检查文件是否存在
            if not os.path.exists(vhdr_file):
                QMessageBox.warning(self, self.lang_manager.get_text('warning'), self.lang_manager.get_text('virtual_file_not_found').format(vhdr_file))
                return False
            
            self.log_message(self.lang_manager.get_text('loading_virtual'), 'info')
            
            # 读取 BrainVision 数据
            raw = mne.io.read_raw_brainvision(vhdr_file, preload=True, verbose=False)
            
            # 获取采样率
            self.virtual_sample_rate = raw.info['sfreq']
            
            # 提取 Fp1 和 Fp2 通道，先滤波再计算平均值
            if 'Fp1' in raw.ch_names and 'Fp2' in raw.ch_names:
                # 对Fp1和Fp2进行1-40Hz带通滤波
                raw_eeg = raw.copy()
                raw_eeg.filter(l_freq=1.0, h_freq=40.0, picks=['Fp1', 'Fp2'], verbose=False)
                
                # 重采样到500Hz（使用MNE的resample方法，带抗混叠滤波）
                raw_eeg.resample(sfreq=500.0, verbose=False)
                
                fp1_data = raw_eeg.get_data(picks=['Fp1'])[0]
                fp2_data = raw_eeg.get_data(picks=['Fp2'])[0]
                eeg_filtered = (fp1_data + fp2_data) / 2.0
                
                # 将V转换为μV（1V = 1,000,000 μV）
                self.virtual_eeg_data = eeg_filtered * 1000000
                
                # 更新采样率为500Hz
                self.virtual_sample_rate = 500
                
                # 打印数据范围用于调试
                eeg_min = np.min(self.virtual_eeg_data)
                eeg_max = np.max(self.virtual_eeg_data)
                eeg_mean = np.mean(self.virtual_eeg_data)
                eeg_std = np.std(self.virtual_eeg_data)
                self.log_message(self.lang_manager.get_text('eeg_range').format(eeg_min, eeg_max, eeg_mean, eeg_std), 'info')
                self.log_message(self.lang_manager.get_text('eeg_loaded').format(len(self.virtual_eeg_data)), 'success')
            else:
                QMessageBox.warning(self, self.lang_manager.get_text('warning'), self.lang_manager.get_text('virtual_no_fp1_fp2'))
                return False
            
            # 提取 PPG 通道并滤波
            if 'PPG' in raw.ch_names:
                # 对PPG进行0.5-8Hz带通滤波
                raw_ppg = raw.copy()
                raw_ppg.filter(l_freq=0.5, h_freq=8.0, picks=['PPG'], verbose=False)
                
                # 重采样到500Hz（使用MNE的resample方法，带抗混叠滤波）
                raw_ppg.resample(sfreq=500.0, verbose=False)
                
                ppg_filtered = raw_ppg.get_data(picks=['PPG'])[0]
                
                # 将V转换为μV（1V = 1,000,000 μV）
                self.virtual_ppg_data = ppg_filtered * 1000000
                
                # 打印数据范围用于调试
                ppg_min = np.min(self.virtual_ppg_data)
                ppg_max = np.max(self.virtual_ppg_data)
                ppg_mean = np.mean(self.virtual_ppg_data)
                ppg_std = np.std(self.virtual_ppg_data)
                self.log_message(self.lang_manager.get_text('ppg_range').format(ppg_min, ppg_max, ppg_mean, ppg_std), 'info')
                self.log_message(self.lang_manager.get_text('ppg_loaded').format(len(self.virtual_ppg_data)), 'success')
            else:
                QMessageBox.warning(self, self.lang_manager.get_text('warning'), self.lang_manager.get_text('virtual_no_ppg'))
                return False
            
            self.log_message(self.lang_manager.get_text('virtual_loaded').format(self.virtual_sample_rate), 'success')
            return True
            
        except Exception as e:
            QMessageBox.critical(self, self.lang_manager.get_text('error'), self.lang_manager.get_text('virtual_load_error').format(str(e)))
            self.log_message(self.lang_manager.get_text('virtual_load_error').format(str(e)), 'error')
            return False
    
    def apply_virtual_data(self, parsed_data):
        """应用虚拟数据到解析的数据包"""
        if self.virtual_eeg_data is None or self.virtual_ppg_data is None:
            return parsed_data
        
        # 初始化虚拟时间
        if self.virtual_start_time is None:
            self.virtual_start_time = datetime.now()
        
        # 数据已经重采样到500Hz，直接使用索引
        virtual_index = self.virtual_data_index % len(self.virtual_eeg_data)
        
        # 替换 EEG 数据 (ads1118)
        if 'ads1118' in parsed_data:
            # 使用已滤波和放大的EEG数据
            eeg_value = self.virtual_eeg_data[virtual_index]
            parsed_data['ads1118'] = int(eeg_value)
        
        # 替换 PPG 数据 (red_led 和 ir_led)
        # 将单个PPG通道分成红光和红外光，模拟真实的光学特性差异
        if 'red_led' in parsed_data or 'ir_led' in parsed_data:
            # 使用已滤波和放大的PPG数据
            ppg_value = self.virtual_ppg_data[virtual_index]
            
            if 'red_led' in parsed_data:
                # 红光LED：幅度较大（对含氧血红蛋白更敏感，AC/DC比更高）
                # 添加随机噪声：约2%的高斯噪声，模拟测量误差
                noise_red = np.random.normal(0, abs(ppg_value) * 0.02)
                parsed_data['red_led'] = int(ppg_value * 1.3 + noise_red)
            if 'ir_led' in parsed_data:
                # 红外LED：幅度较小（信号更稳定）
                # 添加较小的随机噪声：约1.5%的高斯噪声（红外光更稳定）
                noise_ir = np.random.normal(0, abs(ppg_value) * 0.015)
                parsed_data['ir_led'] = int(ppg_value * 0.9 + noise_ir)
        
        # 替换时间戳为均匀的虚拟时间戳（模拟500Hz采样）
        from datetime import timedelta
        virtual_time = self.virtual_start_time + timedelta(seconds=self.virtual_data_index * self.virtual_time_interval)
        parsed_data['timestamp'] = virtual_time
        
        # 姿态数据保持不变（使用真实数据）
        # 'quat' 数据不修改
        
        # 更新索引（循环播放）
        self.virtual_data_index = (self.virtual_data_index + 1) % len(self.virtual_eeg_data)
        
        return parsed_data
    
    def toggle_upload(self):
        """切换云端上传状态"""
        if self.upload_btn.isChecked():
            # 开始上传
            self.start_upload()
        else:
            # 停止上传
            self.stop_upload()
    
    def start_upload(self):
        """开始持续上传数据到云端"""
        # 检查是否有数据
        data = self.data_buffer.get_all_data()
        if len(data) < 500:
            self.log_message(self.lang_manager.get_text('upload_insufficient_data'), 'warning')
            self.upload_btn.setChecked(False)
            return
        
        self.is_uploading = True
        self.upload_btn.setText(f'⏸ {self.lang_manager.get_text("upload_stop")}')
        self.upload_btn.setStyleSheet(
            "QPushButton { "
            "background-color: #f44336; color: white; font-weight: bold; "
            "padding: 5px 15px; border-radius: 5px; font-size: 12px; "
            "} "
            "QPushButton:hover { background-color: #da190b; }"
        )
        
        # 立即上传一次
        self.upload_data_to_cloud()
        
        # 启动定时器持续上传
        self.upload_timer.start(self.upload_interval)
        self.log_message(f"✅ 开始持续上传，每{self.upload_interval/1000}秒上传一次", 'success')
    
    def stop_upload(self):
        """停止上传"""
        self.is_uploading = False
        self.upload_timer.stop()
        self.upload_btn.setText(f'🌐 {self.lang_manager.get_text("upload_start")}')
        self.upload_btn.setStyleSheet(
            "QPushButton { "
            "background-color: #4CAF50; color: white; font-weight: bold; "
            "padding: 5px 15px; border-radius: 5px; font-size: 12px; "
            "} "
            "QPushButton:hover { background-color: #45a049; }"
        )
        self.log_message(f"⏹ {self.lang_manager.get_text('upload_stopped')}", 'info')
    
    def upload_data_to_cloud(self):
        """上传数据到云端服务器进行情绪识别"""
        if not self.is_uploading:
            return
        
        try:
            # 获取所有数据
            data = self.data_buffer.get_all_data()
            if len(data) < 100:
                return
            
            # 如果上一个上传任务还在进行中，跳过本次
            if self.upload_worker is not None and self.upload_worker.isRunning():
                return
            
            # 提取最近5秒的数据
            data_to_send = data[-2500:] if len(data) > 2500 else data
            
            # 准备上传数据
            upload_data = {
                "timestamp": datetime.now().isoformat(),
                "sample_rate": self.sample_rate,
                "data_length": len(data_to_send),
                "eeg_data": [d.get('ads1118', 0) for d in data_to_send],
                "ppg_red_data": [d.get('red_led', 0) for d in data_to_send],
                "ppg_ir_data": [d.get('ir_led', 0) for d in data_to_send],
                "imu_data": [d.get('quat', [0, 0, 0, 0]) for d in data_to_send]
            }
            
            # 创建后台上传线程
            self.upload_worker = UploadWorker(self.cloud_server_url, upload_data, timeout=5)
            self.upload_worker.upload_success.connect(self.on_upload_success)
            self.upload_worker.upload_error.connect(self.on_upload_error)
            self.upload_worker.start()
                
        except Exception as e:
            self.log_message(f"⚠ {self.lang_manager.get_text('upload_failed').format(str(e))}", 'warning')
    
    @pyqtSlot(str, float)
    def on_upload_success(self, emotion, confidence):
        """上传成功回调"""
        # 获取情绪的翻译文本用于日志显示
        emotion_map = {
            'happy': 'emotion_happy', 'sad': 'emotion_sad', 'neutral': 'emotion_neutral'
        }
        emotion_key = emotion_map.get(emotion.lower(), 'emotion_neutral')
        emotion_text = self.lang_manager.get_text(emotion_key)
        
        self.update_emotion_display(emotion)
        self.log_message(f"✅ {self.lang_manager.get_text('upload_emotion_result').format(emotion_text, confidence)}", 'success')
    
    @pyqtSlot(str)
    def on_upload_error(self, error_type):
        """上传错误回调"""
        if error_type == "timeout":
            self.log_message(f"⚠ {self.lang_manager.get_text('upload_timeout')}", 'warning')
        elif error_type == "connection_error":
            self.log_message(f"⚠ {self.lang_manager.get_text('upload_connection_error')}", 'warning')
            # 连接失败时自动停止
            self.upload_btn.setChecked(False)
            self.stop_upload()
        elif error_type.startswith("server_error:"):
            status_code = error_type.split(":")[1]
            self.log_message(f"⚠ {self.lang_manager.get_text('upload_server_error').format(status_code)}", 'warning')
        else:
            error_msg = error_type.replace("error:", "")
            self.log_message(f"⚠ {self.lang_manager.get_text('upload_failed').format(error_msg)}", 'warning')
    
    def update_emotion_display(self, emotion):
        """更新情绪状态显示"""
        # 将服务器返回的情绪映射到标准key
        emotion_map = {
            '开心': 'happy', 'happy': 'happy', 'Happy': 'happy',
            '悲伤': 'sad', 'sad': 'sad', 'Sad': 'sad',
            '中性': 'neutral', 'neutral': 'neutral', 'Neutral': 'neutral'
        }
        emotion_key = emotion_map.get(emotion, 'neutral')
        self.current_emotion = emotion_key
        
        # 获取情绪显示配置
        style_config = EMOTION_DISPLAY_CONFIG.get(emotion_key, EMOTION_DISPLAY_CONFIG.get("neutral"))
        emotion_text = self.lang_manager.get_text(style_config['lang_key'])
        
        self.emotion_label.setText(f"{style_config['icon']} {emotion_text}")
        self.emotion_label.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {style_config['color']}; "
            f"padding: 5px 15px; background-color: {style_config['bg_color']}; border-radius: 5px;"
        )
    
    def log_message(self, message, level='info'):
        """添加日志消息"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        color_map = {
            'info': 'black',
            'success': 'green',
            'warning': 'orange',
            'error': 'red'
        }
        
        color = color_map.get(level, 'black')
        formatted_msg = f'<span style="color: {color};">[{timestamp}] {message}</span>'
        
        self.log_text.append(formatted_msg)
    
    def change_language(self, index):
        """切换语言"""
        lang_map = {0: 'zh_CN', 1: 'en_US'}
        new_lang = lang_map.get(index, 'zh_CN')
        
        if self.lang_manager.set_language(new_lang):
            self.update_ui_language()
    
    def update_ui_language(self):
        """更新界面语言"""
        # 更新窗口标题
        self.setWindowTitle(self.lang_manager.get_text('window_title'))
        
        # 更新控制面板
        self.findChild(QGroupBox).setTitle(self.lang_manager.get_text('control_panel'))
        self.port_label.setText(self.lang_manager.get_text('serial_port'))
        self.refresh_btn.setText(self.lang_manager.get_text('refresh'))
        self.baudrate_label.setText(self.lang_manager.get_text('baudrate'))
        
        # 更新连接按钮
        if self.serial_handler.is_connected():
            self.connect_btn.setText(self.lang_manager.get_text('disconnect'))
            self.status_label.setText(self.lang_manager.get_text('status_connected'))
        else:
            self.connect_btn.setText(self.lang_manager.get_text('connect'))
            self.status_label.setText(self.lang_manager.get_text('status_disconnected'))
        
        # 更新暂停按钮
        if self.is_paused:
            self.pause_btn.setText(self.lang_manager.get_text('continue'))
        else:
            self.pause_btn.setText(self.lang_manager.get_text('pause'))
        
        self.clear_btn.setText(self.lang_manager.get_text('clear'))
        
        # 更新录制按钮
        if self.data_recorder and self.data_recorder.is_recording:
            self.record_btn.setText(self.lang_manager.get_text('stop'))
        else:
            self.record_btn.setText(self.lang_manager.get_text('record'))
        
        self.export_btn.setText(self.lang_manager.get_text('export'))
        self.sdata_checkbox.setText(self.lang_manager.get_text('virtual_data'))
        self.sdata_checkbox.setToolTip(self.lang_manager.get_text('virtual_data_tooltip'))
        self.lang_label.setText(self.lang_manager.get_text('language'))
        
        # 更新上传按钮
        if self.upload_btn.isChecked():
            self.upload_btn.setText(self.lang_manager.get_text('upload_stop'))
        else:
            self.upload_btn.setText(self.lang_manager.get_text('upload_start'))
        
        # 更新情绪状态显示
        self.emotion_title_label.setText(self.lang_manager.get_text('emotion_title'))
        self.update_emotion_display(self.current_emotion)
        
        # 更新图表组框
        self.eeg_group.setTitle(self.lang_manager.get_text('eeg_group'))
        self.ppg_group.setTitle(self.lang_manager.get_text('ppg_group'))
        self.imu_group.setTitle(self.lang_manager.get_text('imu_group'))
        
        # 更新图表标签
        self.eeg_plot.setLabel('left', self.lang_manager.get_text('amplitude'), units='μV')
        self.eeg_plot.setLabel('bottom', self.lang_manager.get_text('time'), units='s')
        self.ppg_plot.setLabel('left', self.lang_manager.get_text('amplitude'), units='μV')
        self.ppg_plot.setLabel('bottom', self.lang_manager.get_text('time'), units='s')
        self.imu_plot.setLabel('left', self.lang_manager.get_text('quaternion'))
        self.imu_plot.setLabel('bottom', self.lang_manager.get_text('time'), units='s')
        
        # 更新图例（需要重新创建曲线来更新图例）
        # 清除并重新添加EEG图例
        self.eeg_plot.plotItem.legend.removeItem(self.eeg_raw_curve)
        self.eeg_plot.plotItem.legend.removeItem(self.eeg_filtered_curve)
        self.eeg_plot.plotItem.legend.addItem(self.eeg_raw_curve, self.lang_manager.get_text('raw'))
        self.eeg_plot.plotItem.legend.addItem(self.eeg_filtered_curve, self.lang_manager.get_text('filtered'))
        
        # 清除并重新添加PPG图例
        self.ppg_plot.plotItem.legend.removeItem(self.ppg_ir_raw_curve)
        self.ppg_plot.plotItem.legend.removeItem(self.ppg_ir_filtered_curve)
        self.ppg_plot.plotItem.legend.addItem(self.ppg_ir_raw_curve, self.lang_manager.get_text('raw'))
        self.ppg_plot.plotItem.legend.addItem(self.ppg_ir_filtered_curve, self.lang_manager.get_text('filtered'))
        
        # 更新日志区域
        self.log_group.setTitle(self.lang_manager.get_text('log_area'))
        
    def closeEvent(self, event):
        """关闭窗口事件"""
        if self.serial_handler.is_connected():
            reply = QMessageBox.question(
                self, self.lang_manager.get_text('confirm'),
                self.lang_manager.get_text('confirm_exit'),
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                if self.data_recorder and self.data_recorder.is_recording:
                    self.data_recorder.stop_recording()
                self.serial_handler.disconnect()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
