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

import tkinter as tk  # 保留用于兼容性
from tkinter import ttk  # 保留用于兼容性
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import json  # 用于保存和加载参数
import mss

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
        print("参数已保存到文件")
    except Exception as e:
        print(f"保存参数失败: {e}")

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
        print("未找到参数文件，使用默认值")
    except Exception as e:
        print(f"加载参数失败: {e}")

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

            print(f"已更新 参数: 循环间隔 = {t}, 收线时间 = {leftclickdown}, 放线时间 = {leftclickup}, 最大拉杆次数 = {times}，抛竿时间 = {paogantime}, 加时 = {jiashi_var}")
            print(f"分辨率: {resolution_choice} ({TARGET_WIDTH}x{TARGET_HEIGHT}), 缩放比例: X={SCALE_X:.2f}, Y={SCALE_Y:.2f}")
            # 保存到文件
            save_parameters()
        except ValueError as e:
            print(f"请输入有效的数值！错误: {e}")
        except Exception as e:
            print(f"更新参数失败: {e}")

# =========================
# 创建 Tkinter 窗口（现代化UI设计）
# =========================
def create_gui():
    # 加载保存的参数
    load_parameters()

    # 创建现代化主题窗口
    root = ttkb.Window(themename="darkly")  # 使用深色主题
    root.title("🎣 PartyFish 自动钓鱼助手")
    root.geometry("420x680")  # 初始大小
    root.minsize(420, 600)    # 最小尺寸
    root.resizable(False, True)  # 允许垂直调整

    # 设置窗口图标（如果有的话）
    try:
        root.iconbitmap("icon.ico")
    except:
        pass

    # ==================== 主容器（使用Canvas实现滚动） ====================
    # 创建Canvas和滚动条
    canvas = ttkb.Canvas(root, highlightthickness=0)
    scrollbar = ttkb.Scrollbar(root, orient="vertical", command=canvas.yview, bootstyle="rounded")

    # 主内容Frame
    main_frame = ttkb.Frame(canvas, padding=20)

    # 配置滚动
    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
        # 自动调整窗口高度以适应内容（最大800像素）
        content_height = main_frame.winfo_reqheight() + 40
        max_height = 800
        new_height = min(content_height, max_height)
        if content_height <= max_height:
            scrollbar.pack_forget()
        else:
            scrollbar.pack(side=RIGHT, fill=Y)
        root.geometry(f"420x{new_height}")

    main_frame.bind("<Configure>", on_frame_configure)

    # 鼠标滚轮支持
    def on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    canvas.bind_all("<MouseWheel>", on_mousewheel)

    # 创建窗口内的frame
    canvas_frame = canvas.create_window((0, 0), window=main_frame, anchor="nw", width=400)
    canvas.configure(yscrollcommand=scrollbar.set)

    # 布局
    canvas.pack(side=LEFT, fill=BOTH, expand=YES)

    # ==================== 标题区域 ====================
    title_frame = ttkb.Frame(main_frame)
    title_frame.pack(fill=X, pady=(0, 15))

    title_label = ttkb.Label(
        title_frame,
        text="PartyFish",
        font=("Segoe UI", 24, "bold"),
        bootstyle="inverse-primary"
    )
    title_label.pack()

    subtitle_label = ttkb.Label(
        title_frame,
        text="自动钓鱼参数配置",
        font=("Segoe UI", 10),
        bootstyle="secondary"
    )
    subtitle_label.pack()

    # ==================== 钓鱼参数卡片 ====================
    params_card = ttkb.Labelframe(
        main_frame,
        text=" ⚙️ 钓鱼参数 ",
        padding=15,
        bootstyle="info"
    )
    params_card.pack(fill=X, pady=(0, 10))

    # 参数输入样式
    def create_param_row(parent, label_text, var, row, tooltip=""):
        label = ttkb.Label(parent, text=label_text, font=("Segoe UI", 10))
        label.grid(row=row, column=0, sticky=W, pady=5, padx=(0, 10))

        entry = ttkb.Entry(parent, textvariable=var, width=12, font=("Segoe UI", 10))
        entry.grid(row=row, column=1, sticky=E, pady=5)
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
        main_frame,
        text=" ⏱️ 加时选项 ",
        padding=15,
        bootstyle="warning"
    )
    jiashi_card.pack(fill=X, pady=(0, 10))

    jiashi_var_option = ttkb.IntVar(value=jiashi_var)

    jiashi_frame = ttkb.Frame(jiashi_card)
    jiashi_frame.pack(fill=X)

    jiashi_label = ttkb.Label(jiashi_frame, text="是否自动加时", font=("Segoe UI", 10))
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
        main_frame,
        text=" 🖥️ 分辨率设置 ",
        padding=15,
        bootstyle="success"
    )
    resolution_card.pack(fill=X, pady=(0, 10))

    resolution_var = ttkb.StringVar(value=resolution_choice)
    custom_width_var = ttkb.StringVar(value=str(TARGET_WIDTH))
    custom_height_var = ttkb.StringVar(value=str(TARGET_HEIGHT))

    # 分辨率选择按钮组
    res_btn_frame = ttkb.Frame(resolution_card)
    res_btn_frame.pack(fill=X, pady=(0, 10))

    resolutions = [("1080P", "1080P"), ("2K", "2K"), ("4K", "4K"), ("自定义", "自定义")]

    # 自定义分辨率输入框容器
    custom_frame = ttkb.Frame(resolution_card)

    custom_width_label = ttkb.Label(custom_frame, text="宽度:", font=("Segoe UI", 9))
    custom_width_label.pack(side=LEFT, padx=(0, 5))

    custom_width_entry = ttkb.Entry(custom_frame, textvariable=custom_width_var, width=8, font=("Segoe UI", 9))
    custom_width_entry.pack(side=LEFT, padx=(0, 15))

    custom_height_label = ttkb.Label(custom_frame, text="高度:", font=("Segoe UI", 9))
    custom_height_label.pack(side=LEFT, padx=(0, 5))

    custom_height_entry = ttkb.Entry(custom_frame, textvariable=custom_height_var, width=8, font=("Segoe UI", 9))
    custom_height_entry.pack(side=LEFT)

    # 当前分辨率信息标签（先创建）
    resolution_info_var = ttkb.StringVar(value=f"当前分辨率: {TARGET_WIDTH} × {TARGET_HEIGHT}")
    info_label = ttkb.Label(
        resolution_card,
        textvariable=resolution_info_var,
        font=("Segoe UI", 9),
        bootstyle="info"
    )

    def update_resolution_info():
        res = resolution_var.get()
        if res == "1080P":
            resolution_info_var.set("当前分辨率: 1920 × 1080")
        elif res == "2K":
            resolution_info_var.set("当前分辨率: 2560 × 1440")
        elif res == "4K":
            resolution_info_var.set("当前分辨率: 3840 × 2160")
        else:
            resolution_info_var.set(f"当前分辨率: {custom_width_var.get()} × {custom_height_var.get()}")

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
        info_label.pack(pady=(10, 0))
        update_resolution_info()

        # 更新布局后刷新窗口大小
        root.update_idletasks()

    # 创建分辨率选择按钮
    for i, (text, value) in enumerate(resolutions):
        rb = ttkb.Radiobutton(
            res_btn_frame,
            text=text,
            variable=resolution_var,
            value=value,
            bootstyle="info-outline-toolbutton",
            width=8,
            command=on_resolution_change
        )
        rb.pack(side=LEFT, padx=3, expand=YES)

    # 初始化显示状态
    if resolution_choice == "自定义":
        custom_frame.pack(fill=X, pady=(5, 0))
    info_label.pack(pady=(10, 0))


    # ==================== 操作按钮区域 ====================
    btn_frame = ttkb.Frame(main_frame)
    btn_frame.pack(fill=X, pady=(15, 0))

    def update_and_refresh():
        """更新参数并刷新显示"""
        update_parameters(
            t_var, leftclickdown_var, leftclickup_var, times_var,
            paogantime_var, jiashi_var_option, resolution_var,
            custom_width_var, custom_height_var
        )
        resolution_info_var.set(f"当前分辨率: {TARGET_WIDTH} × {TARGET_HEIGHT}")
        # 显示保存成功提示
        status_label.config(text="✅ 参数已保存", bootstyle="success")
        root.after(2000, lambda: status_label.config(text="按 F2 启动/暂停", bootstyle="secondary"))

    update_button = ttkb.Button(
        btn_frame,
        text="💾 保存设置",
        command=update_and_refresh,
        bootstyle="success",
        width=20
    )
    update_button.pack(pady=5)

    # ==================== 状态栏 ====================
    status_frame = ttkb.Frame(main_frame)
    status_frame.pack(fill=X, pady=(15, 0))

    separator = ttkb.Separator(status_frame, bootstyle="secondary")
    separator.pack(fill=X, pady=(0, 10))

    status_label = ttkb.Label(
        status_frame,
        text="按 F2 启动/暂停",
        font=("Segoe UI", 10),
        bootstyle="secondary"
    )
    status_label.pack()

    version_label = ttkb.Label(
        status_frame,
        text="v2.0 | PartyFish Auto Fishing",
        font=("Segoe UI", 8),
        bootstyle="secondary"
    )
    version_label.pack(pady=(5, 0))

    # ==================== 开发者信息 ====================
    def open_github(event=None):
        """打开GitHub主页"""
        webbrowser.open("https://github.com/FADEDTUMI")

    dev_frame = ttkb.Frame(status_frame)
    dev_frame.pack(pady=(8, 0))

    dev_label = ttkb.Label(
        dev_frame,
        text="by ",
        font=("Segoe UI", 8),
        bootstyle="secondary"
    )
    dev_label.pack(side=LEFT)

    # 可点击的开发者链接
    dev_link = ttkb.Label(
        dev_frame,
        text="FadedTUMI",
        font=("Segoe UI", 8, "underline"),
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
        print("[状态] 已暂停")
    else:
        if previous_result is None:
            temp_scr = None
            try:
                temp_scr = mss.mss()
                scr = temp_scr  # 临时赋值供bait_math_val使用
                bait_result = bait_math_val()
                if bait_result or bait_result == 0:
                    previous_result = result_val_is
                    run_event.set()  # 恢复运行
                    print("[状态] 开始运行")
                else:
                    time.sleep(0.1)
                    print('未识别到鱼饵')
            except Exception as e:
                print(f"[错误] 初始化失败: {e}")
            finally:
                if temp_scr is not None:
                    try:
                        temp_scr.close()
                    except:
                        pass
                scr = None
        else:
            run_event.set()
            print("[状态] 开始运行")

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
                            print('达到最大拉杆次数')
                            break
                    ensure_mouse_up()
                    a = 0
                elif comparison_result == 1:
                    previous_result = current_result
                    # continue会在finally中关闭scr

            except Exception as e:
                print(f"[错误] 主循环异常: {e}")
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
    print("=" * 50)
    print("🎣 PartyFish 自动钓鱼助手 v2.0")
    print("=" * 50)
    print(f"📺 当前分辨率: {TARGET_WIDTH}x{TARGET_HEIGHT}")
    print("⌨️  按 F2 启动/暂停脚本")
    print("=" * 50)

    # 加载参数和模板
    load_parameters()
    load_templates()
    load_star_template()
    load_f1()
    load_f2()
    load_shangyule()
    load_jiashi()

    # 启动热键监听
    start_hotkey_listener()

    # 将main()放在后台线程运行（daemon=True确保主线程退出时自动结束）
    main_thread = threading.Thread(target=main, daemon=True)
    main_thread.start()

    # GUI必须在主线程运行（Tkinter要求）
    # 这样可以确保GUI正常工作且不会崩溃
    create_gui()
