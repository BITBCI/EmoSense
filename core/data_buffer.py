"""
数据缓冲管理
管理接收到的数据，提供数据访问接口
"""

from collections import deque
from datetime import datetime
import time


class DataBuffer:
    """数据缓冲类"""
    
    def __init__(self, max_points=2000):
        """
        初始化数据缓冲
        
        Args:
            max_points: 最大缓存数据点数
        """
        self.max_points = max_points
        self.data = deque(maxlen=max_points)
        self.start_time = None
        self.last_update_time = None
        self.frame_count = 0
        self.sample_rate = 500  # 假设采样率为500Hz
        self.time_interval = 1.0 / self.sample_rate  # 采样间隔（秒）
        
    def add_data(self, parsed_data):
        """
        添加数据（使用均匀时间戳）
        
        Args:
            parsed_data: 解析后的数据字典
        """
        if self.start_time is None:
            self.start_time = time.time()
            # 使用解析数据中的时间戳作为参考（如果是虚拟数据）
            if 'timestamp' in parsed_data:
                # 保留原有时间戳（虚拟数据已经设置了均匀时间戳）
                pass
            else:
                # 为真实数据生成均匀时间戳
                from datetime import datetime, timedelta
                parsed_data['timestamp'] = datetime.now()
        else:
            # 如果数据中没有时间戳，生成均匀时间戳
            if 'timestamp' not in parsed_data or parsed_data.get('_use_uniform_timestamp', True):
                from datetime import datetime, timedelta
                # 基于第一个数据点生成均匀时间戳
                if len(self.data) > 0:
                    last_timestamp = list(self.data)[-1]['timestamp']
                    parsed_data['timestamp'] = last_timestamp + timedelta(seconds=self.time_interval)
                else:
                    parsed_data['timestamp'] = datetime.now()
            
        self.data.append(parsed_data)
        self.last_update_time = time.time()
        self.frame_count += 1
        
    def get_all_data(self):
        """获取所有数据"""
        return list(self.data)
        
    def get_latest_data(self, n=1):
        """
        获取最新的n条数据
        
        Args:
            n: 数据条数
            
        Returns:
            list: 最新的n条数据
        """
        if n >= len(self.data):
            return list(self.data)
        return list(self.data)[-n:]
        
    def get_data_by_time_range(self, start_time, end_time):
        """
        获取指定时间范围内的数据
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            list: 时间范围内的数据
        """
        return [d for d in self.data 
                if start_time <= d['timestamp'] <= end_time]
                
    def get_timestamps(self):
        """
        获取相对时间戳数组（秒）
        
        Returns:
            list: 时间戳列表
        """
        if not self.data or self.start_time is None:
            return []
            
        timestamps = []
        for d in self.data:
            # 计算相对于开始时间的偏移
            dt = (d['timestamp'] - list(self.data)[0]['timestamp']).total_seconds()
            timestamps.append(dt)
            
        return timestamps
        
    def get_sample_rate(self):
        """
        计算当前采样率
        
        Returns:
            float: 采样率 (Hz)
        """
        if len(self.data) < 2:
            return 0.0
            
        # 计算最近1秒内的采样率
        now = datetime.now()
        recent_data = [d for d in self.data 
                      if (now - d['timestamp']).total_seconds() <= 1.0]
                      
        return len(recent_data)
        
    def clear(self):
        """清空缓冲区"""
        self.data.clear()
        self.start_time = None
        self.last_update_time = None
        self.frame_count = 0
        
    def get_statistics(self):
        """
        获取统计信息
        
        Returns:
            dict: 统计信息
        """
        if not self.data:
            return {
                'count': 0,
                'duration': 0,
                'sample_rate': 0
            }
            
        duration = 0
        if self.start_time and self.last_update_time:
            duration = self.last_update_time - self.start_time
            
        return {
            'count': len(self.data),
            'total_frames': self.frame_count,
            'duration': duration,
            'sample_rate': self.get_sample_rate()
        }
        
    def get_field_data(self, field_name):
        """
        获取指定字段的所有数据
        
        Args:
            field_name: 字段名称
            
        Returns:
            list: 字段数据列表
        """
        return [d[field_name] for d in self.data if field_name in d]
