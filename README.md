# CH9329 自动化看图控制器

基于 CH9329 芯片的自动化鼠标控制器，支持脚本执行和图片预览。

## 快速开始

### 运行程序

双击 `启动脚本.bat` 或使用命令：
```bash
python main_ui.py
```

### 主要功能

1. **串口控制** - 扫描并连接 CH9329 设备
2. **脚本执行** - 编写和执行鼠标自动化脚本
3. **图片预览** - 加载图片文件夹，支持抖动效果
4. **自动化流程** - 创建多节点自动化配置

## 文件结构

```
├── automation.py          # 自动化流程引擎
├── config_manager.py      # 配置文件管理
├── connection_handler.py  # 连接模块
├── image_manager.py       # 图片管理模块
├── main_ui.py             # 主界面模块（入口）
├── mouse_command.py       # 鼠标指令转换模块
├── script_manager.py      # 脚本文件管理
├── serial_control.py      # 串口控制模块
├── configs/               # 自动化配置目录
├── scripts/               # 脚本文件目录
├── 开发文档.md            # 开发文档
├── 使用文档.md            # 使用文档
└── 启动脚本.bat           # 启动脚本
```

## 依赖安装

```bash
pip install pyserial pillow
```

## 文档

- [开发文档.md](开发文档.md) - API接口、协议说明、代码规范
- [使用文档.md](使用文档.md) - 使用方法、脚本编写、自动化配置

## 版本

v1.0