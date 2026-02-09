"""
文件操作工具
提供数据保存、导出等功能
"""

import csv
import json
from datetime import datetime
import os


class DataRecorder:
    """数据录制类"""
    
    def __init__(self):
        self.is_recording = False
        self.filename = None
        self.file_handle = None
        self.csv_writer = None
        self.data_count = 0
        self.start_time = None
        
    def start_recording(self, filename=None):
        """
        开始录制
        
        Args:
            filename: 文件名，如果为None则自动生成
        """
        if self.is_recording:
            return False
            
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'data_record_{timestamp}.csv'
            
        try:
            self.filename = filename
            self.file_handle = open(filename, 'w', newline='', encoding='utf-8')
            self.csv_writer = csv.writer(self.file_handle)
            
            # 写入表头
            header = [
                'timestamp', 'ads1118',
                'red_led', 'ir_led', 'quat_0', 'quat_1', 'quat_2', 'quat_3'
            ]
            self.csv_writer.writerow(header)
            
            self.is_recording = True
            self.data_count = 0
            self.start_time = None
            return True
            
        except Exception as e:
            print(f"开始录制失败: {e}")
            return False
            
    def add_data(self, parsed_data):
        """
        添加数据
        
        Args:
            parsed_data: 解析后的数据字典
        """
        if not self.is_recording or self.csv_writer is None:
            return False
            
        try:
            # 记录开始时间
            if self.start_time is None:
                self.start_time = parsed_data['timestamp']
            
            # 计算相对时间戳（秒）
            relative_time = (parsed_data['timestamp'] - self.start_time).total_seconds()
            
            row = [
                f'{relative_time:.6f}',
                parsed_data.get('ads1118', ''),
                parsed_data.get('red_led', ''),
                parsed_data.get('ir_led', ''),
                parsed_data['quat'][0] if 'quat' in parsed_data else '',
                parsed_data['quat'][1] if 'quat' in parsed_data else '',
                parsed_data['quat'][2] if 'quat' in parsed_data else '',
                parsed_data['quat'][3] if 'quat' in parsed_data else '',
            ]
            self.csv_writer.writerow(row)
            self.data_count += 1
            return True
            
        except Exception as e:
            print(f"添加数据失败: {e}")
            return False
            
    def stop_recording(self):
        """
        停止录制
        
        Returns:
            str: 保存的文件名
        """
        if not self.is_recording:
            return None
            
        if self.file_handle:
            self.file_handle.close()
            
        self.is_recording = False
        filename = self.filename
        self.filename = None
        self.file_handle = None
        self.csv_writer = None
        
        return filename


def export_to_csv(data_list, filename):
    """
    导出数据到CSV文件
    
    Args:
        data_list: 数据列表
        filename: 文件名
        
    Returns:
        bool: 是否成功
    """
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 写入表头
            header = [
                'timestamp', 'ads1118',
                'red_led', 'ir_led', 'quat_0', 'quat_1', 'quat_2', 'quat_3'
            ]
            writer.writerow(header)
            
            # 写入数据
            start_time = data_list[0]['timestamp'] if data_list else None
            for data in data_list:
                # 计算相对时间戳（秒）
                relative_time = (data['timestamp'] - start_time).total_seconds() if start_time else 0
                
                row = [
                    f'{relative_time:.6f}',
                    data.get('ads1118', ''),
                    data.get('red_led', ''),
                    data.get('ir_led', ''),
                    data['quat'][0] if 'quat' in data else '',
                    data['quat'][1] if 'quat' in data else '',
                    data['quat'][2] if 'quat' in data else '',
                    data['quat'][3] if 'quat' in data else '',
                ]
                writer.writerow(row)
                
        return True
        
    except Exception as e:
        print(f"导出CSV失败: {e}")
        return False


def export_to_json(data_list, filename):
    """
    导出数据到JSON文件
    
    Args:
        data_list: 数据列表
        filename: 文件名
        
    Returns:
        bool: 是否成功
    """
    try:
        # 转换datetime对象为字符串
        export_data = []
        for data in data_list:
            data_copy = data.copy()
            data_copy['timestamp'] = data['timestamp'].strftime('%Y-%m-%d %H:%M:%S.%f')
            export_data.append(data_copy)
            
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
            
        return True
        
    except Exception as e:
        print(f"导出JSON失败: {e}")
        return False


def load_from_csv(filename):
    """
    从CSV文件加载数据
    
    Args:
        filename: 文件名
        
    Returns:
        list: 数据列表
    """
    try:
        data_list = []
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data = {
                    'timestamp': datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S.%f'),
                    'frame_id': int(row['frame_id']) if row['frame_id'] else 0,
                    'ads1118': int(row['ads1118']) if row['ads1118'] else 0,
                    'adc_ch0': int(row['adc_ch0']) if row['adc_ch0'] else 0,
                    'adc_ch1': int(row['adc_ch1']) if row['adc_ch1'] else 0,
                    'red_led': int(row['red_led']) if row['red_led'] else 0,
                    'ir_led': int(row['ir_led']) if row['ir_led'] else 0,
                    'quat': [
                        int(row['quat_0']) if row['quat_0'] else 0,
                        int(row['quat_1']) if row['quat_1'] else 0,
                        int(row['quat_2']) if row['quat_2'] else 0,
                        int(row['quat_3']) if row['quat_3'] else 0,
                    ]
                }
                data_list.append(data)
                
        return data_list
        
    except Exception as e:
        print(f"加载CSV失败: {e}")
        return []
