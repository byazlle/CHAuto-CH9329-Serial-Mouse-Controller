# -*- coding:utf-8 -*-
# 鼠标串口指令转换发送模块
# 将鼠标指令转换为CH9329协议数据并发送
import time
import threading
from typing import List, Tuple, Optional, Callable

from serial_control import get_serial_control


class MouseCommand:
    """鼠标指令转换与发送类"""

    # CH9329 协议配置
    HEAD = [0x57, 0xAB]
    ADDR = 0x00
    CMD_MOUSE = 0x05
    DATA_LEN = 0x05

    # 按键定义
    KEY_NONE = 0x00
    KEY_LEFT = 0x01
    KEY_RIGHT = 0x02
    KEY_BOTH = 0x03

    def __init__(self):
        self._serial = get_serial_control()
        self._stop_flag = False
        self._lock = threading.Lock()

    def _compute_checksum(self, data: List[int]) -> int:
        """
        计算校验和 - 使用改进的CRC算法
        基于前n-1字节计算校验字节
        """
        checksum = 0
        for byte in data:
            checksum = (checksum + byte) & 0xFF
        return checksum

    def send_mouse(
        self, x_rel: int, y_rel: int, key: int = 0, wait_ms: int = 1
    ) -> bool:
        """
        发送相对鼠标移动指令

        Args:
            x_rel: X轴相对移动 (-127 ~ 127)
            y_rel: Y轴相对移动 (-127 ~ 127)
            key: 按键类型 (0=无, 1=左键, 2=右键, 3=双键)
            wait_ms: 等待时间(毫秒)

        Returns:
            发送是否成功
        """
        with self._lock:
            if not self._serial.is_connected:
                return False

            # 限制移动范围
            x = max(-127, min(127, x_rel)) & 0xFF
            y = max(-127, min(127, y_rel)) & 0xFF
            key = max(0, min(3, key)) & 0xFF

            # 构建数据包
            pkg = [
                *self.HEAD,
                self.ADDR,
                self.CMD_MOUSE,
                self.DATA_LEN,
                0x01,  # 报告ID
                key,
                x,
                y,
                0x00,  # 滚轮
            ]
            pkg.append(self._compute_checksum(pkg))

            # 发送数据
            success = self._serial.write(bytes(pkg))
            if success:
                time.sleep(wait_ms / 1000)
            return success

    def move_to(
        self, x: int, y: int, key: int = 0, delay_ms: int = 500
    ) -> bool:
        """
        移动到绝对坐标位置

        Args:
            x: 目标X坐标
            y: 目标Y坐标
            key: 按键类型
            delay_ms: 到达后延迟时间

        Returns:
            是否成功执行
        """
        self._stop_flag = False

        with self._lock:
            # 首先将鼠标移动到原点附近进行归位
            for _ in range(60):
                if self._stop_flag:
                    return False
                self._send_mouse_internal(-50, -50, 0, 1)

        # X轴移动
        remaining_x = x
        while remaining_x > 0 and not self._stop_flag:
            step = min(30, remaining_x)
            if not self._send_mouse_internal(step, 0, 0, 2):
                return False
            remaining_x -= step

        # Y轴移动
        remaining_y = y
        while remaining_y > 0 and not self._stop_flag:
            step = min(30, remaining_y)
            if not self._send_mouse_internal(0, step, 0, 2):
                return False
            remaining_y -= step

        if self._stop_flag:
            return False

        # 固定等待500ms（移动后点击前）
        if key != self.KEY_NONE:
            time.sleep(0.5)

        # 执行点击
        if key == self.KEY_LEFT:
            self._send_mouse_internal(0, 0, self.KEY_LEFT, 20)
            self._send_mouse_internal(0, 0, self.KEY_NONE, 20)
        elif key == self.KEY_RIGHT:
            self._send_mouse_internal(0, 0, self.KEY_RIGHT, 20)
            self._send_mouse_internal(0, 0, self.KEY_NONE, 20)

        # 延迟等待
        start_time = time.time()
        while (time.time() - start_time) < delay_ms / 1000 and not self._stop_flag:
            time.sleep(0.01)

        return True

    def _send_mouse_internal(
        self, x_rel: int, y_rel: int, key: int, wait_ms: int
    ) -> bool:
        """内部发送方法（无锁版本）"""
        if not self._serial.is_connected:
            return False

        x = max(-127, min(127, x_rel)) & 0xFF
        y = max(-127, min(127, y_rel)) & 0xFF

        pkg = [
            *self.HEAD,
            self.ADDR,
            self.CMD_MOUSE,
            self.DATA_LEN,
            0x01,
            key,
            x,
            y,
            0x00,
        ]
        pkg.append(self._compute_checksum(pkg))

        success = self._serial.write(bytes(pkg))
        if success:
            time.sleep(wait_ms / 1000)
        return success

    def stop(self):
        """停止当前操作"""
        self._stop_flag = True

    def reset_stop(self):
        """重置停止标志"""
        self._stop_flag = False

    def run_script(
        self,
        script: List[Tuple[int, int, int, int]],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bool:
        """
        执行脚本序列

        Args:
            script: 脚本列表 [(x, y, key, delay_ms), ...]
            progress_callback: 进度回调函数 (current, total)

        Returns:
            是否全部执行完成
        """
        self.reset_stop()
        total = len(script)

        for index, (x, y, k, d) in enumerate(script):
            if self._stop_flag:
                return False

            self.move_to(x, y, k, d)

            if progress_callback:
                progress_callback(index + 1, total)

        return True


# 单例模式
_mouse_command_instance: Optional[MouseCommand] = None
_instance_lock = threading.Lock()


def get_mouse_command() -> MouseCommand:
    """获取鼠标指令单例"""
    global _mouse_command_instance
    with _instance_lock:
        if _mouse_command_instance is None:
            _mouse_command_instance = MouseCommand()
        return _mouse_command_instance
