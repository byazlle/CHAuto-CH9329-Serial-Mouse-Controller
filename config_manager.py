# -*- coding:utf-8 -*-
# 配置管理模块
import os
import json
import threading
from typing import List, Dict, Any, Optional, Tuple

CONFIGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "configs")


class ConfigManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._ensure_configs_dir()

    def _ensure_configs_dir(self):
        if not os.path.exists(CONFIGS_DIR):
            os.makedirs(CONFIGS_DIR)

    def list_configs(self) -> List[str]:
        """列出所有可用配置文件名"""
        with self._lock:
            configs = []
            for filename in os.listdir(CONFIGS_DIR):
                if filename.endswith(".json"):
                    configs.append(filename)
            return sorted(configs)

    def load_config(self, filename: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        加载配置
        
        Returns: (success, message, config_data)
        """
        filepath = os.path.join(CONFIGS_DIR, filename)
        if not os.path.exists(filepath):
            return False, "文件不存在", None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return True, "成功加载", data
        except Exception as e:
            return False, f"加载失败: {str(e)}", None

    def save_config(self, filename: str, config_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        保存配置
        
        Args:
            filename: 文件名
            config_data: 配置数据
        
        Returns: (success, message)
        """
        try:
            # 验证配置结构
            self._validate_config(config_data)

            filepath = os.path.join(CONFIGS_DIR, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            return True, f"已保存到 {filename}"
        except ValueError as e:
            return False, f"配置验证失败: {str(e)}"
        except Exception as e:
            return False, f"保存失败: {str(e)}"

    def delete_config(self, filename: str) -> Tuple[bool, str]:
        """删除配置"""
        filepath = os.path.join(CONFIGS_DIR, filename)
        if not os.path.exists(filepath):
            return False, "文件不存在"

        try:
            os.remove(filepath)
            return True, f"已删除 {filename}"
        except Exception as e:
            return False, f"删除失败: {str(e)}"

    def create_default_config(self) -> Dict[str, Any]:
        """创建空的默认配置结构"""
        return {
            "name": "新建配置",
            "version": "1.0",
            "created_at": "",
            "nodes": [],
            "image_display": {
                "shake_amplitude": 10,
                "shake_speed": 0.2
            },
            "loop": {
                "enabled": True,
                "count": 0
            }
        }

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """验证配置结构"""
        required_fields = ["name", "version", "nodes", "image_display", "loop"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"缺少必要字段: {field}")

        if "nodes" in config:
            for node in config["nodes"]:
                if "type" not in node:
                    raise ValueError("节点缺少 type 字段")

        if "image_display" in config:
            display = config["image_display"]
            if "shake_amplitude" not in display or "shake_speed" not in display:
                raise ValueError("image_display 缺少必要字段")


# 单例模式
_config_instance: Optional[ConfigManager] = None
_instance_lock = threading.Lock()


def get_config_manager() -> ConfigManager:
    """获取配置管理器单例"""
    global _config_instance
    with _instance_lock:
        if _config_instance is None:
            _config_instance = ConfigManager()
        return _config_instance