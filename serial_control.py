# -*- coding:utf-8 -*-
# 鼠标串口控制模块
# 负责串口连接、断开、状态查询、线程安全发送
import serial
import serial.tools.list_ports
import threading
from typing import Optional, List, Tuple


class SerialControl:
    """串口控制类，提供线程安全的串口操作"""

    BAUD = 9600
    TIMEOUT = 0.2

    def __init__(self):
        self._ser: Optional[serial.Serial] = None
        self._lock = threading.Lock()
        self._connected_port: str = ""

    @property
    def is_connected(self) -> bool:
        """检查串口是否已连接"""
        with self._lock:
            return self._ser is not None and self._ser.is_open

    @property
    def connected_port(self) -> str:
        """获取当前连接的端口名"""
        with self._lock:
            return self._connected_port

    def scan_ports(self) -> Tuple[List[Tuple[str, str]], Optional[str]]:
        """
        扫描所有可用串口
        Returns: (端口信息列表, 首选CH340端口)
        端口信息: (设备名, 显示名)
        """
        try:
            port_infos = []
            ch340_port = None
            
            for p in serial.tools.list_ports.comports():
                # 构建显示名
                desc = p.description if p.description else "未知设备"
                display_name = f"{p.device} ({desc})"
                
                port_infos.append((p.device, display_name))
                
                # 检查是否是CH340
                if "CH340" in desc.upper():
                    ch340_port = p.device
            
            return port_infos, ch340_port
        except Exception:
            return [], None

    def connect(self, port: str) -> Tuple[bool, str]:
        """
        连接指定串口
        Returns: (成功标志, 消息)
        """
        with self._lock:
            try:
                # 关闭现有连接
                if self._ser:
                    try:
                        self._ser.close()
                    except Exception:
                        pass
                    self._ser = None

                if not port:
                    return False, "请选择有效的串口"

                self._ser = serial.Serial(port, self.BAUD, timeout=self.TIMEOUT)
                self._connected_port = port
                return True, f"已成功连接到 {port}"

            except serial.SerialException as e:
                self._ser = None
                return False, f"连接失败：{str(e)}"
            except Exception as e:
                self._ser = None
                return False, f"连接异常：{str(e)}"

    def disconnect(self) -> Tuple[bool, str]:
        """
        断开当前串口连接
        Returns: (成功标志, 消息)
        """
        with self._lock:
            try:
                if self._ser:
                    self._ser.close()
                    self._ser = None
                    self._connected_port = ""
                    return True, "已断开串口连接"
                return False, "串口未连接"
            except Exception as e:
                return False, f"断开连接失败：{str(e)}"

    def write(self, data: bytes) -> bool:
        """
        线程安全地发送数据
        Returns: 发送是否成功
        """
        with self._lock:
            if not (self._ser and self._ser.is_open):
                return False
            try:
                self._ser.write(data)
                return True
            except Exception:
                return False

    def read(self, size: int = 1) -> Optional[bytes]:
        """读取串口数据"""
        with self._lock:
            if not (self._ser and self._ser.is_open):
                return None
            try:
                return self._ser.read(size)
            except Exception:
                return None

    def flush(self) -> bool:
        """刷新串口缓冲区"""
        with self._lock:
            if not (self._ser and self._ser.is_open):
                return False
            try:
                self._ser.flush()
                return True
            except Exception:
                return False


# 单例模式全局实例
_serial_instance: Optional[SerialControl] = None
_instance_lock = threading.Lock()


def get_serial_control() -> SerialControl:
    """获取串口控制单例"""
    global _serial_instance
    with _instance_lock:
        if _serial_instance is None:
            _serial_instance = SerialControl()
        return _serial_instance
