"""
串口通信处理类
负责串口的打开、关闭、数据接收等操作
"""

from PyQt5.QtCore import QObject, QThread, pyqtSignal
import serial
import serial.tools.list_ports
import time


class SerialReader(QThread):
    """串口读取线程"""
    data_received = pyqtSignal(bytes)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, serial_port):
        super().__init__()
        self.serial_port = serial_port
        self.running = False
        
    def run(self):
        """线程运行函数"""
        self.running = True
        buffer = bytearray()
        
        while self.running:
            try:
                if self.serial_port and self.serial_port.is_open:
                    # 读取可用数据
                    if self.serial_port.in_waiting:
                        data = self.serial_port.read(self.serial_port.in_waiting)
                        buffer.extend(data)
                        
                        # 查找完整的数据帧
                        while len(buffer) >= 42:
                            # 查找帧头
                            frame_start = -1
                            for i in range(len(buffer) - 3):
                                if (buffer[i] == 0xAB and buffer[i+1] == 0xCD and 
                                    buffer[i+2] == 0x11 and buffer[i+3] == 0x26):
                                    frame_start = i
                                    break
                            
                            if frame_start == -1:
                                # 没找到帧头，保留最后3个字节
                                buffer = buffer[-3:]
                                break
                            
                            # 丢弃帧头前的数据
                            if frame_start > 0:
                                buffer = buffer[frame_start:]
                            
                            # 检查是否有完整帧
                            if len(buffer) >= 42:
                                frame = bytes(buffer[:42])
                                buffer = buffer[42:]
                                self.data_received.emit(frame)
                            else:
                                break
                    else:
                        time.sleep(0.001)  # 避免CPU占用过高
                else:
                    break
                    
            except serial.SerialException as e:
                self.error_occurred.emit(f"串口读取错误: {str(e)}")
                break
            except Exception as e:
                self.error_occurred.emit(f"未知错误: {str(e)}")
                break
                
    def stop(self):
        """停止线程"""
        self.running = False
        self.wait()


class SerialHandler(QObject):
    """串口处理类"""
    data_received = pyqtSignal(bytes)
    connection_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.serial_port = None
        self.reader_thread = None
        
    def get_available_ports(self):
        """获取可用串口列表"""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
        
    def connect(self, port, baudrate=3000000, timeout=1):
        """连接串口"""
        try:
            self.serial_port = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=timeout
            )
            
            # 清空缓冲区
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()
            
            # 启动读取线程
            self.reader_thread = SerialReader(self.serial_port)
            self.reader_thread.data_received.connect(self.data_received)
            self.reader_thread.error_occurred.connect(self._on_reader_error)
            self.reader_thread.start()
            
            self.connection_changed.emit(True)
            return True
            
        except serial.SerialException as e:
            self.error_occurred.emit(f"无法打开串口: {str(e)}")
            return False
        except Exception as e:
            self.error_occurred.emit(f"连接错误: {str(e)}")
            return False
            
    def disconnect(self):
        """断开串口"""
        if self.reader_thread:
            self.reader_thread.stop()
            self.reader_thread = None
            
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            
        self.serial_port = None
        self.connection_changed.emit(False)
        
    def is_connected(self):
        """检查是否已连接"""
        return self.serial_port is not None and self.serial_port.is_open
        
    def write(self, data):
        """发送数据"""
        if self.is_connected():
            try:
                self.serial_port.write(data)
                return True
            except Exception as e:
                self.error_occurred.emit(f"发送数据失败: {str(e)}")
                return False
        return False
        
    def _on_reader_error(self, error_msg):
        """读取线程错误处理"""
        self.error_occurred.emit(error_msg)
        self.disconnect()
