"""
数据解析器
根据通信协议解析接收到的数据帧
"""

import struct
from datetime import datetime


class DataParser:
    """数据解析类"""
    
    FRAME_HEADER = b'\xAB\xCD\x11\x26'
    FRAME_SIZE = 42
    
    def __init__(self):
        self.frame_count = 0
        self.error_count = 0
        
    def parse(self, frame_data):
        """
        解析数据帧
        
        Args:
            frame_data: 42字节的数据帧
            
        Returns:
            dict: 解析后的数据字典，失败返回None
        """
        if len(frame_data) != self.FRAME_SIZE:
            self.error_count += 1
            return None
            
        # 验证帧头
        if frame_data[0:4] != self.FRAME_HEADER:
            self.error_count += 1
            return None
            
        try:
            parsed_data = {
                'timestamp': datetime.now(),
                'frame_id': self.frame_count
            }
            
            # 解析ADS1118数据 (Bytes 4-5)
            parsed_data['ads1118'] = struct.unpack('>H', frame_data[4:6])[0]
            
            # 解析内部ADC通道0 (Bytes 6-7)
            parsed_data['adc_ch0'] = struct.unpack('>H', frame_data[6:8])[0]
            
            # 解析内部ADC通道1 (Bytes 10-11)
            parsed_data['adc_ch1'] = struct.unpack('>H', frame_data[10:12])[0]
            
            # 解析MAX30102血氧数据 (Bytes 20-25)
            parsed_data['red_led'] = (frame_data[20] << 16) | (frame_data[21] << 8) | frame_data[22]
            parsed_data['ir_led'] = (frame_data[23] << 16) | (frame_data[24] << 8) | frame_data[25]
            
            # 解析MPU6050四元数 (Bytes 26-41)
            quat = []
            for i in range(4):
                offset = 26 + i * 4
                quat_value = struct.unpack('>i', frame_data[offset:offset+4])[0]
                quat.append(quat_value)
            parsed_data['quat'] = quat
            
            self.frame_count += 1
            return parsed_data
            
        except Exception as e:
            self.error_count += 1
            print(f"解析错误: {e}")
            return None
            
    def get_statistics(self):
        """获取统计信息"""
        total = self.frame_count + self.error_count
        success_rate = (self.frame_count / total * 100) if total > 0 else 0
        
        return {
            'total_frames': self.frame_count,
            'error_frames': self.error_count,
            'success_rate': success_rate
        }
        
    def reset_statistics(self):
        """重置统计信息"""
        self.frame_count = 0
        self.error_count = 0


class DataConverter:
    """数据转换工具类"""
    
    @staticmethod
    def ads1118_to_voltage(value, vref=3.3, gain=1):
        """
        将ADS1118 ADC值转换为电压
        
        Args:
            value: ADC值 (0-65535)
            vref: 参考电压
            gain: 增益
            
        Returns:
            float: 电压值
        """
        # ADS1118是16位有符号数
        if value > 32767:
            value = value - 65536
        voltage = (value / 32768.0) * (vref / gain)
        return voltage
        
    @staticmethod
    def stm32_adc_to_voltage(value, vref=3.3):
        """
        将STM32内部ADC值转换为电压
        
        Args:
            value: ADC值 (0-4095)
            vref: 参考电压
            
        Returns:
            float: 电压值
        """
        return (value / 4095.0) * vref
        
    @staticmethod
    def quaternion_to_euler(q0, q1, q2, q3):
        """
        将四元数转换为欧拉角
        
        Args:
            q0, q1, q2, q3: 四元数分量
            
        Returns:
            tuple: (roll, pitch, yaw) 弧度制
        """
        import math
        
        # 归一化四元数
        norm = math.sqrt(q0*q0 + q1*q1 + q2*q2 + q3*q3)
        if norm == 0:
            return (0, 0, 0)
            
        q0 /= norm
        q1 /= norm
        q2 /= norm
        q3 /= norm
        
        # 转换为欧拉角
        roll = math.atan2(2*(q0*q1 + q2*q3), 1 - 2*(q1*q1 + q2*q2))
        pitch = math.asin(2*(q0*q2 - q3*q1))
        yaw = math.atan2(2*(q0*q3 + q1*q2), 1 - 2*(q2*q2 + q3*q3))
        
        return (roll, pitch, yaw)
