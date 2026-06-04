# -*- coding:utf-8 -*-
# 自动化流程模块
# 支持预设多个节点，执行串口发送、鼠标自动化、延迟、切换图片等操作
import threading
import time
import re
from typing import List, Optional, Callable, Dict, Any

from mouse_command import get_mouse_command
from image_manager import get_image_manager


class AutomationEngine:
    """自动化引擎"""

    def __init__(self):
        self._nodes: List[Dict[str, Any]] = []
        self._is_running = False
        self._stop_flag = False
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None

        self._on_progress: Optional[Callable[[int, int, str], None]] = None
        self._on_status_change: Optional[Callable[[bool], None]] = None
        self._on_log: Optional[Callable[[str], None]] = None

        self._mouse = get_mouse_command()
        self._image_mgr = get_image_manager()

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._is_running

    @property
    def nodes(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._nodes)

    def set_callbacks(
        self,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        on_status_change: Optional[Callable[[bool], None]] = None,
        on_log: Optional[Callable[[str], None]] = None,
    ):
        self._on_progress = on_progress
        self._on_status_change = on_status_change
        self._on_log = on_log

    def _log(self, message: str):
        if self._on_log:
            self._on_log(message)

    def load_config(self, config_data: Dict[str, Any]) -> bool:
        """从配置数据加载"""
        with self._lock:
            if "nodes" not in config_data:
                return False

            self._nodes = list(config_data["nodes"])

            # 应用显示配置
            if "image_display" in config_data:
                display = config_data["image_display"]
                self._image_mgr.SHAKE_AMPLITUDE = display.get("shake_amplitude", 10)
                self._image_mgr.FLOAT_SPEED = display.get("shake_speed", 0.2)

            return True

    def set_nodes(self, nodes: List[Dict[str, Any]]):
        """设置节点列表"""
        with self._lock:
            self._nodes = list(nodes)

    def add_node(self, node: Dict[str, Any]):
        """添加节点"""
        with self._lock:
            self._nodes.append(node)

    def clear_nodes(self):
        """清空所有节点"""
        with self._lock:
            self._nodes.clear()

    def stop(self):
        """停止自动化"""
        with self._lock:
            self._stop_flag = True
        self._mouse.stop()

    def run(self, config_data: Optional[Dict[str, Any]] = None):
        """运行自动化流程"""
        if self.is_running:
            self._log("自动化正在运行中，请先停止")
            return

        if config_data:
            self.load_config(config_data)

        self._stop_flag = False

        with self._lock:
            self._is_running = True

        self._notify_status(True)
        self._log("自动化流程已启动")

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _notify_status(self, running: bool):
        if self._on_status_change:
            self._on_status_change(running)

    def _run_loop(self):
        try:
            # 获取循环配置
            loop_enabled = True
            loop_count = 0  # 0表示无限循环

            # 从配置中获取循环设置（如果有）
            with self._lock:
                total_nodes = len(self._nodes)

            current_loop = 0

            while not self._stop_flag:
                current_loop += 1

                for node_index, node in enumerate(self._nodes):
                    if self._stop_flag:
                        break

                    node_type = node.get("type")
                    node_name = self._get_node_name(node_type, node)

                    loop_info = f"[循环 {current_loop}]" if loop_enabled else ""
                    self._log(f"{loop_info} 执行节点 {node_index+1}/{total_nodes}: {node_name}")

                    if node_type == "script":
                        self._execute_script_node(node)
                    elif node_type == "delay":
                        self._execute_delay_node(node)
                    elif node_type == "image_switch":
                        self._execute_image_switch(node)
                    elif node_type == "image_goto":
                        self._execute_image_goto(node)
                    elif node_type == "mouse_move":
                        self._execute_mouse_move(node)

                    if self._on_progress:
                        self._on_progress(node_index + 1, total_nodes, node_name)

                # 检查是否需要继续循环
                if self._stop_flag:
                    break

                if loop_count > 0 and current_loop >= loop_count:
                    self._log(f"已达到循环次数 {loop_count}，停止自动化")
                    break

                # 无限循环或未达到次数，短暂等待后继续
                if not self._stop_flag:
                    time.sleep(0.1)

        except Exception as e:
            self._log(f"自动化执行异常: {str(e)}")
        finally:
            with self._lock:
                self._is_running = False
                self._stop_flag = False
            self._notify_status(False)
            self._log("自动化流程已停止")

    def _execute_script_node(self, node: Dict[str, Any]):
        """执行脚本节点"""
        script_content = node.get("content", "")
        delay_after = node.get("delay_after_ms", 500)

        if not script_content:
            self._log("脚本内容为空")
            return

        commands = self._parse_script_content(script_content)
        if not commands:
            self._log("无法解析脚本内容")
            return

        self._log(f"执行 {len(commands)} 条脚本指令")
        self._mouse.run_script(commands)

        if delay_after > 0:
            self._wait_for(delay_after)

    def _execute_delay_node(self, node: Dict[str, Any]):
        """执行延时节点"""
        duration = node.get("duration_ms", 1000)
        self._log(f"延时 {duration}ms")
        self._wait_for(duration)

    def _execute_image_switch(self, node: Dict[str, Any]):
        """执行图片切换"""
        direction = node.get("direction", "next")
        if direction == "next":
            self._image_mgr.next()
        elif direction == "prev":
            self._image_mgr.prev()

        info = self._image_mgr.get_current_image_info()
        if info:
            self._log(f"已切换到: {info['filename']}")

    def _execute_image_goto(self, node: Dict[str, Any]):
        """执行图片跳转"""
        index = node.get("index", 0)
        self._image_mgr.go_to(index)

        info = self._image_mgr.get_current_image_info()
        if info:
            self._log(f"已跳转到: {info['filename']}")

    def _execute_mouse_move(self, node: Dict[str, Any]):
        """执行单次鼠标移动"""
        x = node.get("x", 0)
        y = node.get("y", 0)
        key = node.get("key", 0)
        delay = node.get("delay_ms", 500)

        self._mouse.move_to(x, y, key, delay)

    def _wait_for(self, ms: int):
        """等待指定毫秒数"""
        start = time.time()
        while (time.time() - start) < ms / 1000 and not self._stop_flag:
            time.sleep(0.01)

    def _parse_script_content(self, content: str) -> List:
        """解析脚本内容为指令列表"""
        commands = []
        lines = content.splitlines()

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            match = re.match(r'\((\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)', line)
            if match:
                try:
                    x = int(match.group(1))
                    y = int(match.group(2))
                    key = int(match.group(3))
                    delay = int(match.group(4))
                    commands.append((x, y, key, delay))
                except:
                    pass

        return commands

    def _get_node_name(self, node_type: str, node: Dict[str, Any]) -> str:
        """获取节点类型名称"""
        if node_type == "script":
            return f"执行脚本: {node.get('name', '未命名')}"
        elif node_type == "delay":
            return f"延时: {node.get('duration_ms', 0)}ms"
        elif node_type == "image_switch":
            direction = "下一张" if node.get("direction") == "next" else "上一张"
            return f"切换图片: {direction}"
        elif node_type == "image_goto":
            return f"跳转图片: 第{node.get('index', 0)}张"
        elif node_type == "mouse_move":
            return "单次鼠标操作"
        else:
            return "未知节点"


# 单例模式
_automation_instance: Optional[AutomationEngine] = None
_instance_lock = threading.Lock()


def get_automation_engine() -> AutomationEngine:
    """获取自动化引擎单例"""
    global _automation_instance
    with _instance_lock:
        if _automation_instance is None:
            _automation_instance = AutomationEngine()
        return _automation_instance