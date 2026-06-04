# -*- coding:utf-8 -*-
# 主界面模块
# 负责界面渲染、按钮渲染，接收其他模块回传的内容进行显示
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import threading
import time
from typing import Optional, Dict, Any, List

from connection_handler import get_connection_handler
from image_manager import get_image_manager
from script_manager import get_script_manager
from config_manager import get_config_manager

COLOR_PRIMARY = "#2E86AB"
COLOR_SECONDARY = "#A23B72"
COLOR_SUCCESS = "#F18F01"
COLOR_DANGER = "#C73E1D"
COLOR_BACKGROUND = "#F8F9FA"
COLOR_TEXT = "#2C3E50"
COLOR_BORDER = "#E0E0E0"
COLOR_LOG_BG = "#1E1E1E"
COLOR_LOG_TEXT = "#00FF00"

REFRESH_INTERVAL = 500
LOG_MAX_LINES = 100


class CustomButton(tk.Button):
    """自定义按钮组件"""

    def __init__(
        self,
        master,
        text: str,
        command=None,
        bg=COLOR_PRIMARY,
        fg="white",
        hover_bg=None,
        hover_fg="white",
        font=("微软雅黑", 9),
        **kwargs,
    ):
        self.hover_bg = hover_bg if hover_bg else self._darken_color(bg, 0.1)
        self.default_bg = bg
        self.default_fg = fg
        self.hover_fg = hover_fg

        super().__init__(
            master,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            font=font,
            relief=tk.FLAT,
            bd=0,
            **kwargs,
        )

        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self._apply_style()

    def _darken_color(self, color: str, factor: float) -> str:
        r = int(color[1:3], 16) * (1 - factor)
        g = int(color[3:5], 16) * (1 - factor)
        b = int(color[5:7], 16) * (1 - factor)
        return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

    def _apply_style(self):
        self.config(padx=10, pady=3, cursor="hand2", highlightthickness=0)

    def on_enter(self, e):
        self.config(bg=self.hover_bg, fg=self.hover_fg)

    def on_leave(self, e):
        self.config(bg=self.default_bg, fg=self.default_fg)

    def set_enabled(self, enabled: bool):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.config(state=state)


class ScriptEditorWindow(tk.Toplevel):
    """脚本编辑器窗口"""

    def __init__(self, parent, filename="", content="", on_save=None):
        super().__init__(parent)
        self.title(f"脚本编辑器 - {filename if filename else '新建脚本'}")
        self.geometry("600x450")
        self.filename = filename
        self.on_save_callback = on_save
        self.script_mgr = get_script_manager()

        self._create_ui(content)

    def _create_ui(self, content):
        top_frame = tk.Frame(self, bg=COLOR_BACKGROUND)
        top_frame.pack(fill=tk.X, padx=10, pady=10)

        self.name_var = tk.StringVar(value=self.filename.replace(".txt", "") if self.filename else "")
        tk.Label(top_frame, text="脚本名称:", bg=COLOR_BACKGROUND).pack(side=tk.LEFT)
        tk.Entry(top_frame, textvariable=self.name_var, width=30).pack(side=tk.LEFT, padx=5)

        btn_frame = tk.Frame(top_frame, bg=COLOR_BACKGROUND)
        btn_frame.pack(side=tk.RIGHT)

        CustomButton(btn_frame, text="保存", command=self._on_save, bg=COLOR_SUCCESS).pack(side=tk.LEFT, padx=5)
        CustomButton(btn_frame, text="取消", command=self._on_cancel, bg=COLOR_DANGER).pack(side=tk.LEFT)

        tk.Label(self, text="脚本内容 (格式: (x, y, key, delay), 以 # 开头为注释):", anchor=tk.W).pack(fill=tk.X, padx=10, pady=(0,5))

        self.text_area = tk.Text(self, font=("Consolas", 10))
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))
        self.text_area.insert(tk.END, content)

    def _on_save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("提示", "请输入脚本名称")
            return

        filename = name if name.endswith(".txt") else name + ".txt"
        content = self.text_area.get(1.0, tk.END)

        success, msg = self.script_mgr.save_script(filename, content)
        if success:
            if self.on_save_callback:
                self.on_save_callback(filename, content)
            messagebox.showinfo("成功", msg)
            self.destroy()
        else:
            messagebox.showerror("错误", msg)

    def _on_cancel(self):
        self.destroy()


class ConfigEditorWindow(tk.Toplevel):
    """配置编辑器窗口"""

    def __init__(self, parent, filename="", config_data=None, on_save=None):
        super().__init__(parent)
        self.title(f"自动化配置编辑器 - {filename if filename else '新建配置'}")
        self.geometry("800x600")
        self.filename = filename
        self.config_data = config_data if config_data else {}
        self.on_save_callback = on_save
        self.config_mgr = get_config_manager()
        self.script_mgr = get_script_manager()

        self._create_ui()
        self._load_data()

    def _create_ui(self):
        top_frame = tk.Frame(self, bg=COLOR_BACKGROUND)
        top_frame.pack(fill=tk.X, padx=10, pady=10)

        self.name_var = tk.StringVar(value=self.config_data.get("name", "新建配置"))
        tk.Label(top_frame, text="配置名称:", bg=COLOR_BACKGROUND).pack(side=tk.LEFT)
        tk.Entry(top_frame, textvariable=self.name_var, width=30).pack(side=tk.LEFT, padx=5)

        btn_frame = tk.Frame(top_frame, bg=COLOR_BACKGROUND)
        btn_frame.pack(side=tk.RIGHT)

        CustomButton(btn_frame, text="保存", command=self._on_save, bg=COLOR_SUCCESS).pack(side=tk.LEFT, padx=5)
        CustomButton(btn_frame, text="取消", command=self._on_cancel, bg=COLOR_DANGER).pack(side=tk.LEFT)

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        nodes_frame = tk.Frame(nb)
        display_frame = tk.Frame(nb)
        loop_frame = tk.Frame(nb)

        nb.add(nodes_frame, text="节点列表")
        nb.add(display_frame, text="显示设置")
        nb.add(loop_frame, text="循环设置")

        self._create_nodes_tab(nodes_frame)
        self._create_display_tab(display_frame)
        self._create_loop_tab(loop_frame)

    def _create_nodes_tab(self, parent):
        left_frame = tk.Frame(parent)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=8)

        tk.Label(left_frame, text="自动化节点列表:", anchor=tk.W).pack(fill=tk.X)

        self.nodes_listbox = tk.Listbox(left_frame, height=15)
        self.nodes_listbox.pack(fill=tk.BOTH, expand=True)

        btn_row = tk.Frame(left_frame)
        btn_row.pack(fill=tk.X, pady=5)

        CustomButton(btn_row, text="+ 添加脚本", command=self._add_script_node, bg=COLOR_PRIMARY).pack(side=tk.LEFT, padx=2)
        CustomButton(btn_row, text="+ 延时", command=self._add_delay_node, bg=COLOR_PRIMARY).pack(side=tk.LEFT, padx=2)
        CustomButton(btn_row, text="+ 图片切换", command=self._add_image_node, bg=COLOR_PRIMARY).pack(side=tk.LEFT, padx=2)
        tk.Frame(btn_row, width=10).pack(side=tk.LEFT)
        CustomButton(btn_row, text="↑ 上移", command=self._move_node_up, bg=COLOR_SECONDARY).pack(side=tk.LEFT, padx=2)
        CustomButton(btn_row, text="↓ 下移", command=self._move_node_down, bg=COLOR_SECONDARY).pack(side=tk.LEFT, padx=2)
        CustomButton(btn_row, text="删除", command=self._remove_node, bg=COLOR_DANGER).pack(side=tk.LEFT, padx=2)

        right_frame = tk.Frame(parent)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=8)

        tk.Label(right_frame, text="节点编辑:", anchor=tk.W).pack(fill=tk.X)
        self.node_edit_frame = tk.Frame(right_frame, bg="white", relief=tk.SUNKEN, bd=2)
        self.node_edit_frame.pack(fill=tk.Y, padx=5, pady=5)

        self.nodes = []

    def _create_display_tab(self, parent):
        frame = tk.Frame(parent, bg=COLOR_BACKGROUND)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(frame, text="抖动幅度:", bg=COLOR_BACKGROUND).grid(row=0, column=0, sticky=tk.W, pady=3)
        self.shake_amp_var = tk.StringVar(value="10")
        tk.Entry(frame, textvariable=self.shake_amp_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=8)

        tk.Label(frame, text="抖动速度:", bg=COLOR_BACKGROUND).grid(row=1, column=0, sticky=tk.W, pady=3)
        self.shake_speed_var = tk.StringVar(value="0.2")
        tk.Entry(frame, textvariable=self.shake_speed_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=8)

    def _create_loop_tab(self, parent):
        frame = tk.Frame(parent, bg=COLOR_BACKGROUND)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.loop_enable_var = tk.BooleanVar(value=True)
        tk.Checkbutton(frame, text="启用循环", variable=self.loop_enable_var, bg=COLOR_BACKGROUND).pack(anchor=tk.W, pady=3)

        tk.Label(frame, text="循环次数 (0=无限):", bg=COLOR_BACKGROUND).pack(anchor=tk.W, pady=3)
        self.loop_count_var = tk.StringVar(value="0")
        tk.Entry(frame, textvariable=self.loop_count_var, width=10).pack(anchor=tk.W, padx=8)

    def _load_data(self):
        if "nodes" in self.config_data:
            self.nodes = self.config_data["nodes"]
            self._refresh_nodes_list()

        if "image_display" in self.config_data:
            disp = self.config_data["image_display"]
            self.shake_amp_var.set(str(disp.get("shake_amplitude", 10)))
            self.shake_speed_var.set(str(disp.get("shake_speed", 0.2)))

        if "loop" in self.config_data:
            loop = self.config_data["loop"]
            self.loop_enable_var.set(loop.get("enabled", True))
            self.loop_count_var.set(str(loop.get("count", 0)))

    def _refresh_nodes_list(self):
        self.nodes_listbox.delete(0, tk.END)
        for i, node in enumerate(self.nodes):
            desc = self._get_node_desc(node)
            self.nodes_listbox.insert(tk.END, f"{i+1}. {desc}")

    def _get_node_desc(self, node):
        t = node.get("type")
        if t == "script":
            return f"脚本: {node.get('name', '未命名')}"
        elif t == "delay":
            return f"延时: {node.get('duration_ms', 1000)}ms"
        elif t == "image_switch":
            d = "下一张" if node.get("direction") == "next" else "上一张"
            return f"切换图片: {d}"
        elif t == "image_goto":
            return f"跳转图片: 第{node.get('index', 0)}张"
        elif t == "mouse_move":
            return f"鼠标操作: ({node.get('x')}, {node.get('y')}"
        else:
            return "未知节点"

    def _add_script_node(self):
        scripts = self.script_mgr.list_scripts()
        if not scripts:
            messagebox.showinfo("提示", "没有可用的脚本，请先创建脚本")
            return

        win = tk.Toplevel(self)
        win.title("选择脚本")
        win.geometry("400x300")

        lb = tk.Listbox(win)
        lb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        for s in scripts:
            lb.insert(tk.END, s)

        def select():
            sel = lb.curselection()
            if not sel:
                return
            name = lb.get(sel[0])
            success, msg, content = self.script_mgr.load_script_content(name)
            if success:
                self.nodes.append({
                    "type": "script",
                    "name": name.replace(".txt", ""),
                    "content": content,
                    "delay_after_ms": 500
                })
                self._refresh_nodes_list()
            win.destroy()

        btn = CustomButton(win, text="确定", command=select, bg=COLOR_SUCCESS)
        btn.pack(pady=8)

    def _add_delay_node(self):
        val = tk.simpledialog.askinteger("输入延时", "延时 (ms):", initialvalue=2000)
        if val is not None:
            self.nodes.append({"type": "delay", "duration_ms": val})
            self._refresh_nodes_list()

    def _add_image_node(self):
        choice = messagebox.askyesnocancel("选择方向", "点击 YES 选择下一张，NO 选择上一张")
        if choice is not None:
            direction = "next" if choice else "prev"
            self.nodes.append({"type": "image_switch", "direction": direction})
            self._refresh_nodes_list()

    def _remove_node(self):
        sel = self.nodes_listbox.curselection()
        if sel:
            idx = sel[0]
            del self.nodes[idx]
            self._refresh_nodes_list()

    def _move_node_up(self):
        sel = self.nodes_listbox.curselection()
        if sel and sel[0] > 0:
            idx = sel[0]
            self.nodes[idx], self.nodes[idx-1] = self.nodes[idx-1], self.nodes[idx]
            self._refresh_nodes_list()
            self.nodes_listbox.select_set(idx-1)

    def _move_node_down(self):
        sel = self.nodes_listbox.curselection()
        if sel and sel[0] < len(self.nodes)-1:
            idx = sel[0]
            self.nodes[idx], self.nodes[idx+1] = self.nodes[idx+1], self.nodes[idx]
            self._refresh_nodes_list()
            self.nodes_listbox.select_set(idx+1)

    def _on_save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("提示", "请输入配置名称")
            return

        filename = name if name.endswith(".json") else name + ".json"

        try:
            shake_amp = float(self.shake_amp_var.get())
            shake_speed = float(self.shake_speed_var.get())
            loop_count = int(self.loop_count_var.get())
        except:
            messagebox.showerror("错误", "请输入有效的数值")
            return

        config = {
            "name": name,
            "version": "1.0",
            "created_at": time.strftime("%Y-%m-%d"),
            "nodes": list(self.nodes),
            "image_display": {
                "shake_amplitude": shake_amp,
                "shake_speed": shake_speed
            },
            "loop": {
                "enabled": self.loop_enable_var.get(),
                "count": loop_count
            }
        }

        success, msg = self.config_mgr.save_config(filename, config)
        if success:
            if self.on_save_callback:
                self.on_save_callback(filename, config)
            messagebox.showinfo("成功", msg)
            self.destroy()
        else:
            messagebox.showerror("错误", msg)

    def _on_cancel(self):
        self.destroy()


class AppUI:
    """主界面类"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("CH9329 自动化看图控制器")
        self.root.geometry("900x750")
        self.root.resizable(True, True)
        self.root.configure(bg=COLOR_BACKGROUND)

        default_font = ("微软雅黑", 9)
        self.root.option_add("*Font", default_font)

        self._handler = get_connection_handler()
        self._image_mgr = get_image_manager()
        self._script_mgr = get_script_manager()
        self._config_mgr = get_config_manager()

        self._tkimg = None
        self._log_lines: list = []
        self._port_name_map: Dict[str, str] = {}
        self._current_config: Optional[Dict[str, Any]] = None

        self._handler.set_callbacks(
            on_status_update=self._update_status,
            on_com_update=self._update_com_status,
            on_log_message=self._add_log,
            on_error=self._show_error,
        )

        self._create_ui()
        self._auto_refresh()

    def _create_ui(self):
        top_frame = tk.Frame(self.root, bg=COLOR_BACKGROUND)
        top_frame.pack(fill=tk.X, padx=15, pady=(8, 0))

        tk.Label(top_frame, text="CH9329 自动化看图控制器", font=("微软雅黑", 15, "bold"),
                 bg=COLOR_BACKGROUND, fg=COLOR_PRIMARY).pack(side=tk.LEFT)

        status_frame = tk.Frame(top_frame, bg=COLOR_BACKGROUND)
        status_frame.pack(side=tk.RIGHT)

        self.com_status_var = tk.StringVar(value="串口: 未连接")
        self.run_status_var = tk.StringVar(value="状态: 空闲")

        tk.Label(status_frame, textvariable=self.com_status_var,
                 bg=COLOR_BACKGROUND, fg=COLOR_TEXT).pack(side=tk.LEFT, padx=8)
        tk.Label(status_frame, textvariable=self.run_status_var,
                 bg=COLOR_BACKGROUND, fg=COLOR_TEXT).pack(side=tk.LEFT, padx=8)

        main_frame = tk.Frame(self.root, bg=COLOR_BACKGROUND)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=12)

        left_col = tk.Frame(main_frame, bg=COLOR_BACKGROUND, width=360)
        left_col.pack(side=tk.LEFT, fill=tk.Y, padx=(0,8))

        right_col = tk.Frame(main_frame, bg=COLOR_BACKGROUND)
        right_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._create_serial_section(left_col)
        self._create_script_section(left_col)
        self._create_automation_section(left_col)
        self._create_log_section(left_col)

        self._create_image_control_section(right_col)

    def _create_card(self, parent, title, pack_fill=tk.X, pack_expand=False, pack_side=None):
        card = tk.Frame(parent, bg=COLOR_BORDER, bd=1, relief=tk.FLAT)
        if pack_side:
            card.pack(side=pack_side, fill=pack_fill, expand=pack_expand, pady=(0,8))
        else:
            card.pack(fill=pack_fill, expand=pack_expand, pady=(0,8))

        card_inner = tk.Frame(card, bg="white")
        card_inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        title_frame = tk.Frame(card_inner, bg=COLOR_PRIMARY)
        title_frame.pack(fill=tk.X)
        tk.Label(title_frame, text=title, font=("微软雅黑", 10, "bold"),
                 bg=COLOR_PRIMARY, fg="white", padx=10, pady=4).pack(side=tk.LEFT)

        content = tk.Frame(card_inner, bg="white")
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        return content

    def _create_serial_section(self, parent):
        frame = self._create_card(parent, "串口控制")

        CustomButton(frame, text="扫描串口", command=self._on_scan_com, bg=COLOR_PRIMARY).grid(row=0, column=0, padx=2, pady=3)

        self.com_var = tk.StringVar()
        self.cb_com = ttk.Combobox(frame, textvariable=self.com_var, width=20, state="readonly")
        self.cb_com.grid(row=0, column=1, padx=2, pady=3)

        CustomButton(frame, text="连接", command=self._on_connect, bg=COLOR_SUCCESS).grid(row=0, column=2, padx=2, pady=3)
        CustomButton(frame, text="断开", command=self._on_disconnect, bg=COLOR_DANGER).grid(row=0, column=3, padx=2, pady=3)

    def _create_script_section(self, parent):
        frame = self._create_card(parent, "脚本控制")

        tk.Label(frame, text="脚本:", bg="white").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.script_var = tk.StringVar()
        self.cb_script = ttk.Combobox(frame, textvariable=self.script_var, width=22, state="readonly")
        self.cb_script.grid(row=0, column=1, columnspan=2, padx=2, pady=3)

        CustomButton(frame, text="编辑", command=self._on_edit_script, bg=COLOR_PRIMARY).grid(row=0, column=3, padx=2, pady=3)

        CustomButton(frame, text="执行当前", command=self._on_run_script, bg=COLOR_SUCCESS).grid(row=1, column=0, columnspan=2, padx=2, pady=6)
        CustomButton(frame, text="新建脚本", command=self._on_new_script, bg=COLOR_SECONDARY).grid(row=1, column=2, columnspan=2, padx=2, pady=6)

        self._refresh_scripts()

    def _create_log_section(self, parent):
        frame = self._create_card(parent, "运行日志", pack_fill=tk.BOTH, pack_expand=True)

        log_container = tk.Frame(frame, bg=COLOR_LOG_BG)
        log_container.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_container, bg=COLOR_LOG_BG, fg=COLOR_LOG_TEXT,
                                font=("Consolas", 8), relief=tk.FLAT, bd=0, state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(log_container, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

    def _create_image_control_section(self, parent):
        frame = self._create_card(parent, "图片控制")

        CustomButton(frame, text="选择文件夹", command=self._on_select_folder, bg=COLOR_SECONDARY).grid(row=0, column=0, columnspan=4, pady=3, sticky=tk.EW)

        tk.Label(frame, text="图片:", bg="white").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.img_status_var = tk.StringVar(value="0/0")
        tk.Label(frame, textvariable=self.img_status_var, bg="white",
                 font=("微软雅黑", 9, "bold")).grid(row=1, column=1, columnspan=3, sticky=tk.W, padx=5)

        btn_row = tk.Frame(frame, bg="white")
        btn_row.grid(row=2, column=0, columnspan=4, pady=5)
        CustomButton(btn_row, text="上一张", command=self._on_prev_image, bg=COLOR_PRIMARY).pack(side=tk.LEFT, padx=2)
        CustomButton(btn_row, text="下一张", command=self._on_next_image, bg=COLOR_PRIMARY).pack(side=tk.LEFT, padx=2)

        shake_frame = tk.Frame(frame, bg="white")
        shake_frame.grid(row=3, column=0, columnspan=4, pady=8, sticky=tk.EW)

        tk.Label(shake_frame, text="抖动幅度:", bg="white").grid(row=0, column=0, sticky=tk.W)
        self.shake_amp_var = tk.StringVar(value="10")
        tk.Entry(shake_frame, textvariable=self.shake_amp_var, width=10).grid(row=0, column=1, padx=5, sticky=tk.W)

        tk.Label(shake_frame, text="抖动速度:", bg="white").grid(row=0, column=2, sticky=tk.W, padx=(12,0))
        self.shake_speed_var = tk.StringVar(value="0.2")
        tk.Entry(shake_frame, textvariable=self.shake_speed_var, width=10).grid(row=0, column=3, padx=5, sticky=tk.W)

        prev_frame = self._create_card(parent, "图片预览", pack_fill=tk.BOTH, pack_expand=True)

        self.canvas = tk.Canvas(prev_frame, bg="#f5f5f5", relief=tk.FLAT, bd=1, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.empty_text = self.canvas.create_text(0, 0, text="未选择图片文件夹\n或文件夹中无图片文件",
                                                  font=("微软雅黑", 11), fill="#999", anchor=tk.CENTER)

    def _create_automation_section(self, parent):
        frame = self._create_card(parent, "自动化控制")

        row0 = tk.Frame(frame, bg="white")
        row0.pack(fill=tk.X, pady=3)

        tk.Label(row0, text="配置:", bg="white").pack(side=tk.LEFT)
        self.config_var = tk.StringVar()
        self.cb_config = ttk.Combobox(row0, textvariable=self.config_var, width=22, state="readonly")
        self.cb_config.pack(side=tk.LEFT, padx=5)

        CustomButton(row0, text="保存", command=self._on_save_config, bg=COLOR_PRIMARY).pack(side=tk.LEFT, padx=2)
        CustomButton(row0, text="编辑", command=self._on_edit_config, bg=COLOR_PRIMARY).pack(side=tk.LEFT, padx=2)
        CustomButton(row0, text="新建", command=self._on_new_config, bg=COLOR_SECONDARY).pack(side=tk.LEFT, padx=2)

        tk.Label(frame, text="节点列表:", anchor=tk.W, bg="white").pack(fill=tk.X, pady=(8,3))

        nodes_frame = tk.Frame(frame, bg="white")
        nodes_frame.pack(fill=tk.BOTH, expand=True)

        self.automation_nodes_listbox = tk.Listbox(nodes_frame, height=5)
        self.automation_nodes_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_nodes = tk.Scrollbar(nodes_frame, command=self.automation_nodes_listbox.yview)
        scroll_nodes.pack(side=tk.RIGHT, fill=tk.Y)
        self.automation_nodes_listbox.config(yscrollcommand=scroll_nodes.set)

        btn_row = tk.Frame(frame, bg="white")
        btn_row.pack(fill=tk.X, pady=8)

        self.auto_btn = CustomButton(btn_row, text="开始自动化", command=self._on_toggle_auto, bg=COLOR_SUCCESS)
        self.auto_btn.pack(side=tk.LEFT, padx=2)
        CustomButton(btn_row, text="停止", command=self._on_stop_auto, bg=COLOR_DANGER).pack(side=tk.LEFT, padx=2)

        self._refresh_configs()

    def _update_status(self, status: str):
        self.run_status_var.set(f"状态: {status}")
        if status == "运行中":
            self.auto_btn.config(text="运行中...", bg=COLOR_DANGER)
        else:
            self.auto_btn.config(text="开始自动化", bg=COLOR_SUCCESS)
            if self._handler.is_serial_connected():
                self.auto_btn.set_enabled(True)
            else:
                self.auto_btn.set_enabled(False)

    def _update_com_status(self, status: str):
        self.com_status_var.set(status)

    def _add_log(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"
        self._log_lines.append(log_line)
        if len(self._log_lines) > LOG_MAX_LINES:
            self._log_lines.pop(0)

        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, "".join(self._log_lines))
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _show_error(self, title: str, message: str):
        messagebox.showerror(title, message)

    def _on_scan_com(self):
        threading.Thread(target=self._scan_com_worker, daemon=True).start()

    def _scan_com_worker(self):
        success, msg, port_infos, ch340_port = self._handler.scan_serial_ports()
        self.root.after(0, lambda: self._on_scan_com_result(success, msg, port_infos, ch340_port))

    def _on_scan_com_result(self, success, msg, port_infos, ch340_port):
        if success:
            self._port_name_map = {disp: dev for dev, disp in port_infos}
            self.cb_com["values"] = [disp for _, disp in port_infos]
            if ch340_port:
                for i, (dev, disp) in enumerate(port_infos):
                    if dev == ch340_port:
                        self.cb_com.current(i)
                        break
            elif port_infos:
                self.cb_com.current(0)
        messagebox.showinfo("扫描结果", msg)

    def _on_connect(self):
        selected_disp = self.com_var.get()
        if not selected_disp:
            messagebox.showwarning("提示", "请先选择串口")
            return

        port = self._port_name_map.get(selected_disp, selected_disp)
        threading.Thread(target=self._connect_worker, args=(port,), daemon=True).start()

    def _connect_worker(self, port):
        success, msg = self._handler.connect_serial(port)
        if not success:
            self.root.after(0, lambda: messagebox.showerror("错误", msg))

    def _on_disconnect(self):
        threading.Thread(target=self._disconnect_worker, daemon=True).start()

    def _disconnect_worker(self):
        success, msg = self._handler.disconnect_serial()
        if success:
            self.root.after(0, lambda: messagebox.showinfo("提示", msg))

    def _refresh_scripts(self):
        scripts = self._script_mgr.list_scripts()
        self.cb_script["values"] = scripts
        if scripts:
            self.cb_script.current(0)

    def _on_new_script(self):
        def on_save(filename, content):
            self._refresh_scripts()
            self.script_var.set(filename)
        ScriptEditorWindow(self.root, filename="", content="", on_save=on_save)

    def _on_edit_script(self):
        filename = self.script_var.get()
        if not filename:
            messagebox.showwarning("提示", "请先选择脚本")
            return

        success, msg, content = self._script_mgr.load_script_content(filename)
        if not success:
            messagebox.showerror("错误", msg)
            return

        def on_save(new_filename, new_content):
            self._refresh_scripts()
            self.script_var.set(new_filename)

        ScriptEditorWindow(self.root, filename=filename, content=content, on_save=on_save)

    def _on_run_script(self):
        filename = self.script_var.get()
        if not filename:
            messagebox.showwarning("提示", "请先选择脚本")
            return
        threading.Thread(target=self._run_script_worker, args=(filename,), daemon=True).start()

    def _run_script_worker(self, filename):
        success, msg = self._handler.run_single_script(filename)
        if not success:
            self.root.after(0, lambda: messagebox.showwarning("提示", msg))

    def _refresh_configs(self):
        configs = self._config_mgr.list_configs()
        self.cb_config["values"] = configs
        if configs:
            self.cb_config.current(0)
            self._load_config(configs[0])

    def _load_config(self, filename):
        success, msg, data = self._config_mgr.load_config(filename)
        if success:
            self._current_config = data
            self._update_nodes_display(data.get("nodes", []))

    def _update_nodes_display(self, nodes):
        self.automation_nodes_listbox.delete(0, tk.END)
        for i, node in enumerate(nodes):
            t = node.get("type")
            if t == "script":
                desc = f"脚本: {node.get('name')}"
            elif t == "delay":
                desc = f"延时: {node.get('duration_ms')}ms"
            elif t == "image_switch":
                d = "下一张" if node.get("direction") == "next" else "上一张"
                desc = f"切换图片: {d}"
            else:
                desc = "节点"
            self.automation_nodes_listbox.insert(tk.END, f"{i+1}. {desc}")

    def _on_new_config(self):
        def on_save(filename, data):
            self._refresh_configs()
            self.config_var.set(filename)

        ConfigEditorWindow(self.root, filename="", config_data=self._config_mgr.create_default_config(), on_save=on_save)

    def _on_edit_config(self):
        filename = self.config_var.get()
        if not filename:
            messagebox.showwarning("提示", "请先选择配置")
            return

        success, msg, data = self._config_mgr.load_config(filename)
        if not success:
            messagebox.showerror("错误", msg)
            return

        def on_save(new_filename, new_data):
            self._refresh_configs()
            self.config_var.set(new_filename)
            self._load_config(new_filename)

        ConfigEditorWindow(self.root, filename=filename, config_data=data, on_save=on_save)

    def _on_save_config(self):
        filename = self.config_var.get()
        if not filename or not self._current_config:
            messagebox.showwarning("提示", "请先选择配置")
            return

        success, msg = self._config_mgr.save_config(filename, self._current_config)
        if success:
            messagebox.showinfo("成功", msg)
        else:
            messagebox.showerror("错误", msg)

    def _on_toggle_auto(self):
        if self._handler.is_automation_running():
            self._handler.stop_automation()
        else:
            if not self._current_config:
                messagebox.showwarning("提示", "请先加载配置")
                return
            threading.Thread(target=self._start_auto_worker, daemon=True).start()

    def _start_auto_worker(self):
        config = dict(self._current_config)

        try:
            amp = float(self.shake_amp_var.get())
            speed = float(self.shake_speed_var.get())
            config["image_display"]["shake_amplitude"] = amp
            config["image_display"]["shake_speed"] = speed
        except:
            pass

        success, msg = self._handler.start_automation(config)
        if not success:
            self.root.after(0, lambda: messagebox.showwarning("提示", msg))

    def _on_stop_auto(self):
        self._handler.stop_automation()

    def _on_select_folder(self):
        folder = filedialog.askdirectory(title="选择图片文件夹")
        if folder:
            threading.Thread(target=self._load_folder_worker, args=(folder,), daemon=True).start()

    def _load_folder_worker(self, folder):
        success, msg, count = self._image_mgr.load_folder(folder)
        self.root.after(
            0,
            lambda: (
                messagebox.showinfo("成功", msg) if success else messagebox.showwarning("提示", msg)
            ),
        )

    def _on_prev_image(self):
        self._image_mgr.prev()

    def _on_next_image(self):
        self._image_mgr.next()

    def _refresh_image_status(self):
        info = self._image_mgr.get_current_image_info()
        if info:
            self.img_status_var.set(f"{info['index']+1}/{info['total']}")
        else:
            self.img_status_var.set("0/0")

    def _refresh_image(self):
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw < 50 or ch < 50:
            return

        self.canvas.coords(self.empty_text, cw // 2, ch // 2)

        if not self._image_mgr.image_list:
            self.canvas.itemconfig(self.empty_text, state=tk.NORMAL)
            self.canvas.delete("image")
            return

        self.canvas.itemconfig(self.empty_text, state=tk.HIDDEN)

        try:
            amp = float(self.shake_amp_var.get())
            speed = float(self.shake_speed_var.get())
        except:
            amp, speed = 10, 0.2

        self._image_mgr.SHAKE_AMPLITUDE = amp
        self._image_mgr.FLOAT_SPEED = speed

        result = self._image_mgr.render_for_canvas(cw, ch, apply_effect=True)
        if result:
            self._tkimg, ox, oy = result
            self.canvas.delete("image")
            self.canvas.create_image(
                cw // 2 + ox, ch // 2 + oy, image=self._tkimg, anchor=tk.CENTER, tag="image"
            )

    def _auto_refresh(self):
        try:
            self._refresh_image()
            self._refresh_image_status()
        except Exception as e:
            print(f"刷新错误: {e}")

        self.root.after(REFRESH_INTERVAL, self._auto_refresh)


if __name__ == "__main__":
    root = tk.Tk()
    app = AppUI(root)
    root.mainloop()
