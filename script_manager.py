# -*- coding:utf-8 -*-
# 脚本管理模块
import os
import re
import threading
from typing import List, Tuple, Optional, Dict

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")


class ScriptManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._ensure_scripts_dir()

    def _ensure_scripts_dir(self):
        if not os.path.exists(SCRIPTS_DIR):
            os.makedirs(SCRIPTS_DIR)

    def list_scripts(self) -> List[str]:
        """列出所有可用脚本文件名"""
        with self._lock:
            scripts = []
            for filename in os.listdir(SCRIPTS_DIR):
                if filename.endswith(".txt"):
                    scripts.append(filename)
            return sorted(scripts)

    def load_script(self, filename: str) -> Tuple[bool, str, List[Tuple[int, int, int, int]]]:
        """
        加载脚本
        
        Returns: (success, message, commands)
        """
        filepath = os.path.join(SCRIPTS_DIR, filename)
        if not os.path.exists(filepath):
            return False, "文件不存在", []

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            success, msg, commands = self._parse_script(content)
            if not success:
                return False, msg, []
            return True, f"成功加载 {len(commands)} 条指令", commands

        except Exception as e:
            return False, f"加载失败: {str(e)}", []

    def load_script_content(self, filename: str) -> Tuple[bool, str, str]:
        """
        加载脚本原始内容（用于编辑）
        
        Returns: (success, message, content)
        """
        filepath = os.path.join(SCRIPTS_DIR, filename)
        if not os.path.exists(filepath):
            return False, "文件不存在", ""

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            return True, "成功", content
        except Exception as e:
            return False, f"加载失败: {str(e)}", ""

    def save_script(self, filename: str, content: str, validate: bool = True) -> Tuple[bool, str]:
        """
        保存脚本
        
        Args:
            filename: 文件名
            content: 脚本内容
            validate: 是否验证内容
        
        Returns: (success, message)
        """
        if validate:
            success, msg, _ = self._parse_script(content, validate_only=True)
            if not success:
                return False, msg

        try:
            filepath = os.path.join(SCRIPTS_DIR, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return True, f"已保存到 {filename}"
        except Exception as e:
            return False, f"保存失败: {str(e)}"

    def delete_script(self, filename: str) -> Tuple[bool, str]:
        """删除脚本"""
        filepath = os.path.join(SCRIPTS_DIR, filename)
        if not os.path.exists(filepath):
            return False, "文件不存在"

        try:
            os.remove(filepath)
            return True, f"已删除 {filename}"
        except Exception as e:
            return False, f"删除失败: {str(e)}"

    def _parse_script(self, content: str, validate_only: bool = False) -> Tuple[bool, str, List[Tuple[int, int, int, int]]]:
        """
        解析脚本内容
        
        Args:
            content: 脚本内容
            validate_only: 仅验证不返回结果
        
        Returns: (success, message, commands)
        """
        commands = []
        lines = content.splitlines()

        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            match = re.match(r'\((\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)', line)
            if not match:
                return False, f"第 {line_num} 行格式错误: {line}", []

            try:
                x = int(match.group(1))
                y = int(match.group(2))
                key = int(match.group(3))
                delay = int(match.group(4))

                if key not in [0, 1, 2, 3]:
                    return False, f"第 {line_num} 行 key 必须是 0-3", []

                if not validate_only:
                    commands.append((x, y, key, delay))

            except Exception as e:
                return False, f"第 {line_num} 行解析错误: {str(e)}", []

        return True, f"解析成功，共 {len(commands)} 条指令", commands


# 单例模式
_script_instance: Optional[ScriptManager] = None
_instance_lock = threading.Lock()


def get_script_manager() -> ScriptManager:
    """获取脚本管理器单例"""
    global _script_instance
    with _instance_lock:
        if _script_instance is None:
            _script_instance = ScriptManager()
        return _script_instance