# -*- coding:utf-8 -*-
# 图片循环模块
# 负责图片选择、加载、预览展示（含抖动移动效果）
import os
import threading
from typing import List, Optional, Tuple, Callable
from PIL import Image, ImageTk
import time
import math


class ImageManager:
    """图片管理器"""

    SUPPORTED_FORMATS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff")

    # 预览效果配置
    SHAKE_AMPLITUDE = 10
    FLOAT_SPEED = 0.2
    SHAKE_SPEED = 30

    def __init__(self):
        self._image_list: List[str] = []
        self._current_index: int = 0
        self._lock = threading.Lock()
        self._tkimg: Optional[ImageTk.PhotoImage] = None
        self._current_image: Optional[Image.Image] = None

    @property
    def image_list(self) -> List[str]:
        """获取图片列表"""
        with self._lock:
            return self._image_list.copy()

    @property
    def current_index(self) -> int:
        """获取当前图片索引"""
        with self._lock:
            return self._current_index

    @property
    def total_count(self) -> int:
        """获取图片总数"""
        with self._lock:
            return len(self._image_list)

    @property
    def current_image_path(self) -> str:
        """获取当前图片路径"""
        with self._lock:
            if self._image_list:
                return self._image_list[self._current_index]
            return ""

    def load_folder(self, folder_path: str) -> Tuple[bool, str, int]:
        """
        加载图片文件夹

        Returns:
            (成功标志, 消息, 图片数量)
        """
        if not folder_path or not os.path.isdir(folder_path):
            return False, "无效的文件夹路径", 0

        image_files = []
        try:
            for name in sorted(os.listdir(folder_path)):
                if name.lower().endswith(self.SUPPORTED_FORMATS):
                    image_files.append(os.path.join(folder_path, name))
        except Exception as e:
            return False, f"读取文件夹失败：{str(e)}", 0

        with self._lock:
            self._image_list = image_files
            self._current_index = 0

        count = len(image_files)
        if count > 0:
            return True, f"已加载 {count} 张图片", count
        else:
            return False, "文件夹中未找到支持的图片文件", 0

    def prev(self) -> bool:
        """
        切换到上一张（循环）
        Returns:
            是否切换成功
        """
        with self._lock:
            if not self._image_list:
                return False
            self._current_index = (self._current_index - 1) % len(self._image_list)
            return True

    def next(self) -> bool:
        """
        切换到下一张（循环）
        Returns:
            是否切换成功
        """
        with self._lock:
            if not self._image_list:
                return False
            self._current_index = (self._current_index + 1) % len(self._image_list)
            return True

    def go_to(self, index: int) -> bool:
        """
        跳转到指定索引

        Args:
            index: 目标索引

        Returns:
            是否跳转成功
        """
        with self._lock:
            if not self._image_list or index < 0 or index >= len(self._image_list):
                return False
            self._current_index = index
            return True

    def get_current_image_info(self) -> Optional[dict]:
        """
        获取当前图片信息

        Returns:
            包含路径、索引、总数的字典，无图片时返回None
        """
        with self._lock:
            if not self._image_list:
                return None
            return {
                "path": self._image_list[self._current_index],
                "index": self._current_index,
                "total": len(self._image_list),
                "filename": os.path.basename(self._image_list[self._current_index]),
            }

    def render_for_canvas(
        self,
        canvas_width: int,
        canvas_height: int,
        apply_effect: bool = True,
    ) -> Optional[Tuple[ImageTk.PhotoImage, float, float]]:
        """
        渲染当前图片供Canvas显示

        Args:
            canvas_width: 画布宽度
            canvas_height: 画布高度
            apply_effect: 是否应用抖动效果

        Returns:
            (PhotoImage, offset_x, offset_y) 或 None
        """
        with self._lock:
            if not self._image_list:
                return None
            image_path = self._image_list[self._current_index]

        if canvas_width < 50 or canvas_height < 50:
            return None

        try:
            # 关闭之前的图片释放内存
            self._close_current_image()

            # 打开并处理图片
            self._current_image = Image.open(image_path)
            w, h = self._current_image.size

            # 计算缩放比例
            scale = min(canvas_width / w, canvas_height / h) * 0.95
            new_w, new_h = int(w * scale), int(h * scale)

            # 缩放图片
            resized = self._current_image.resize(
                (new_w, new_h), Image.Resampling.LANCZOS
            )

            # 生成PhotoImage
            self._tkimg = ImageTk.PhotoImage(resized)

            # 计算偏移量（抖动效果）
            if apply_effect:
                offset_x = self.SHAKE_AMPLITUDE * math.sin(time.time() * self.FLOAT_SPEED)
                offset_y = self.SHAKE_AMPLITUDE * math.cos(time.time() * self.FLOAT_SPEED)
            else:
                offset_x = 0
                offset_y = 0

            return self._tkimg, offset_x, offset_y

        except Exception:
            return None

    def _close_current_image(self):
        """关闭当前图片释放内存"""
        if self._current_image:
            try:
                self._current_image.close()
            except Exception:
                pass
            self._current_image = None

        if self._tkimg:
            self._tkimg = None

    def clear(self):
        """清空所有图片"""
        with self._lock:
            self._close_current_image()
            self._image_list = []
            self._current_index = 0

    def get_all_images(self) -> List[dict]:
        """
        获取所有图片信息列表

        Returns:
            图片信息列表，每个元素包含 path, index, filename
        """
        with self._lock:
            if not self._image_list:
                return []
            return [
                {
                    "path": path,
                    "index": idx,
                    "filename": os.path.basename(path),
                }
                for idx, path in enumerate(self._image_list)
            ]


# 单例模式
_image_manager_instance: Optional[ImageManager] = None
_instance_lock = threading.Lock()


def get_image_manager() -> ImageManager:
    """获取图片管理器单例"""
    global _image_manager_instance
    with _instance_lock:
        if _image_manager_instance is None:
            _image_manager_instance = ImageManager()
        return _image_manager_instance
