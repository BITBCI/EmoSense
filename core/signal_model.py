"""
生理信号模板和形态约束模块
提供EEG和PPG的标准波形模板，用于约束拟合
"""

import numpy as np
from scipy import signal


class PhysiologicalSignalModel:
    """生理信号模型类"""
    
    @staticmethod
    def ppg_template(duration=1.0, sample_rate=500, heart_rate=70):
        """
        生成标准PPG脉搏波形模板
        
        Args:
            duration: 持续时间(秒)
            sample_rate: 采样率
            heart_rate: 心率(bpm)
            
        Returns:
            t, ppg: 时间轴和PPG波形
        """
        t = np.linspace(0, duration, int(duration * sample_rate))
        ppg = np.zeros_like(t)
        
        # 心跳周期
        period = 60.0 / heart_rate
        
        for i, time in enumerate(t):
            # 在每个心跳周期内生成脉搏波
            phase = (time % period) / period
            
            # 标准PPG波形：快速上升 + 缓慢下降 + 重搏波
            if phase < 0.15:  # 快速上升相 (收缩期)
                ppg[i] = np.sin(phase / 0.15 * np.pi / 2) ** 2
            elif phase < 0.35:  # 下降相
                ppg[i] = 1.0 - (phase - 0.15) / 0.2 * 0.7
            elif phase < 0.45:  # 重搏波 (舒张期)
                ppg[i] = 0.3 + 0.15 * np.sin((phase - 0.35) / 0.1 * np.pi)
            else:  # 回到基线
                ppg[i] = 0.3 * np.exp(-(phase - 0.45) / 0.3 * 5)
        
        return t, ppg
    
    @staticmethod
    def eeg_alpha_wave(duration=1.0, sample_rate=500, frequency=10):
        """
        生成标准EEG α波模板
        
        Args:
            duration: 持续时间
            sample_rate: 采样率
            frequency: α波频率 (8-13Hz)
            
        Returns:
            t, eeg: 时间轴和EEG波形
        """
        t = np.linspace(0, duration, int(duration * sample_rate))
        # α波：主频 + 少量谐波
        eeg = (np.sin(2 * np.pi * frequency * t) + 
               0.3 * np.sin(2 * np.pi * frequency * 2 * t) +
               0.1 * np.sin(2 * np.pi * frequency * 0.5 * t))
        return t, eeg
    
    @staticmethod
    def adaptive_template_fitting(raw_data, template, strength=0.7):
        """
        自适应模板约束拟合
        
        Args:
            raw_data: 原始数据
            template: 模板波形
            strength: 约束强度 (0-1)，越大越接近模板
            
        Returns:
            fitted_data: 拟合后的数据
        """
        if len(raw_data) != len(template):
            # 重采样模板以匹配数据长度
            from scipy import interpolate
            x_template = np.linspace(0, 1, len(template))
            x_data = np.linspace(0, 1, len(raw_data))
            f = interpolate.interp1d(x_template, template, kind='cubic')
            template = f(x_data)
        
        # 归一化
        raw_normalized = (raw_data - np.mean(raw_data)) / (np.std(raw_data) + 1e-6)
        template_normalized = (template - np.mean(template)) / (np.std(template) + 1e-6)
        
        # 加权融合：保留原始数据的幅度信息，采用模板的形态
        fitted = strength * template_normalized + (1 - strength) * raw_normalized
        
        # 恢复原始数据的幅度
        fitted = fitted * np.std(raw_data) + np.mean(raw_data)
        
        return fitted
    
    @staticmethod
    def detect_heart_rate(ppg_data, sample_rate=500):
        """
        从PPG数据中检测心率
        
        Args:
            ppg_data: PPG数据
            sample_rate: 采样率
            
        Returns:
            heart_rate: 心率(bpm)
        """
        if len(ppg_data) < sample_rate:
            return 70  # 默认心率
        
        # 使用FFT检测主频
        from scipy.fft import fft, fftfreq
        
        # 去趋势
        ppg_detrend = signal.detrend(ppg_data)
        
        # FFT
        n = len(ppg_detrend)
        yf = fft(ppg_detrend)
        xf = fftfreq(n, 1/sample_rate)
        
        # 只看0.5-3Hz范围 (30-180 bpm)
        valid_idx = (xf > 0.5) & (xf < 3.0)
        if not np.any(valid_idx):
            return 70
        
        # 找峰值频率
        power = np.abs(yf[valid_idx])
        peak_freq = xf[valid_idx][np.argmax(power)]
        
        heart_rate = peak_freq * 60
        
        # 限制在合理范围
        heart_rate = np.clip(heart_rate, 40, 180)
        
        return heart_rate
    
    @staticmethod
    def morphology_constrained_smooth(data, template, window=50):
        """
        形态约束的滑动窗口平滑
        
        在每个窗口内，使用模板约束数据形态
        """
        result = np.copy(data)
        half_window = window // 2
        
        for i in range(half_window, len(data) - half_window):
            # 提取窗口数据
            window_data = data[i - half_window:i + half_window]
            
            # 提取对应的模板片段
            template_segment = template[i - half_window:i + half_window]
            
            # 局部拟合
            fitted = PhysiologicalSignalModel.adaptive_template_fitting(
                window_data, template_segment, strength=0.5)
            
            # 只更新中心点
            result[i] = fitted[half_window]
        
        return result
