"""
语言配置模块
支持中英文切换
"""

class LanguageManager:
    """语言管理器"""
    
    # 语言配置字典
    LANGUAGES = {
        'zh_CN': {
            # 窗口标题
            'window_title': '生理信号采集系统 v1.0',
            'app_name': '生理信号采集系统',
            
            # 控制面板
            'control_panel': '控制面板',
            'serial_port': '串口:',
            'refresh': '刷新',
            'baudrate': '波特率:',
            'connect': '连接',
            'disconnect': '断开',
            'pause': '暂停',
            'continue': '继续',
            'clear': '清空',
            'record': '录制',
            'stop': '停止',
            'export': '导出',
            'virtual_data': '数据源',
            'virtual_data_tooltip': '切换数据来源',
            'status_disconnected': '未连接',
            'status_connected': '已连接',
            'language': '语言:',
            
            # 图表组框
            'eeg_group': 'EEG',
            'ppg_group': 'PPG',
            'imu_group': 'IMU',
            
            # 图表标签
            'amplitude': '幅值',
            'time': '时间',
            'quaternion': '四元数',
            'raw': '原始',
            'filtered': '滤波',
            
            # 日志区域
            'log_area': '日志',
            
            # 消息提示
            'system_init': '系统初始化完成',
            'ports_found': '发现 {0} 个可用串口',
            'no_ports': '未发现可用串口',
            'select_port_warning': '请选择串口!',
            'connected_to': '已连接到 {0} @ {1} bps',
            'connect_failed': '连接失败: {0}',
            'paused': '已暂停',
            'continued': '已继续',
            'data_cleared': '数据已清空',
            'recording_started': '开始录制',
            'recording_stopped': '录制已停止: {0}',
            'no_data_export': '没有数据可以导出!',
            'data_exported': '数据已导出到: {0}',
            'export_failed': '数据导出失败!',
            'virtual_enabled': '数据源已切换',
            'virtual_disabled': '数据源已切换',
            'virtual_load_failed': '数据源加载失败',
            'loading_virtual': '正在加载数据源...',
            'virtual_file_not_found': '数据源文件不存在:\n{0}',
            'virtual_no_fp1_fp2': '数据源中未找到 Fp1 或 Fp2 通道',
            'virtual_no_ppg': '数据源中未找到 PPG 通道',
            'virtual_load_error': '加载数据时出错:\n{0}',
            'virtual_loaded': '数据源已加载 (采样率: {0} Hz)',
            'eeg_range': 'EEG数据范围: [{0:.1f}, {1:.1f}] μV, 均值: {2:.1f} μV, 标准差: {3:.1f} μV',
            'ppg_range': 'PPG数据范围: [{0:.1f}, {1:.1f}] μV, 均值: {2:.1f} μV, 标准差: {3:.1f} μV',
            'eeg_loaded': '已加载EEG数据, 长度: {0} 点',
            'ppg_loaded': '已加载PPG数据, 长度: {0} 点',
            
            # 情绪状态
            'emotion_title': '当前情绪状态',
            'emotion_happy': '开心',
            'emotion_sad': '悲伤',
            'emotion_neutral': '中性',
            'emotion_unknown': '未知',
            
            # 云端上传
            'upload_start': '开始上传',
            'upload_stop': '停止上传',
            'upload_started': '已开始持续上传，每{0}秒上传一次',
            'upload_stopped': '已停止上传',
            'upload_insufficient_data': '数据不足，请至少采集1秒数据后再上传',
            'upload_emotion_result': '情绪: {0} (置信度: {1:.1%})',
            'upload_server_error': '服务器错误: {0}',
            'upload_timeout': '连接超时',
            'upload_connection_error': '无法连接到服务器',
            'upload_failed': '上传失败: {0}',
            'upload_stop': '停止上传',
            'upload_started': '已开始持续上传，每{0}秒上传一次',
            'upload_stopped': '已停止上传',
            'upload_insufficient_data': '数据不足，请至少采集1秒数据后再上传',
            'upload_emotion_result': '情绪: {0} (置信度: {1:.1%})',
            'upload_server_error': '服务器错误: {0}',
            'upload_timeout': '连接超时',
            'upload_connection_error': '无法连接到服务器',
            'upload_failed': '上传失败: {0}',
            
            # 对话框
            'warning': '警告',
            'error': '错误',
            'confirm': '确认',
            'confirm_clear': '确定要清空所有数据吗?',
            'confirm_exit': '串口仍在连接中，确定要退出吗?',
            'export_data_title': '导出数据',
            'csv_files': 'CSV Files (*.csv);;All Files (*)',
        },
        'en_US': {
            # Window title
            'window_title': 'Physiological Signal Acquisition System v1.0',
            'app_name': 'Physiological Signal System',
            
            # Control panel
            'control_panel': 'Control Panel',
            'serial_port': 'Port:',
            'refresh': 'Refresh',
            'baudrate': 'Baudrate:',
            'connect': 'Connect',
            'disconnect': 'Disconnect',
            'pause': 'Pause',
            'continue': 'Continue',
            'clear': 'Clear',
            'record': 'Record',
            'stop': 'Stop',
            'export': 'Export',
            'virtual_data': 'Data Source',
            'virtual_data_tooltip': 'Switch data source',
            'status_disconnected': 'Disconnected',
            'status_connected': 'Connected',
            'language': 'Language:',
            
            # Chart groups
            'eeg_group': 'EEG',
            'ppg_group': 'PPG',
            'imu_group': 'IMU',
            
            # Chart labels
            'amplitude': 'Amplitude',
            'time': 'Time',
            'quaternion': 'Quaternion',
            'raw': 'Raw',
            'filtered': 'Filtered',
            
            # Log area
            'log_area': 'Log',
            
            # Messages
            'system_init': 'System initialized',
            'ports_found': 'Found {0} available port(s)',
            'no_ports': 'No ports found',
            'select_port_warning': 'Please select a port!',
            'connected_to': 'Connected to {0} @ {1} bps',
            'connect_failed': 'Connection failed: {0}',
            'paused': 'Paused',
            'continued': 'Continued',
            'data_cleared': 'Data cleared',
            'recording_started': 'Recording started',
            'recording_stopped': 'Recording stopped: {0}',
            'no_data_export': 'No data to export!',
            'data_exported': 'Data exported to: {0}',
            'export_failed': 'Export failed!',
            'virtual_enabled': 'Data source switched',
            'virtual_disabled': 'Data source switched',
            'virtual_load_failed': 'Failed to load data source',
            'loading_virtual': 'Loading data source...',
            'virtual_file_not_found': 'Data source file not found:\n{0}',
            'virtual_no_fp1_fp2': 'Fp1 or Fp2 channel not found in data source',
            'virtual_no_ppg': 'PPG channel not found in data source',
            'virtual_load_error': 'Error loading data:\n{0}',
            'virtual_loaded': 'Data source loaded (Sample rate: {0} Hz)',
            'eeg_range': 'EEG range: [{0:.1f}, {1:.1f}] μV, mean: {2:.1f} μV, std: {3:.1f} μV',
            'ppg_range': 'PPG range: [{0:.1f}, {1:.1f}] μV, mean: {2:.1f} μV, std: {3:.1f} μV',
            'eeg_loaded': 'EEG data loaded, length: {0} pts',
            'ppg_loaded': 'PPG data loaded, length: {0} pts',
            
            # Emotion status
            'emotion_title': 'Emotion Status',
            'emotion_happy': 'Happy',
            'emotion_sad': 'Sad',
            'emotion_neutral': 'Neutral',
            'emotion_unknown': 'Unknown',
            
            # Cloud upload
            'upload_start': 'Start Upload',
            'upload_stop': 'Stop Upload',
            'upload_started': 'Upload started, every {0}s',
            'upload_stopped': 'Upload stopped',
            'upload_insufficient_data': 'Insufficient data, please collect at least 1 second',
            'upload_emotion_result': 'Emotion: {0} (Confidence: {1:.1%})',
            'upload_server_error': 'Server error: {0}',
            'upload_timeout': 'Connection timeout',
            'upload_connection_error': 'Cannot connect to server',
            'upload_failed': 'Upload failed: {0}',
            'upload_stopped': 'Upload stopped',
            'upload_insufficient_data': 'Insufficient data, please collect at least 1 second',
            'upload_emotion_result': 'Emotion: {0} (Confidence: {1:.1%})',
            'upload_server_error': 'Server error: {0}',
            'upload_timeout': 'Connection timeout',
            'upload_connection_error': 'Cannot connect to server',
            'upload_failed': 'Upload failed: {0}',
            
            # Dialogs
            'warning': 'Warning',
            'error': 'Error',
            'confirm': 'Confirm',
            'confirm_clear': 'Are you sure you want to clear all data?',
            'confirm_exit': 'Serial port is still connected. Are you sure you want to exit?',
            'export_data_title': 'Export Data',
            'csv_files': 'CSV Files (*.csv);;All Files (*)',
        }
    }
    
    def __init__(self, default_lang='zh_CN'):
        """初始化语言管理器"""
        self.current_language = default_lang
    
    def get_text(self, key):
        """获取指定键的文本"""
        return self.LANGUAGES.get(self.current_language, {}).get(key, key)
    
    def set_language(self, lang):
        """设置语言"""
        if lang in self.LANGUAGES:
            self.current_language = lang
            return True
        return False
    
    def get_available_languages(self):
        """获取可用语言列表"""
        return {
            'zh_CN': '中文',
            'en_US': 'English'
        }
