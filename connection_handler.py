# -*- coding:utf-8 -*-
# 连接模块
# 处理主界面按钮的功能调用，接收相关内容并调用其他模块展示，同时回传任务结果
import threading
import datetime
from typing import List, Tuple, Optional, Callable, Dict, Any

from serial_control import get_serial_control
from mouse_command import get_mouse_command
from image_manager import get_image_manager
from automation import get_automation_engine
from script_manager import get_script_manager
from config_manager import get_config_manager


class ConnectionHandler:
    """连接处理器 - 协调各模块工作"""

    def __init__(self):
        self._serial = get_serial_control()
        self._mouse = get_mouse_command()
        self._image_mgr = get_image_manager()
        self._automation = get_automation_engine()
        self._script_mgr = get_script_manager()
        self._config_mgr = get_config_manager()

        self._on_status_update: Optional[Callable[[str], None]] = None
        self._on_com_update: Optional[Callable[[str], None]] = None
        self._on_log_message: Optional[Callable[[str], None]] = None
        self._on_error: Optional[Callable[[str, str], None]] = None

    def set_callbacks(
        self,
        on_status_update: Optional[Callable[[str], None]] = None,
        on_com_update: Optional[Callable[[str], None]] = None,
        on_log_message: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str, str], None]] = None,
    ):
        self._on_status_update = on_status_update
        self._on_com_update = on_com_update
        self._on_log_message = on_log_message
        self._on_error = on_error

    def _notify_status(self, status: str):
        if self._on_status_update:
            self._on_status_update(status)

    def _notify_com(self, status: str):
        if self._on_com_update:
            self._on_com_update(status)

    def _notify_log(self, message: str):
        if self._on_log_message:
            self._on_log_message(message)

    def _notify_error(self, title: str, message: str):
        if self._on_error:
            self._on_error(title, message)

    def scan_serial_ports(self) -> Tuple[bool, str, List[Tuple[str, str]], Optional[str]]:
        port_infos = []
        ch340_port = None
        try:
            from serial.tools import list_ports
            ports = list_ports.comports()
            for p in ports:
                desc = p.description if p.description else "未知设备"
                display = f"{p.device} ({desc})"
                port_infos.append((p.device, display))
                if "CH340" in desc.upper():
                    ch340_port = p.device
        except:
            pass

        count = len(port_infos)
        if count > 0:
            if ch340_port:
                return True, f"已为您自动选择可能的相关端口（共 {count} 个）", port_infos, ch340_port
            else:
                return True, f"未找到可能的相关端口，共 {count} 个", port_infos, None
        else:
            return False, "未扫描到任何串口", [], None

    def connect_serial(self, port: str) -> Tuple[bool, str]:
        if not port:
            return False, "请先选择串口"
        success, message = self._serial.connect(port)
        if success:
            self._notify_com(f"串口: 已连接 {port}")
            self._notify_status("空闲")
            self._notify_log(f"已连接到 {port}")
        else:
            self._notify_com("串口: 未连接")
        return success, message

    def disconnect_serial(self) -> Tuple[bool, str]:
        success, message = self._serial.disconnect()
        if success:
            self._notify_com("串口: 未连接")
            self._notify_log("已断开串口连接")
        return success, message

    def is_serial_connected(self) -> bool:
        return self._serial.is_connected

    def get_serial_status(self) -> str:
        if self._serial.is_connected:
            return f"串口: 已连接 {self._serial.connected_port}"
        return "串口: 未连接"

    def run_single_script(self, filename: str) -> Tuple[bool, str]:
        if not self._serial.is_connected:
            return False, "请先连接串口"

        self._notify_status("执行中")
        self._notify_log(f"开始执行脚本: {filename}")

        try:
            success, msg, commands = self._script_mgr.load_script(filename)
            if not success:
                return False, msg

            self._notify_log(msg)
            success = self._mouse.run_script(commands)

            if success:
                self._notify_status("空闲")
                self._notify_log("脚本执行完成")
                return True, "脚本执行完成"
            else:
                self._notify_status("空闲")
                self._notify_log("脚本执行被中断")
                return False, "脚本执行被中断"

        except Exception as e:
            self._notify_status("空闲")
            self._notify_log(f"脚本执行异常: {str(e)}")
            return False, f"执行异常: {str(e)}"

    def run_script_from_content(self, content: str) -> Tuple[bool, str]:
        if not self._serial.is_connected:
            return False, "请先连接串口"

        self._notify_status("执行中")
        self._notify_log("开始执行脚本...")

        try:
            success, msg, commands = self._script_mgr._parse_script(content)
            if not success:
                return False, msg

            success = self._mouse.run_script(commands)

            if success:
                self._notify_status("空闲")
                self._notify_log("脚本执行完成")
                return True, "脚本执行完成"
            else:
                self._notify_status("空闲")
                self._notify_log("脚本执行被中断")
                return False, "脚本执行被中断"

        except Exception as e:
            self._notify_status("空闲")
            self._notify_log(f"脚本执行异常: {str(e)}")
            return False, f"执行异常: {str(e)}"

    def start_automation(self, config_data: Dict[str, Any]) -> Tuple[bool, str]:
        if not self._serial.is_connected:
            return False, "请先连接串口"

        if self._automation.is_running:
            return False, "自动化已在运行中"

        self._automation.set_callbacks(
            on_progress=self._on_automation_progress,
            on_status_change=self._on_automation_status,
            on_log=self._on_automation_log,
        )

        self._notify_status("运行中")
        self._notify_log("启动自动化...")

        self._automation.run(config_data)
        return True, "自动化已启动"

    def stop_automation(self) -> Tuple[bool, str]:
        if not self._automation.is_running:
            return False, "自动化未在运行"

        self._automation.stop()
        self._notify_status("空闲")
        self._notify_log("已停止自动化")
        return True, "已停止自动化"

    def is_automation_running(self) -> bool:
        return self._automation.is_running

    def get_automation_status(self) -> str:
        if self._automation.is_running:
            return "状态: 运行中"
        return "状态: 空闲"

    def _on_automation_progress(self, current: int, total: int, node: str):
        self._notify_log(f"进度: {current}/{total} - {node}")

    def _on_automation_status(self, running: bool):
        self._notify_status("运行中" if running else "空闲")

    def _on_automation_log(self, message: str):
        self._notify_log(message)


# 单例模式
_handler_instance: Optional[ConnectionHandler] = None
_handler_lock = threading.Lock()


def get_connection_handler() -> ConnectionHandler:
    """获取连接处理器单例"""
    global _handler_instance
    with _handler_lock:
        if _handler_instance is None:
            _handler_instance = ConnectionHandler()
        return _handler_instance