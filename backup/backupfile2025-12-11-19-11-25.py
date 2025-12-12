import time
import os
import webbrowser
import pyautogui
import cv2
import numpy as np
from PIL import Image
import threading  # For running the script in a separate thread
import ctypes
from pynput import keyboard
import datetime
import re

import tkinter as tk  # 保留用于兼容性
from tkinter import ttk  # 保留用于兼容性
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import json  # 用于保存和加载参数
import mss

# =========================
# OCR引擎初始化（使用rapidocr，速度快）
# =========================
try:
    from rapidocr_onnxruntime import RapidOCR
    ocr_engine = RapidOCR()
    OCR_AVAILABLE = True
    print("✅ [OCR] RapidOCR 引擎加载成功")
except ImportError:
    OCR_AVAILABLE = False
    ocr_engine = None
    print("⚠️  [OCR] RapidOCR 未安装，钓鱼记录功能将不可用")

# =========================
# 线程锁 - 保护共享变量
# =========================
param_lock = threading.Lock()  # 参数读写锁

# =========================
# 参数文件路径
# =========================
PARAMETER_FILE = "./parameters.json"
# =========================
# 加载和保存参数
# =========================
def save_parameters():
    params = {
        "t": t,
        "leftclickdown": leftclickdown,
        "leftclickup": leftclickup,
        "times": times,
        "paogantime": paogantime,
        "jiashi_var": jiashi_var,  # 保存加时参数
        "resolution": resolution_choice,  # 保存分辨率选择
        "custom_width": TARGET_WIDTH,  # 保存自定义宽度
        "custom_height": TARGET_HEIGHT  # 保存自定义高度
    }
    try:
        with open(PARAMETER_FILE, "w") as f:
            json.dump(params, f)
        print("💾 [保存] 参数已成功保存到文件")
    except Exception as e:
        print(f"❌ [错误] 保存参数失败: {e}")

def load_parameters():
    global t, leftclickdown, leftclickup, times, paogantime, jiashi_var
    global resolution_choice, TARGET_WIDTH, TARGET_HEIGHT, SCALE_X, SCALE_Y
    try:
        with open(PARAMETER_FILE, "r") as f:
            params = json.load(f)
            t = params.get("t", t)
            leftclickdown = params.get("leftclickdown", leftclickdown)
            leftclickup = params.get("leftclickup", leftclickup)
            times = params.get("times", times)
            paogantime = params.get("paogantime", paogantime)
            jiashi_var = params.get("jiashi_var", jiashi_var)
            resolution_choice = params.get("resolution", "2K")
            # 根据分辨率选择设置目标分辨率
            if resolution_choice == "1080P":
                TARGET_WIDTH, TARGET_HEIGHT = 1920, 1080
            elif resolution_choice == "2K":
                TARGET_WIDTH, TARGET_HEIGHT = 2560, 1440
            elif resolution_choice == "4K":
                TARGET_WIDTH, TARGET_HEIGHT = 3840, 2160
            elif resolution_choice == "自定义":
                TARGET_WIDTH = params.get("custom_width", 2560)
                TARGET_HEIGHT = params.get("custom_height", 1440)
            # 重新计算缩放比例
            SCALE_X = TARGET_WIDTH / BASE_WIDTH
            SCALE_Y = TARGET_HEIGHT / BASE_HEIGHT
            update_region_coords()  # 更新区域坐标
            #print(f"已加载参数: 循环间隔 = {t}, 收线时间 = {leftclickdown}, 放线时间 = {leftclickup}, 最大拉杆次数 = {times}，抛竿时间 = {paogantime}, 加时 = {jiashi_var}")
    except FileNotFoundError:
        print("📄 [信息] 未找到参数文件，使用默认值")
    except Exception as e:
        print(f"❌ [错误] 加载参数失败: {e}")

# =========================
# 更新参数
# =========================
def update_parameters(t_var, leftclickdown_var, leftclickup_var, times_var, paogantime_var, jiashi_var_option,
                      resolution_var, custom_width_var, custom_height_var):
    global t, leftclickdown, leftclickup, times, paogantime, jiashi_var
    global resolution_choice, TARGET_WIDTH, TARGET_HEIGHT, SCALE_X, SCALE_Y

    with param_lock:  # 使用锁保护参数更新
        try:
            t = float(t_var.get())
            leftclickdown = float(leftclickdown_var.get())
            leftclickup = float(leftclickup_var.get())
            times = int(times_var.get())
            paogantime = float(paogantime_var.get())
            jiashi_var = jiashi_var_option.get()

            # 更新分辨率设置
            resolution_choice = resolution_var.get()
            if resolution_choice == "1080P":
                TARGET_WIDTH, TARGET_HEIGHT = 1920, 1080
            elif resolution_choice == "2K":
                TARGET_WIDTH, TARGET_HEIGHT = 2560, 1440
            elif resolution_choice == "4K":
                TARGET_WIDTH, TARGET_HEIGHT = 3840, 2160
            elif resolution_choice == "自定义":
                TARGET_WIDTH = int(custom_width_var.get())
                TARGET_HEIGHT = int(custom_height_var.get())

            # 重新计算缩放比例
            SCALE_X = TARGET_WIDTH / BASE_WIDTH
            SCALE_Y = TARGET_HEIGHT / BASE_HEIGHT
            update_region_coords()  # 更新区域坐标

            print("┌" + "─" * 48 + "┐")
            print("│  ⚙️  参数更新成功                              │")
            print("├" + "─" * 48 + "┤")
            print(f"│  ⏱️  循环间隔: {t:.1f}s    📍 收线: {leftclickdown:.1f}s    📍 放线: {leftclickup:.1f}s")
            print(f"│  🎣 最大拉杆: {times}次     ⏳ 抛竿: {paogantime:.1f}s    {'✅' if jiashi_var else '❌'} 加时: {'是' if jiashi_var else '否'}")
            print(f"│  🖥️  分辨率: {resolution_choice} ({TARGET_WIDTH}×{TARGET_HEIGHT})")
            print(f"│  📐 缩放比例: X={SCALE_X:.2f}  Y={SCALE_Y:.2f}")
            print("└" + "─" * 48 + "┘")
            # 保存到文件
            save_parameters()
        except ValueError as e:
            print(f"⚠️  [警告] 请输入有效的数值！错误: {e}")
        except Exception as e:
            print(f"❌ [错误] 更新参数失败: {e}")

# =========================
# 创建 Tkinter 窗口（现代化UI设计 - 左右分栏布局）
# =========================
def create_gui():
    # 加载保存的参数
    load_parameters()

    # 创建现代化主题窗口
    root = ttkb.Window(themename="darkly")  # 使用深色主题
    root.title("🎣 PartyFish 自动钓鱼助手")
    root.geometry("950x680")  # 增加高度以容纳所有内容
    root.minsize(900, 650)    # 最小尺寸
    root.resizable(True, True)  # 允许调整大小

    # 设置窗口图标（如果有的话）
    try:
        root.iconbitmap("icon.ico")
    except:
        pass

    # ==================== 主容器（固定布局，左右分栏） ====================
    main_frame = ttkb.Frame(root, padding=12)
    main_frame.pack(fill=BOTH, expand=YES)

    # 配置主框架的行列权重
    main_frame.columnconfigure(0, weight=0, minsize=300)  # 左侧固定宽度
    main_frame.columnconfigure(1, weight=1, minsize=500)  # 右侧自适应扩展
    main_frame.rowconfigure(0, weight=1)  # 内容区域自适应高度

    # ==================== 左侧面板（设置区域） ====================
    left_panel = ttkb.Frame(main_frame)
    left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

    # ==================== 标题区域 ====================
    title_frame = ttkb.Frame(left_panel)
    title_frame.pack(fill=X, pady=(0, 8))

    title_label = ttkb.Label(
        title_frame,
        text="🎣 PartyFish",
        font=("Segoe UI", 16, "bold"),
        bootstyle="light"
    )
    title_label.pack()

    subtitle_label = ttkb.Label(
        title_frame,
        text="自动钓鱼参数配置",
        font=("Segoe UI", 8),
        bootstyle="light"
    )
    subtitle_label.pack()

    # ==================== 钓鱼参数卡片 ====================
    params_card = ttkb.Labelframe(
        left_panel,
        text=" ⚙️ 钓鱼参数 ",
        padding=10,
        bootstyle="info"
    )
    params_card.pack(fill=X, pady=(0, 6))

    # 参数输入样式
    def create_param_row(parent, label_text, var, row, tooltip=""):
        label = ttkb.Label(parent, text=label_text, font=("Segoe UI", 9))
        label.grid(row=row, column=0, sticky=W, pady=3, padx=(0, 8))

        entry = ttkb.Entry(parent, textvariable=var, width=10, font=("Segoe UI", 9))
        entry.grid(row=row, column=1, sticky=E, pady=3)
        return entry

    # 循环间隔
    t_var = ttkb.StringVar(value=str(t))
    create_param_row(params_card, "循环间隔 (秒)", t_var, 0)

    # 收线时间
    leftclickdown_var = ttkb.StringVar(value=str(leftclickdown))
    create_param_row(params_card, "收线时间 (秒)", leftclickdown_var, 1)

    # 放线时间
    leftclickup_var = ttkb.StringVar(value=str(leftclickup))
    create_param_row(params_card, "放线时间 (秒)", leftclickup_var, 2)

    # 最大拉线次数
    times_var = ttkb.StringVar(value=str(times))
    create_param_row(params_card, "最大拉杆次数", times_var, 3)

    # 抛竿时间
    paogantime_var = ttkb.StringVar(value=str(paogantime))
    create_param_row(params_card, "抛竿时间 (秒)", paogantime_var, 4)

    # 配置列宽
    params_card.columnconfigure(0, weight=1)
    params_card.columnconfigure(1, weight=0)

    # ==================== 加时选项卡片 ====================
    jiashi_card = ttkb.Labelframe(
        left_panel,
        text=" ⏱️ 加时选项 ",
        padding=10,
        bootstyle="warning"
    )
    jiashi_card.pack(fill=X, pady=(0, 6))

    jiashi_var_option = ttkb.IntVar(value=jiashi_var)

    jiashi_frame = ttkb.Frame(jiashi_card)
    jiashi_frame.pack(fill=X)

    jiashi_label = ttkb.Label(jiashi_frame, text="是否自动加时", font=("Segoe UI", 9))
    jiashi_label.pack(side=LEFT)

    jiashi_btn_frame = ttkb.Frame(jiashi_frame)
    jiashi_btn_frame.pack(side=RIGHT)

    jiashi_yes = ttkb.Radiobutton(
        jiashi_btn_frame,
        text="是",
        variable=jiashi_var_option,
        value=1,
        bootstyle="success-outline-toolbutton"
    )
    jiashi_yes.pack(side=LEFT, padx=5)

    jiashi_no = ttkb.Radiobutton(
        jiashi_btn_frame,
        text="否",
        variable=jiashi_var_option,
        value=0,
        bootstyle="danger-outline-toolbutton"
    )
    jiashi_no.pack(side=LEFT, padx=5)

    # ==================== 分辨率设置卡片 ====================
    resolution_card = ttkb.Labelframe(
        left_panel,
        text=" 🖥️ 分辨率设置 ",
        padding=10,
        bootstyle="success"
    )
    resolution_card.pack(fill=X, pady=(0, 6))

    resolution_var = ttkb.StringVar(value=resolution_choice)
    custom_width_var = ttkb.StringVar(value=str(TARGET_WIDTH))
    custom_height_var = ttkb.StringVar(value=str(TARGET_HEIGHT))

    # 分辨率选择按钮组（使用2x2网格布局）
    res_btn_frame = ttkb.Frame(resolution_card)
    res_btn_frame.pack(fill=X, pady=(0, 6))

    resolutions = [("1080P", "1080P"), ("2K", "2K"), ("4K", "4K"), ("自定义", "自定义")]

    # 自定义分辨率输入框容器
    custom_frame = ttkb.Frame(resolution_card)

    custom_width_label = ttkb.Label(custom_frame, text="宽:", font=("Segoe UI", 9))
    custom_width_label.pack(side=LEFT, padx=(0, 3))

    custom_width_entry = ttkb.Entry(custom_frame, textvariable=custom_width_var, width=6, font=("Segoe UI", 9))
    custom_width_entry.pack(side=LEFT, padx=(0, 10))

    custom_height_label = ttkb.Label(custom_frame, text="高:", font=("Segoe UI", 9))
    custom_height_label.pack(side=LEFT, padx=(0, 3))

    custom_height_entry = ttkb.Entry(custom_frame, textvariable=custom_height_var, width=6, font=("Segoe UI", 9))
    custom_height_entry.pack(side=LEFT)

    # 当前分辨率信息标签
    resolution_info_var = ttkb.StringVar(value=f"当前: {TARGET_WIDTH}×{TARGET_HEIGHT}")
    info_label = ttkb.Label(
        resolution_card,
        textvariable=resolution_info_var,
        font=("Segoe UI", 8),
        bootstyle="info"
    )

    def update_resolution_info():
        res = resolution_var.get()
        if res == "1080P":
            resolution_info_var.set("当前: 1920×1080")
        elif res == "2K":
            resolution_info_var.set("当前: 2560×1440")
        elif res == "4K":
            resolution_info_var.set("当前: 3840×2160")
        else:
            resolution_info_var.set(f"当前: {custom_width_var.get()}×{custom_height_var.get()}")

    def on_resolution_change():
        """当分辨率选择改变时，更新自定义输入框状态"""
        # 先隐藏所有动态元素
        custom_frame.pack_forget()
        info_label.pack_forget()

        if resolution_var.get() == "自定义":
            # 显示自定义输入框
            custom_frame.pack(fill=X, pady=(5, 0))
        else:
            # 根据选择更新显示值
            if resolution_var.get() == "1080P":
                custom_width_var.set("1920")
                custom_height_var.set("1080")
            elif resolution_var.get() == "2K":
                custom_width_var.set("2560")
                custom_height_var.set("1440")
            elif resolution_var.get() == "4K":
                custom_width_var.set("3840")
                custom_height_var.set("2160")

        # 始终显示分辨率信息标签
        info_label.pack(pady=(8, 0))
        update_resolution_info()


    # 创建分辨率选择按钮（2x2网格布局）
    res_btn_frame.columnconfigure(0, weight=1)
    res_btn_frame.columnconfigure(1, weight=1)
    for i, (text, value) in enumerate(resolutions):
        rb = ttkb.Radiobutton(
            res_btn_frame,
            text=text,
            variable=resolution_var,
            value=value,
            bootstyle="info-outline-toolbutton",
            width=9,
            command=on_resolution_change
        )
        rb.grid(row=i//2, column=i%2, padx=2, pady=2, sticky="ew")

    # 初始化显示状态
    if resolution_choice == "自定义":
        custom_frame.pack(fill=X, pady=(5, 0))
    info_label.pack(pady=(8, 0))

    # ==================== 右侧面板（钓鱼记录区域） ====================
    right_panel = ttkb.Frame(main_frame)
    right_panel.grid(row=0, column=1, sticky="nsew")

    # ==================== 钓鱼记录卡片 ====================
    fish_record_card = ttkb.Labelframe(
        right_panel,
        text=" 🐟 钓鱼记录 ",
        padding=12,
        bootstyle="primary"
    )
    fish_record_card.pack(fill=BOTH, expand=YES)

    # 切换按钮（本次/总览）
    record_view_frame = ttkb.Frame(fish_record_card)
    record_view_frame.pack(fill=X, pady=(0, 10))

    view_mode = ttkb.StringVar(value="current")

    current_btn = ttkb.Radiobutton(
        record_view_frame,
        text="本次钓鱼",
        variable=view_mode,
        value="current",
        bootstyle="info-outline-toolbutton",
        command=lambda: update_fish_display()
    )
    current_btn.pack(side=LEFT, padx=5)

    all_btn = ttkb.Radiobutton(
        record_view_frame,
        text="历史总览",
        variable=view_mode,
        value="all",
        bootstyle="info-outline-toolbutton",
        command=lambda: update_fish_display()
    )
    all_btn.pack(side=LEFT, padx=5)

    # 刷新按钮
    refresh_btn = ttkb.Button(
        record_view_frame,
        text="🔄",
        command=lambda: update_fish_display(),
        bootstyle="info-outline",
        width=3
    )
    refresh_btn.pack(side=RIGHT, padx=5)

    # 搜索和筛选框
    search_frame = ttkb.Frame(fish_record_card)
    search_frame.pack(fill=X, pady=(0, 10))

    search_var = ttkb.StringVar()
    search_entry = ttkb.Entry(search_frame, textvariable=search_var, width=15, font=("Segoe UI", 9))
    search_entry.pack(side=LEFT, padx=(0, 5))
    search_entry.insert(0, "搜索鱼名...")

    def on_search_focus_in(event):
        if search_entry.get() == "搜索鱼名...":
            search_entry.delete(0, "end")

    def on_search_focus_out(event):
        if not search_entry.get():
            search_entry.insert(0, "搜索鱼名...")

    search_entry.bind("<FocusIn>", on_search_focus_in)
    search_entry.bind("<FocusOut>", on_search_focus_out)
    search_entry.bind("<Return>", lambda e: update_fish_display())

    search_btn = ttkb.Button(
        search_frame,
        text="🔍",
        command=lambda: update_fish_display(),
        bootstyle="info-outline",
        width=3
    )
    search_btn.pack(side=LEFT, padx=(0, 10))

    # 品质筛选
    quality_var = ttkb.StringVar(value="全部")
    quality_label = ttkb.Label(search_frame, text="品质:", font=("Segoe UI", 9))
    quality_label.pack(side=LEFT)
    quality_combo = ttkb.Combobox(
        search_frame,
        textvariable=quality_var,
        values=["全部"] + QUALITY_LEVELS,
        width=8,
        state="readonly",
        font=("Segoe UI", 9)
    )
    quality_combo.pack(side=LEFT, padx=5)
    quality_combo.bind("<<ComboboxSelected>>", lambda e: update_fish_display())

    # 记录列表容器（包含Treeview和滚动条）
    tree_container = ttkb.Frame(fish_record_card)
    tree_container.pack(fill=BOTH, expand=YES, pady=(0, 8))

    # 记录列表（使用Treeview）
    columns = ("时间", "名称", "品质", "重量")
    fish_tree = ttkb.Treeview(
        tree_container,
        columns=columns,
        show="headings",
        height=15,
        bootstyle="info"
    )

    # 添加垂直滚动条（放在Treeview右侧）
    tree_scroll = ttkb.Scrollbar(tree_container, orient="vertical", command=fish_tree.yview, bootstyle="rounded")
    fish_tree.configure(yscrollcommand=tree_scroll.set)

    # 设置列标题和宽度
    fish_tree.heading("时间", text="时间")
    fish_tree.heading("名称", text="鱼名")
    fish_tree.heading("品质", text="品质")
    fish_tree.heading("重量", text="重量")

    fish_tree.column("时间", width=145, anchor="center")  # 增加宽度以显示完整日期时间(年月日时分秒)
    fish_tree.column("名称", width=110, anchor="w")
    fish_tree.column("品质", width=50, anchor="center")
    fish_tree.column("重量", width=65, anchor="center")

    # 布局Treeview和滚动条
    fish_tree.pack(side=LEFT, fill=BOTH, expand=YES)
    tree_scroll.pack(side=RIGHT, fill=Y)

    # 配置品质颜色标签（背景色和前景色）
    # 标准-白色背景黑色字体, 非凡-绿色, 稀有-蓝色, 史诗-紫色, 传说-橙色
    fish_tree.tag_configure("标准", background="#FFFFFF", foreground="#000000")
    fish_tree.tag_configure("非凡", background="#2ECC71", foreground="#000000")
    fish_tree.tag_configure("稀有", background="#3498DB", foreground="#FFFFFF")
    fish_tree.tag_configure("史诗", background="#9B59B6", foreground="#FFFFFF")
    fish_tree.tag_configure("传说", background="#E67E22", foreground="#000000")

    # 绑定鼠标滚轮到Treeview
    def on_tree_mousewheel(event):
        fish_tree.yview_scroll(int(-1*(event.delta/120)), "units")

    fish_tree.bind("<MouseWheel>", on_tree_mousewheel)

    # 统计信息
    stats_var = ttkb.StringVar(value="共 0 条记录")
    stats_label = ttkb.Label(
        fish_record_card,
        textvariable=stats_var,
        font=("Segoe UI", 9),
        bootstyle="info"
    )
    stats_label.pack()

    def update_fish_display():
        """更新钓鱼记录显示"""
        # 清空列表
        for item in fish_tree.get_children():
            fish_tree.delete(item)

        # 获取搜索关键词
        keyword = search_var.get()
        if keyword == "搜索鱼名...":
            keyword = ""

        # 根据视图模式选择数据源
        use_session = (view_mode.get() == "current")
        quality_filter = quality_var.get()

        # 获取筛选后的记录
        filtered = search_fish_records(keyword, quality_filter, use_session)

        # 显示记录（倒序，最新的在前面）
        for record in reversed(filtered[-100:]):  # 最多显示100条
            # 直接使用完整时间戳（格式：YYYY-MM-DD HH:MM:SS）
            time_display = record.timestamp if record.timestamp else "未知时间"

            # 根据品质确定标签（用于显示颜色）
            quality_tag = record.quality if record.quality in ["标准", "非凡", "稀有", "史诗", "传说"] else "标准"

            fish_tree.insert("", "end", values=(
                time_display,
                record.name,
                record.quality,
                record.weight
            ), tags=(quality_tag,))

        # 更新统计
        total = len(filtered)
        if use_session:
            stats_var.set(f"本次: {total} 条")
        else:
            stats_var.set(f"总计: {total} 条")

    # 设置GUI更新回调
    global gui_fish_update_callback
    def safe_update():
        try:
            root.after(0, update_fish_display)
        except:
            pass
    gui_fish_update_callback = safe_update

    # 初始加载
    update_fish_display()


    # ==================== 操作按钮区域（左侧面板底部） ====================
    btn_frame = ttkb.Frame(left_panel)
    btn_frame.pack(fill=X, pady=(8, 0))

    def update_and_refresh():
        """更新参数并刷新显示"""
        update_parameters(
            t_var, leftclickdown_var, leftclickup_var, times_var,
            paogantime_var, jiashi_var_option, resolution_var,
            custom_width_var, custom_height_var
        )
        resolution_info_var.set(f"当前: {TARGET_WIDTH}×{TARGET_HEIGHT}")
        # 显示保存成功提示
        status_label.config(text="✅ 参数已保存", bootstyle="success")
        root.after(2000, lambda: status_label.config(text="按 F2 启动/暂停", bootstyle="light"))

    update_button = ttkb.Button(
        btn_frame,
        text="💾 保存设置",
        command=update_and_refresh,
        bootstyle="success",
        width=16
    )
    update_button.pack(pady=3, fill=X)

    # ==================== 状态栏（左侧面板底部） ====================
    status_frame = ttkb.Frame(left_panel)
    status_frame.pack(fill=X, pady=(8, 0))

    separator = ttkb.Separator(status_frame, bootstyle="secondary")
    separator.pack(fill=X, pady=(0, 5))

    status_label = ttkb.Label(
        status_frame,
        text="按 F2 启动/暂停",
        font=("Segoe UI", 9),
        bootstyle="light"
    )
    status_label.pack()

    version_label = ttkb.Label(
        status_frame,
        text="v2.0 | PartyFish",
        font=("Segoe UI", 7),
        bootstyle="light"
    )
    version_label.pack(pady=(2, 0))

    # ==================== 开发者信息 ====================
    def open_github(event=None):
        """打开GitHub主页"""
        webbrowser.open("https://github.com/FADEDTUMI")

    dev_frame = ttkb.Frame(status_frame)
    dev_frame.pack(pady=(3, 0))

    dev_label = ttkb.Label(
        dev_frame,
        text="by ",
        font=("Segoe UI", 7),
        bootstyle="light"
    )
    dev_label.pack(side=LEFT)

    # 可点击的开发者链接
    dev_link = ttkb.Label(
        dev_frame,
        text="FadedTUMI",
        font=("Segoe UI", 7, "underline"),
        bootstyle="info",
        cursor="hand2"
    )
    dev_link.pack(side=LEFT)
    dev_link.bind("<Button-1>", open_github)

    # 鼠标悬停效果
    def on_enter(event):
        dev_link.configure(bootstyle="primary")

    def on_leave(event):
        dev_link.configure(bootstyle="info")

    dev_link.bind("<Enter>", on_enter)
    dev_link.bind("<Leave>", on_leave)

    # 运行 GUI
    root.mainloop()
# =========================
# =========================
# 常数 t 定义：定义时间间隔为 0.3 秒（可以根据需要调整）
t = 0.3  # 将时间间隔缩短，提高响应速度
# 常数 leftclickup 和 leftclickdown，用于调整按下去和抬起的时间
leftclickdown = 2.5  # 鼠标左键按下去的时间（秒）
leftclickup = 2  # 鼠标左键抬起的时间（秒）
times = 15 #最大钓鱼拉杆次数
paogantime = 0.5
# =========================
# 分辨率设置（修改此处适配不同分辨率）
# =========================
# 基准分辨率：2560x1440 (2K)
BASE_WIDTH = 2560
BASE_HEIGHT = 1440
# 目标分辨率（修改为您的屏幕分辨率）
TARGET_WIDTH = 2560
TARGET_HEIGHT = 1440

# 分辨率选择（用于GUI和保存）
resolution_choice = "2K"

# 计算缩放比例
SCALE_X = TARGET_WIDTH / BASE_WIDTH
SCALE_Y = TARGET_HEIGHT / BASE_HEIGHT

def scale_coords(x, y, w, h):
    """根据分辨率缩放坐标"""
    return (int(x * SCALE_X), int(y * SCALE_Y), int(w * SCALE_X), int(h * SCALE_Y))

def scale_point(x, y):
    """根据分辨率缩放单点坐标"""
    return (int(x * SCALE_X), int(y * SCALE_Y))

def update_region_coords():
    """根据当前缩放比例更新所有区域坐标"""
    global region3_coords, region4_coords, region5_coords, region6_coords
    region3_coords = scale_coords(1172, 165, 34, 34)    #上鱼星星
    region4_coords = scale_coords(1100, 1329, 10, 19)   #F1位置
    region5_coords = scale_coords(1212, 1329, 10, 19)   #F2位置
    region6_coords = scale_coords(1146, 1316, 17, 21)   #上鱼右键

# =========================
# 参数设置
# =========================
template_folder_path = os.path.join('.', 'resources')

# =========================
# 钓鱼记录系统
# =========================
FISH_RECORD_FILE = "./fish_records.txt"

# 鱼信息识别区域（2K分辨率基准值）
FISH_INFO_REGION_BASE = (915, 75, 1640, 225)  # 左上角x, y, 右下角x, y

# 品质等级定义
QUALITY_LEVELS = ["标准", "非凡", "稀有", "史诗", "传说"]
QUALITY_COLORS = {
    "标准": "⚪",
    "非凡": "🟢",
    "稀有": "🔵",
    "史诗": "🟣",
    "传说": "🟡"
}

# 当前会话数据
current_session_id = None
current_session_fish = []  # 当前会话钓到的鱼
all_fish_records = []      # 所有钓鱼记录（从文件加载）
fish_record_lock = threading.Lock()  # 钓鱼记录锁

# GUI更新回调（将在create_gui中设置）
gui_fish_update_callback = None

class FishRecord:
    """单条鱼的记录"""
    def __init__(self, name, quality, weight):
        self.name = name if name else "未知"
        self.quality = quality if quality in QUALITY_LEVELS else "标准"
        self.weight = weight if weight else "0"
        self.timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.session_id = current_session_id

    def to_dict(self):
        return {
            "name": self.name,
            "quality": self.quality,
            "weight": self.weight,
            "timestamp": self.timestamp,
            "session_id": self.session_id
        }

    def to_line(self):
        """转换为文件存储格式"""
        return f"{self.session_id}|{self.timestamp}|{self.name}|{self.quality}|{self.weight}\n"

    @staticmethod
    def from_line(line):
        """从文件行解析"""
        try:
            parts = line.strip().split("|")
            if len(parts) >= 5:
                record = FishRecord.__new__(FishRecord)
                record.session_id = parts[0]
                record.timestamp = parts[1]
                record.name = parts[2]
                record.quality = parts[3]
                record.weight = parts[4]
                return record
        except:
            pass
        return None

def save_fish_record(fish_record):
    """保存单条钓鱼记录到文件"""
    try:
        with open(FISH_RECORD_FILE, "a", encoding="utf-8") as f:
            f.write(fish_record.to_line())
    except Exception as e:
        print(f"❌ [错误] 保存钓鱼记录失败: {e}")

def load_all_fish_records():
    """加载所有历史钓鱼记录"""
    global all_fish_records
    all_fish_records = []
    try:
        if os.path.exists(FISH_RECORD_FILE):
            with open(FISH_RECORD_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        record = FishRecord.from_line(line)
                        if record:
                            all_fish_records.append(record)
            print(f"📊 [信息] 已加载 {len(all_fish_records)} 条历史钓鱼记录")
    except Exception as e:
        print(f"❌ [错误] 加载钓鱼记录失败: {e}")

def start_new_session():
    """开始新的钓鱼会话"""
    global current_session_id, current_session_fish
    current_session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    current_session_fish = []
    print(f"🎣 [会话] 新钓鱼会话开始: {current_session_id}")

def end_current_session():
    """结束当前钓鱼会话"""
    global current_session_id, current_session_fish
    if current_session_fish:
        print(f"📊 [会话] 本次钓鱼结束，共钓到 {len(current_session_fish)} 条鱼")
        # 统计品质
        quality_count = {}
        for fish in current_session_fish:
            quality_count[fish.quality] = quality_count.get(fish.quality, 0) + 1
        for q, count in quality_count.items():
            emoji = QUALITY_COLORS.get(q, "⚪")
            print(f"   {emoji} {q}: {count} 条")
    current_session_id = None

def capture_fish_info_region():
    """截取鱼信息区域的图像"""
    global scr
    if scr is None:
        return None

    # 根据分辨率缩放坐标
    x1, y1, x2, y2 = FISH_INFO_REGION_BASE
    region = (
        int(x1 * SCALE_X),
        int(y1 * SCALE_Y),
        int(x2 * SCALE_X),
        int(y2 * SCALE_Y)
    )

    try:
        frame = scr.grab(region)
        if frame is None:
            return None
        img = np.array(frame)
        # 转换为RGB格式（OCR需要）
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
        return img_rgb
    except Exception as e:
        print(f"❌ [错误] 截取鱼信息区域失败: {e}")
        return None

def recognize_fish_info_ocr(img):
    """使用OCR识别鱼的信息"""
    if not OCR_AVAILABLE or ocr_engine is None:
        return None, None, None

    if img is None:
        return None, None, None

    try:
        # 执行OCR识别
        result, elapse = ocr_engine(img)

        if result is None or len(result) == 0:
            return None, None, None

        # 合并所有识别到的文本
        full_text = ""
        for line in result:
            if len(line) >= 2:
                full_text += line[1] + " "

        full_text = full_text.strip()

        if not full_text:
            return None, None, None

        # 解析鱼的信息
        fish_name = None
        fish_quality = None
        fish_weight = None

        # 识别品质
        for quality in QUALITY_LEVELS:
            if quality in full_text:
                fish_quality = quality
                break

        # 识别重量（匹配数字+kg或g的模式）
        weight_pattern = r'(\d+\.?\d*)\s*(kg|g|千克|克)?'
        weight_matches = re.findall(weight_pattern, full_text, re.IGNORECASE)
        if weight_matches:
            # 取最后一个匹配的数字作为重量
            for match in weight_matches:
                if match[0]:
                    fish_weight = match[0]
                    unit = match[1].lower() if match[1] else "kg"
                    if unit in ['g', '克']:
                        fish_weight = str(float(fish_weight) / 1000)
                    fish_weight = f"{float(fish_weight):.2f}kg"

        # 识别鱼名 - 优先匹配"你钓到了XXX"或"首次捕获XXX"格式
        # 使用正则表达式提取鱼名
        fish_name_patterns = [
            r'你钓到了\s*[「【\[]?\s*(.+?)\s*[」】\]]?\s*(?:标准|非凡|稀有|史诗|传说|$)',  # 你钓到了XXX
            r'首次捕获\s*[「【\[]?\s*(.+?)\s*[」】\]]?\s*(?:标准|非凡|稀有|史诗|传说|$)',  # 首次捕获XXX
            r'钓到了\s*[「【\[]?\s*(.+?)\s*[」】\]]?\s*(?:标准|非凡|稀有|史诗|传说|$)',   # 钓到了XXX
            r'捕获\s*[「【\[]?\s*(.+?)\s*[」】\]]?\s*(?:标准|非凡|稀有|史诗|传说|$)',     # 捕获XXX
        ]

        for pattern in fish_name_patterns:
            match = re.search(pattern, full_text)
            if match:
                extracted_name = match.group(1).strip()
                # 清理鱼名中的数字、单位和特殊字符
                extracted_name = re.sub(r'\d+\.?\d*\s*(kg|g|千克|克)?', '', extracted_name, flags=re.IGNORECASE)
                extracted_name = re.sub(r'[^\u4e00-\u9fa5a-zA-Z\s]', '', extracted_name)
                extracted_name = extracted_name.strip()
                if extracted_name and len(extracted_name) >= 2:
                    fish_name = extracted_name
                    break

        # 如果上述模式都没匹配到，尝试备用方案
        if not fish_name:
            name_text = full_text
            # 移除常见前缀
            prefixes_to_remove = ['你钓到了', '首次捕获', '钓到了', '捕获', '你钓到', '钓到']
            for prefix in prefixes_to_remove:
                name_text = name_text.replace(prefix, ' ')
            # 移除品质词
            if fish_quality:
                name_text = name_text.replace(fish_quality, ' ')
            # 移除数字和单位
            name_text = re.sub(r'\d+\.?\d*\s*(kg|g|千克|克)?', '', name_text, flags=re.IGNORECASE)
            # 清理特殊字符，保留中文和英文
            name_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z]', ' ', name_text)
            # 取最长的连续中文词作为鱼名
            chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,}', name_text)
            if chinese_words:
                # 选择最长的词作为鱼名
                fish_name = max(chinese_words, key=len)

        return fish_name, fish_quality, fish_weight

    except Exception as e:
        print(f"❌ [错误] OCR识别失败: {e}")
        return None, None, None

def record_caught_fish():
    """识别并记录钓到的鱼"""
    global current_session_fish, all_fish_records

    if not OCR_AVAILABLE:
        return None

    # 等待鱼信息显示
    time.sleep(0.3)

    # 截取鱼信息区域
    img = capture_fish_info_region()
    if img is None:
        return None

    # OCR识别
    fish_name, fish_quality, fish_weight = recognize_fish_info_ocr(img)

    if fish_name is None and fish_quality is None and fish_weight is None:
        return None

    # 创建记录
    with fish_record_lock:
        fish = FishRecord(fish_name, fish_quality, fish_weight)
        current_session_fish.append(fish)
        all_fish_records.append(fish)
        save_fish_record(fish)

    # 终端输出
    quality_emoji = QUALITY_COLORS.get(fish.quality, "⚪")
    print(f"🐟 [钓到] {quality_emoji} {fish.name} | 品质: {fish.quality} | 重量: {fish.weight}")

    # 通知GUI更新
    if gui_fish_update_callback:
        try:
            gui_fish_update_callback()
        except:
            pass

    return fish

def get_session_fish_list():
    """获取当前会话的钓鱼记录"""
    with fish_record_lock:
        return list(current_session_fish)

def get_all_fish_list():
    """获取所有钓鱼记录"""
    with fish_record_lock:
        return list(all_fish_records)

def search_fish_records(keyword="", quality_filter="全部", use_session=True):
    """搜索钓鱼记录"""
    with fish_record_lock:
        records = current_session_fish if use_session else all_fish_records

        filtered = []
        for record in records:
            # 品质筛选
            if quality_filter != "全部" and record.quality != quality_filter:
                continue
            # 关键词搜索
            if keyword and keyword.lower() not in record.name.lower():
                continue
            filtered.append(record)

        return filtered
# 定义区域的坐标 (x, y, w, h) - 基于2K分辨率的基准值
# 使用 scale_coords 函数自动缩放
region3_coords = scale_coords(1172, 165, 34, 34)    #上鱼星星
region4_coords = scale_coords(1100, 1329, 10, 19)   #F1位置
region5_coords = scale_coords(1212, 1329, 10, 19)   #F2位置
region6_coords = scale_coords(1146, 1316, 17, 21)   #上鱼右键

# 鱼饵数量区域（基准值）
BAIT_REGION_BASE = (2318, 1296, 2348, 1318)
# 加时界面检测区域（基准值）
JIASHI_REGION_BASE = (1245, 675, 26, 27)
# 点击按钮位置（基准值）
BTN_NO_JIASHI_BASE = (1182, 776)   # 不加时按钮
BTN_YES_JIASHI_BASE = (1398, 776)  # 加时按钮
previous_result = None  # 上次识别的结果
current_result = 0  # 当前识别的数字
# 模板加载一次
templates = None
star_template = None
f1 = None
f2 = None
shangyule = None
jiashi = None
jiashi_var = 0
run_event = threading.Event()
begin_event = threading.Event()
user32 = ctypes.WinDLL("user32")
pyautogui.PAUSE = 0           # 禁用 PyAutoGUI 默认的每个操作后的暂停（0.1秒）
pyautogui.FAILSAFE = False    # 禁用 PyAutoGUI 的“鼠标移动到屏幕左上角时触发异常”功能
listener = None #监听
a = 0
region1 = 0
region2 = 0
result_val_is = None
scr = None
# =========================
# 模板加载
# =========================
# 加载模板（0.png到9.png）
def load_templates():
    global templates, template_folder_path
    if templates is None:
        templates = []
        for i in range(10):
            template_path = os.path.join(template_folder_path, f"{i}_grayscale.png")
            img = Image.open(template_path)
            template = np.array(img)
            templates.append(template)
    return templates

# 加载模板
def load_star_template():
    global star_template, template_folder_path
    if star_template is None:
        star_template_path = os.path.join(template_folder_path, "star_grayscale.png")
        img = Image.open(star_template_path)
        star_template = np.array(img)
    return star_template

def load_f1():
    global f1
    if f1 is None:
        f1_path = os.path.join(template_folder_path, "F1_grayscale.png")
        img = Image.open(f1_path)
        f1 = np.array(img)
    return f1

def load_f2():
    global f2
    if f2 is None:
        f2_path = os.path.join(template_folder_path, "F2_grayscale.png")
        img = Image.open(f2_path)
        f2 = np.array(img)
    return f2
def load_shangyule():
    global shangyule
    shangyule_path = os.path.join(template_folder_path, "shangyu_grayscale.png")
    img = Image.open(shangyule_path)
    shangyule = np.array(img)
    return shangyule
def load_jiashi():
    global jiashi
    jiashi_path = os.path.join(template_folder_path, "chang_grayscale.png")
    img = Image.open(jiashi_path)
    jiashi = np.array(img)
    return jiashi
# =========================
# 鼠标操作（使用 win32api 实现）
# =========================
mouse_lock = threading.Lock()
mouse_is_down = False
def pressandreleasemousebutton():
    user32.mouse_event(0x02, 0, 0, 0, 0)
    time.sleep(leftclickdown)
    user32.mouse_event(0x04, 0, 0, 0, 0)
    time.sleep(leftclickup)

def ensure_mouse_down():
    global mouse_is_down
    with mouse_lock:
        if not mouse_is_down:
            user32.mouse_event(0x02, 0, 0, 0, 0)  # 左键按下
            mouse_is_down = True

def ensure_mouse_up():
    global mouse_is_down
    with mouse_lock:
        if mouse_is_down:
            user32.mouse_event(0x04, 0, 0, 0, 0)  # 左键释放
            mouse_is_down = False
# =========================
# 比较数字大小
# =========================
def compare_results():
    global current_result, previous_result
    if current_result is None or previous_result is None:
        return 0  # 无法比较，返回 0 作为标识
    if current_result > previous_result:
        return 1  # 当前结果较大
    elif current_result < previous_result:
        return -1  # 上次结果较大
    else:
        return 0  # 当前结果与上次相同
# =========================
# 截取屏幕区域
# =========================
def bait_math_val():
    global  region1, region2, result_val_is, scr
    # 使用缩放后的坐标
    x1, y1, x2, y2 = BAIT_REGION_BASE
    region = (int(x1 * SCALE_X), int(y1 * SCALE_Y), int(x2 * SCALE_X), int(y2 * SCALE_Y))
    math_frame = scr.grab(region)
    # 将 mss 截取的图像转换为 NumPy 数组 (height, width, 4)，即 RGBA 图像
    if math_frame is None:
        result_val_is = None
        return None
    else:
        img = np.array(math_frame)  # screenshot 是 ScreenShot 类型，转换为 NumPy 数组
        gray_img = cv2.cvtColor(img, cv2.COLOR_RGBA2GRAY)
        # 截取并处理区域1
        region1 = gray_img [0:22, 0:15]  # 获取区域1的图像
        best_match1 = match_digit_template(region1)
        # 截取并处理区域2
        region2 = gray_img [0:22, 15:30]  # 获取区域2的图像
        best_match2 = match_digit_template(region2)
        region3 = gray_img[0:22, 7:22]
        best_match3 = match_digit_template(region3)
        if best_match1 and best_match2:
            # 从best_match中提取数字索引（i），并拼接成整数
            best_match1_val = best_match1[0]  # 提取区域1的数字索引
            best_match2_val = best_match2[0]  # 提取区域2的数字索引
            # 拼接两个匹配的数字，转换为整数
            result_val_is = int(f"{best_match1_val}{best_match2_val}")
        elif best_match3:
            result_val_is = int(f'{best_match3[0]}')
        else:
            result_val_is = None
        return result_val_is

def match_digit_template(image):
    best_match = None  # 最佳匹配信息
    best_val = 0  # 存储最佳匹配度
    for i, template in enumerate(templates):
        res = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        if max_val> 0.8 and max_val > best_val:  # 找到最佳匹配
            best_val = max_val
            best_match = (i, max_loc)  # 记录最佳匹配的数字和位置
    return best_match

def capture_region(x, y, w, h):
    region = (x, y,x+w,y+h)
    frame = scr.grab(region)
    if frame is None:
        return None
    img = np.array(frame)  # screenshot 是 ScreenShot 类型，转换为 NumPy 数组
    gray_img = cv2.cvtColor(img, cv2.COLOR_RGBA2GRAY)
    return gray_img

#识别钓上鱼
def fished():
    global region3_coords, star_template
    # 获取区域坐标并捕获灰度图
    region_gray = capture_region(*region3_coords)  # 直接传递解包后的参数
    if region_gray is None:
        return None
    # 执行模板匹配并检查最大匹配度是否大于 0.8
    return cv2.minMaxLoc(cv2.matchTemplate(region_gray, star_template, cv2.TM_CCOEFF_NORMED))[1] > 0.8
def f1_mached():
    global region4_coords, f1
    region_gray = capture_region(*region4_coords)
    if region_gray is None:
        return None
    return cv2.minMaxLoc(cv2.matchTemplate(region_gray, f1, cv2.TM_CCOEFF_NORMED))[1] > 0.8
def f2_mached():
    global region5_coords, f2
    region_gray = capture_region(*region5_coords)
    if region_gray is None:
        return None
    return cv2.minMaxLoc(cv2.matchTemplate(region_gray, f2, cv2.TM_CCOEFF_NORMED))[1] > 0.8
def shangyu_mached():
    global region6_coords, shangyule
    region_gray = capture_region(*region6_coords)
    if region_gray is None:
        return None
    return cv2.minMaxLoc(cv2.matchTemplate(region_gray, shangyule, cv2.TM_CCOEFF_NORMED))[1] > 0.8
def fangzhu_jiashi():
    x, y, w, h = JIASHI_REGION_BASE
    region_gray = capture_region(int(x * SCALE_X), int(y * SCALE_Y), int(w * SCALE_X), int(h * SCALE_Y))
    if region_gray is None:
        return None
    return cv2.minMaxLoc(cv2.matchTemplate(region_gray, jiashi, cv2.TM_CCOEFF_NORMED))[1] > 0.8
# =========================
# 程序主循环与热键监听
# =========================
def toggle_run():
    global a, previous_result, scr
    if run_event.is_set():
        run_event.clear()  # 暂停
        a = 0
        previous_result = None
        ensure_mouse_up()  # 确保鼠标没有按下
        end_current_session()  # 结束钓鱼会话
        print("⏸️  [状态] 脚本已暂停")
    else:
        start_new_session()  # 开始新的钓鱼会话
        if previous_result is None:
            temp_scr = None
            try:
                temp_scr = mss.mss()
                scr = temp_scr  # 临时赋值供bait_math_val使用
                bait_result = bait_math_val()
                if bait_result or bait_result == 0:
                    previous_result = result_val_is
                    run_event.set()  # 恢复运行
                    print("▶️  [状态] 脚本开始运行")
                else:
                    time.sleep(0.1)
                    print("⚠️  [警告] 未识别到鱼饵，请确保游戏界面正确")
            except Exception as e:
                print(f"❌ [错误] 初始化失败: {e}")
            finally:
                if temp_scr is not None:
                    try:
                        temp_scr.close()
                    except:
                        pass
                scr = None
        else:
            run_event.set()
            print("▶️  [状态] 脚本继续运行")

def on_press(key):
    time.sleep(0.02)
    if key == keyboard.Key.f2:
        toggle_run()  # 暂停或恢复程序
        return
def start_hotkey_listener():
    global listener
    if listener is None or not listener.running:
        listener = keyboard.Listener(on_press=on_press)
        listener.daemon = True
        listener.start()
# =========================
# 主函数
# =========================
# 主函数：定时识别并比较数字
def main():
    global templates, template_folder_path, current_result, previous_result, times, a, region1, region2, result_val_is, scr, jiashi_var

    while not begin_event.is_set():
        if run_event.is_set():
            scr = None
            try:
                scr = mss.mss()

                # 检测F1/F2抛竿
                if f1_mached():
                    user32.mouse_event(0x02, 0, 0, 0, 0)
                    time.sleep(paogantime)
                    user32.mouse_event(0x04, 0, 0, 0, 0)
                    time.sleep(0.15)
                elif f2_mached():
                    user32.mouse_event(0x02, 0, 0, 0, 0)
                    time.sleep(paogantime)
                    user32.mouse_event(0x04, 0, 0, 0, 0)
                    time.sleep(0.15)
                elif shangyu_mached():
                    user32.mouse_event(0x02, 0, 0, 0, 0)
                    time.sleep(0.1)
                    user32.mouse_event(0x04, 0, 0, 0, 0)

                time.sleep(0.05)

                # 处理加时选择（使用锁保护读取jiashi_var）
                with param_lock:
                    current_jiashi = jiashi_var

                if current_jiashi == 0:
                    if fangzhu_jiashi():
                        btn_x, btn_y = scale_point(*BTN_NO_JIASHI_BASE)
                        user32.SetCursorPos(btn_x, btn_y)
                        time.sleep(0.05)
                        user32.mouse_event(0x02, 0, 0, 0, 0)
                        time.sleep(0.1)
                        user32.mouse_event(0x04, 0, 0, 0, 0)
                        time.sleep(0.05)
                        if bait_math_val():
                            previous_result = result_val_is
                elif current_jiashi == 1:
                    if fangzhu_jiashi():
                        btn_x, btn_y = scale_point(*BTN_YES_JIASHI_BASE)
                        user32.SetCursorPos(btn_x, btn_y)
                        time.sleep(0.05)
                        user32.mouse_event(0x02, 0, 0, 0, 0)
                        time.sleep(0.1)
                        user32.mouse_event(0x04, 0, 0, 0, 0)
                        time.sleep(0.05)
                        if bait_math_val():
                            previous_result = result_val_is

                time.sleep(0.05)

                # 获取当前结果
                if bait_math_val():
                    current_result = result_val_is
                else:
                    current_result = previous_result  # 将当前数字设为上次的数字
                    time.sleep(0.1)
                    continue  # 会在finally中关闭scr

                # 比较并执行操作
                comparison_result = compare_results()
                time.sleep(0.01)

                if comparison_result == -1:  # 当前结果小于上次结果
                    previous_result = current_result  # 更新上次识别的结果
                    while not fished() and run_event.is_set():
                        # 使用锁保护读取times
                        with param_lock:
                            current_times = times
                        if a <= current_times:
                            a += 1
                            pressandreleasemousebutton()  # 执行点击循环直到识别到 star.png
                        else:
                            a = 0
                            print("🎣 [提示] 达到最大拉杆次数，本轮结束")
                            break
                    ensure_mouse_up()
                    a = 0

                    # 钓到鱼后，识别并记录鱼的信息
                    if OCR_AVAILABLE:
                        try:
                            record_caught_fish()
                        except Exception as e:
                            print(f"⚠️  [警告] 记录鱼信息失败: {e}")

                elif comparison_result == 1:
                    previous_result = current_result
                    # continue会在finally中关闭scr

            except Exception as e:
                print(f"❌ [错误] 主循环异常: {e}")
            finally:
                # 确保mss资源被正确释放
                if scr is not None:
                    try:
                        scr.close()
                    except:
                        pass
                    scr = None

        time.sleep(0.1)

# =========================
# 程序入口
# =========================
if __name__ == "__main__":
    print()
    print("╔" + "═" * 50 + "╗")
    print("║" + " " * 50 + "║")
    print("║     🎣  PartyFish 自动钓鱼助手  v2.0            ║")
    print("║" + " " * 50 + "║")
    print("╠" + "═" * 50 + "╣")
    print(f"║  📺 当前分辨率: {TARGET_WIDTH} × {TARGET_HEIGHT}".ljust(51) + "║")
    print("║  ⌨️  快捷键: F2 启动/暂停脚本                     ║")
    print("║  🔧 开发者: FadedTUMI                            ║")
    print("╚" + "═" * 50 + "╝")
    print()

    # 加载参数和模板
    print("📦 [初始化] 正在加载配置...")
    load_parameters()

    # 加载历史钓鱼记录
    print("📊 [初始化] 正在加载钓鱼记录...")
    load_all_fish_records()

    print("🖼️  [初始化] 正在加载图像模板...")
    load_templates()
    load_star_template()
    load_f1()
    load_f2()
    load_shangyule()
    load_jiashi()
    print("✅ [初始化] 模板加载完成")

    # 启动热键监听
    print("🎮 [初始化] 正在启动热键监听...")
    start_hotkey_listener()
    print("✅ [初始化] 热键监听已启动")

    print()
    print("┌" + "─" * 48 + "┐")
    print("│  🚀 程序已就绪，按 F2 开始自动钓鱼！            │")
    print("└" + "─" * 48 + "┘")
    print()

    # 将main()放在后台线程运行（daemon=True确保主线程退出时自动结束）
    main_thread = threading.Thread(target=main, daemon=True)
    main_thread.start()

    # GUI必须在主线程运行（Tkinter要求）
    # 这样可以确保GUI正常工作且不会崩溃
    create_gui()
