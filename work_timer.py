"""
ElePhocus - Work Time Tracker  v1.1
Copyright (c) 2025 붉은코끼리 (Red Elephant)
Licensed under MIT License with commercial restriction

상업적 이용 또는 앱스토어 배포 시 사전 허가 필요
Contact: [khsx007@naver.com]
"""
import customtkinter as ctk
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox
import json
import os
import sys
import platform
from datetime import datetime
import threading
import time

IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"
VERSION = "1.1"

if IS_MAC:
    from AppKit import NSWorkspace, NSApplication
    from Quartz import (CGSessionCopyCurrentDictionary, CGEventSourceSecondsSinceLastEventType,
                        kCGEventSourceStateHIDSystemState, kCGAnyInputEventType)
elif IS_WIN:
    import ctypes
    from ctypes import wintypes
    import psutil


def resource_path(name):
    """PyInstaller 패키징 후에도 리소스 경로를 찾도록"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


# 윈도우: 번들 폰트를 (설치 없이) 이 프로세스에서만 사용하도록 등록. Tk 창 만들기 전에 해야 함
if IS_WIN:
    try:
        _font_path = resource_path("NotoSansKR-Light.ttf")
        if os.path.exists(_font_path):
            ctypes.windll.gdi32.AddFontResourceExW(_font_path, 0x10, 0)  # FR_PRIVATE
    except Exception:
        pass

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class WorkTimer:
    def __init__(self, root):
        self.root = root
        self.root.title("ElePhocus")

        self.font = self.pick_font()

        self.compact_height = 170
        self.expanded_height = 510 if IS_WIN else 510
        self.root.geometry(f"300x{self.compact_height}")
        self.root.resizable(False, False)

        # (항상 위 기능 제거됨)

        if IS_MAC:
            self.setup_menubar()

        if IS_MAC:
            self.config_file = os.path.expanduser("~/Library/Application Support/ElePhocus/config.json")
        else:
            self.config_file = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")),
                                            "ElePhocus", "config.json")
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

        self.tracked_apps = []
        self.elapsed_seconds = 0
        self.is_running = False
        self.monitoring_thread = None
        self.stop_monitoring = False
        self.last_active_app = ""
        self.idle_threshold = 30
        self.is_settings_expanded = False

        self.color_themes = [
            {'name': 'Strawberry', 'primary': '#FF6B6B', 'bg': '#2B1F1F', 'card': '#3D2B2B', 'text': '#FFFFFF'},
            {'name': 'Ocean', 'primary': '#4ECDC4', 'bg': '#1F2B2B', 'card': '#2B3D3D', 'text': '#FFFFFF'},
            {'name': 'Cloud', 'primary': '#45B7D1', 'bg': '#1F2534', 'card': '#2B3546', 'text': '#FFFFFF'},
            {'name': 'Tangerine', 'primary': '#FFA07A', 'bg': '#2B231F', 'card': '#3D322B', 'text': '#FFFFFF'},
            {'name': 'Spearmint', 'primary': '#98D8C8', 'bg': '#1F2B26', 'card': '#2B3D36', 'text': '#FFFFFF'},
            {'name': 'Lemon', 'primary': '#F7DC6F', 'bg': '#2B2B1F', 'card': '#3D3D2B', 'text': '#FFFFFF'},
            {'name': 'Cherry', 'primary': '#C44569', 'bg': '#2B1F24', 'card': '#3D2B33', 'text': '#FFFFFF'},
            {'name': 'Lavender', 'primary': '#A29BFE', 'bg': '#24223D', 'card': '#33304D', 'text': '#FFFFFF'},
            {'name': 'Blueberry', 'primary': '#74B9FF', 'bg': '#1F2534', 'card': '#2B3546', 'text': '#FFFFFF'},
            {'name': 'Rose', 'primary': '#FD79A8', 'bg': '#2B1F26', 'card': '#3D2B36', 'text': '#FFFFFF'},
            {'name': 'Honey', 'primary': '#FDCB6E', 'bg': '#2B261F', 'card': '#3D3628', 'text': '#FFFFFF'},
            {'name': 'Grape', 'primary': '#6C5CE7', 'bg': '#1F1E2B', 'card': '#2E2B3D', 'text': '#FFFFFF'},
            {'name': 'Lime', 'primary': '#00B894', 'bg': '#1F2B25', 'card': '#2B3D35', 'text': '#FFFFFF'},
            {'name': 'Salmon', 'primary': '#FA8072', 'bg': '#2B221F', 'card': '#3D302B', 'text': '#FFFFFF'},
            {'name': 'Slate', 'primary': '#95A5A6', 'bg': '#23252A', 'card': '#32353B', 'text': '#FFFFFF'},
            {'name': 'Coral', 'primary': '#FF7675', 'bg': '#2B1F20', 'card': '#3D2B2D', 'text': '#FFFFFF'},
            {'name': 'Teal', 'primary': '#16A085', 'bg': '#1F2829', 'card': '#2B3738', 'text': '#FFFFFF'},
            {'name': 'Plum', 'primary': '#9B59B6', 'bg': '#251F2B', 'card': '#352B3D', 'text': '#FFFFFF'},
            {'name': 'Olive', 'primary': '#A29751', 'bg': '#27261F', 'card': '#38362B', 'text': '#FFFFFF'},
            {'name': 'Crimson', 'primary': '#DC143C', 'bg': '#2B1F21', 'card': '#3D2B2F', 'text': '#FFFFFF'}
        ]
        self.current_color_index = 0

        self.load_config()
        self.setup_ui()
        self.update_timer_display()
        self.start_monitoring()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ---------- 폰트 ----------
    def pick_font(self):
        if IS_WIN:
            try:
                fams = tkfont.families(self.root)
                for cand in ("Noto Sans KR Light", "Noto Sans KR"):
                    if cand in fams:
                        return cand
            except Exception:
                pass
            return "Malgun Gothic"
        return "Helvetica"

    # ---------- 메뉴바 (mac) ----------
    def setup_menubar(self):
        try:
            app = NSApplication.sharedApplication()
            main_menu = app.mainMenu()
            if main_menu:
                app_menu_item = main_menu.itemAtIndex_(0)
                if app_menu_item:
                    app_menu = app_menu_item.submenu()
                    if app_menu:
                        about_item = app_menu.itemAtIndex_(0)
                        if about_item and "about" in about_item.title().lower():
                            about_item.setTarget_(self)
                            about_item.setAction_('showAbout:')
        except Exception as e:
            print(f"메뉴바 설정 오류: {e}")

    def showAbout_(self, sender):
        about_text = f"""ElePhocus

개발자: 붉은코끼리
버전: {VERSION}

작업 시간을 추적하는 
미니멀 타이머 앱입니다."""
        messagebox.showinfo("About ElePhocus", about_text)

    # ---------- UI ----------
    def setup_ui(self):
        F = self.font
        self.top_frame = ctk.CTkFrame(self.root, corner_radius=10)
        self.top_frame.pack(fill="x", padx=15, pady=15)

        header_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        header_frame.pack(fill='x', padx=10, pady=(5, 0))

        date_str = datetime.now().strftime("%m월 %d일")
        self.header_label = ctk.CTkLabel(header_frame, text=f"  {date_str}",
                                         font=(F, 11, "bold"))
        self.header_label.pack(side="left")

        self.settings_btn = ctk.CTkButton(header_frame, text="⚙", width=40,
                                          command=self.toggle_settings,
                                          font=("Segoe UI Symbol", 15) if IS_WIN else (F, 18),
                                          height=28,
                                          fg_color="transparent",
                                          hover_color=("gray70", "gray30"))
        self.settings_btn.pack(side="right",pady=(3, 0) if IS_WIN else 0)

        self.timer_label = ctk.CTkLabel(self.top_frame, text="00:00:00",
                                        font=("Segoe UI", 42, "bold") if IS_WIN else (F, 42, "bold"))
        self.timer_label.pack()

        self.status_label = ctk.CTkLabel(self.top_frame, text="⏸ 대기 중",
                                         font=(F, 11))
        self.status_label.pack()

        self.current_app_label = ctk.CTkLabel(self.top_frame, text="",
                                              font=(F, 10), height=10)
        self.current_app_label.pack()

        self.color_btn = ctk.CTkButton(self.top_frame, text="🎨 Color",
                                       command=self.change_color,
                                       font=(F, 12),
                                       height=35)
        self.color_btn.pack(pady=(5, 10))

        self.settings_container = ctk.CTkFrame(self.root, fg_color="transparent")

        settings_inner = ctk.CTkFrame(self.settings_container, fg_color="transparent")
        settings_inner.pack(fill='both', expand=True, padx=15, pady=(0, 10))

        ctk.CTkLabel(settings_inner, text="추적 대상 앱",
                     font=(F, 11, "bold")).pack(anchor='w', pady=(0, 5))

        list_frame = ctk.CTkFrame(settings_inner, fg_color="transparent")
        list_frame.pack(fill='x', pady=(0, 5))

        self.app_listbox = tk.Listbox(list_frame, height=4,
                                      font=(F, 11),
                                      bg="#2b2b2b", fg="#ffffff",
                                      selectbackground="#4a9eff",
                                      selectforeground="#ffffff",
                                      relief="solid", borderwidth=1,
                                      highlightthickness=0)
        self.app_listbox.pack(fill='x')

        btn_frame = ctk.CTkFrame(settings_inner, fg_color="transparent")
        btn_frame.pack(fill='x', pady=(0, 15))

        self.remove_btn = ctk.CTkButton(btn_frame, text="선택 삭제", font=(F, 12),
                                        command=self.remove_selected_app)
        self.remove_btn.pack(side="left", fill='x', expand=True, padx=(0, 5))

        self.clear_btn = ctk.CTkButton(btn_frame, text="전체 비우기", font=(F, 12),
                                       command=self.clear_all_apps)
        self.clear_btn.pack(side="left", fill='x', expand=True)

        ctk.CTkLabel(settings_inner, text="앱 추가",
                     font=(F, 11, "bold")).pack(anchor='w', pady=(0, 5))

        combo_frame = ctk.CTkFrame(settings_inner, fg_color="transparent")
        combo_frame.pack(fill='x', pady=(0, 5))

        self.running_apps_var = ctk.StringVar()
        self.running_apps_combo = ctk.CTkComboBox(combo_frame,
                                                  variable=self.running_apps_var,
                                                  font=(F, 12),
                                                  dropdown_font=(F, 12),
                                                  state='readonly',
                                                  border_width=1)
        self.running_apps_combo.pack(side="left", fill='x', expand=True, padx=(0, 5))

        self.refresh_btn = ctk.CTkButton(combo_frame, text="↻", width=50,
                                         command=self.refresh_running_apps,
                                         font=(F, 16))
        self.refresh_btn.pack(side="left", padx=(0, 5))

        self.add_combo_btn = ctk.CTkButton(combo_frame, text="추가", width=80,
                                           font=(F, 12),
                                           command=self.add_from_running_apps)
        self.add_combo_btn.pack(side="left")

        entry_frame = ctk.CTkFrame(settings_inner, fg_color="transparent")
        entry_frame.pack(fill='x', pady=(0, 15))

        self.app_entry = ctk.CTkEntry(entry_frame,
                                      placeholder_text="대소문자 정확히 입력",
                                      font=(F, 11),
                                      border_width=1)
        self.app_entry.pack(side="left", fill='x', expand=True, padx=(0, 5))

        self.add_manual_btn = ctk.CTkButton(entry_frame, text="직접 추가", width=80,
                                            font=(F, 12),
                                            command=self.add_manual_app)
        self.add_manual_btn.pack(side="left")

        self.reset_btn = ctk.CTkButton(settings_inner, text="⚠️ 타이머 0으로 초기화",
                                       font=(F, 12),
                                       command=self.reset_timer)
        self.reset_btn.pack(fill='x', pady=(5, 0))

        self.refresh_running_apps()
        self.update_app_list()
        self.apply_color()

    def change_color(self):
        self.current_color_index = (self.current_color_index + 1) % len(self.color_themes)
        self.apply_color()
        self.save_config()

    def get_text_color(self, bg_color):
        r = int(bg_color[1:3], 16)
        g = int(bg_color[3:5], 16)
        b = int(bg_color[5:7], 16)
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        return '#000000' if brightness > 155 else '#FFFFFF'

    def get_complementary_color(self, hex_color):
        if hex_color.upper() == '#F7DC6F':
            return '#00CED1'
        if hex_color.upper() == '#FDCB6E':
            return '#5AADFF'

        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)

        comp_r, comp_g, comp_b = 255 - r, 255 - g, 255 - b
        comp_brightness = (comp_r * 299 + comp_g * 587 + comp_b * 114) / 1000

        if comp_brightness < 150:
            comp_r = min(255, int(comp_r * 2.2))
            comp_g = min(255, int(comp_g * 2.2))
            comp_b = min(255, int(comp_b * 2.2))

        return f'#{comp_r:02x}{comp_g:02x}{comp_b:02x}'

    def apply_color(self):
        theme = self.color_themes[self.current_color_index]

        self.root.configure(fg_color=theme['bg'])
        self.top_frame.configure(fg_color=theme['card'])
        self.timer_label.configure(text_color=theme['primary'])
        self.header_label.configure(text_color=theme['primary'])
        self.current_app_label.configure(text_color=theme['primary'])

        text_color = self.get_text_color(theme['primary'])

        self.color_btn.configure(text=f"🎨 {theme['name']}",
                                 fg_color=theme['primary'],
                                 hover_color=theme['primary'],
                                 text_color=text_color)
        self.settings_btn.configure(text_color=theme['primary'])

        for name in ('remove_btn', 'clear_btn', 'refresh_btn', 'add_combo_btn',
                     'add_manual_btn', 'reset_btn'):
            if hasattr(self, name):
                getattr(self, name).configure(fg_color=theme['primary'],
                                              hover_color=theme['primary'],
                                              text_color=text_color)

        if hasattr(self, 'settings_container'):
            self.settings_container.configure(fg_color="transparent")

        if self.is_running:
            self.status_label.configure(text_color=self.get_complementary_color(theme['primary']))

    def toggle_settings(self):
        if self.is_settings_expanded:
            self.settings_container.pack_forget()
            self.root.geometry(f"300x{self.compact_height}")
            self.is_settings_expanded = False
        else:
            self.settings_container.pack(fill='both', expand=True, padx=0, pady=0)
            self.root.geometry(f"300x{self.expanded_height}")
            self.is_settings_expanded = True

    def format_time(self, seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def update_timer_display(self):
        self.timer_label.configure(text=self.format_time(self.elapsed_seconds))

    def update_app_list(self):
        self.app_listbox.delete(0, tk.END)
        for app in self.tracked_apps:
            self.app_listbox.insert(tk.END, app)

    # ---------- 플랫폼별 앱 감지 ----------
    def list_running_apps(self):
        names = []
        if IS_MAC:
            for app in NSWorkspace.sharedWorkspace().runningApplications():
                name = app.localizedName()
                if name and name not in ['Python', 'python', 'loginwindow', 'Finder']:
                    if not name.startswith('com.apple.'):
                        names.append(name)
        elif IS_WIN:
            user32 = ctypes.windll.user32
            EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

            def cb(hwnd, lparam):
                if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0:
                    n = self.win_process_name(hwnd)
                    if n and n.lower() not in ('elephocus', 'python', 'pythonw', 'explorer'):
                        names.append(n)
                return True

            user32.EnumWindows(EnumProc(cb), 0)
        return sorted(set(names))

    def win_process_name(self, hwnd):
        try:
            pid = wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            name = psutil.Process(pid.value).name()
            return name[:-4] if name.lower().endswith('.exe') else name
        except Exception:
            return None

    def get_active_app_name(self):
        try:
            if IS_MAC:
                app = NSWorkspace.sharedWorkspace().frontmostApplication()
                return app.localizedName() if app else None
            if IS_WIN:
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                return self.win_process_name(hwnd) if hwnd else None
        except Exception:
            pass
        return None

    def refresh_running_apps(self):
        app_names = self.list_running_apps()
        self.running_apps_combo.configure(values=app_names)
        if app_names:
            self.running_apps_combo.set(app_names[0])

    def add_from_running_apps(self):
        selected_app = self.running_apps_var.get().strip()
        if not selected_app: return
        if selected_app in self.tracked_apps: return
        self.tracked_apps.append(selected_app)
        self.update_app_list()
        self.save_config()

    def add_manual_app(self):
        app_name = self.app_entry.get().strip()
        if not app_name: return
        if app_name in self.tracked_apps: return
        self.tracked_apps.append(app_name)
        self.update_app_list()
        self.app_entry.delete(0, "end")
        self.save_config()

    def remove_selected_app(self):
        selection = self.app_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "삭제할 앱을 선택하세요.")
            return
        self.tracked_apps.pop(selection[0])
        self.update_app_list()
        self.save_config()

    def clear_all_apps(self):
        if not self.tracked_apps: return
        if messagebox.askyesno("확인", "모든 앱을 삭제하시겠습니까?"):
            self.tracked_apps.clear()
            self.update_app_list()
            self.save_config()

    def reset_timer(self):
        if messagebox.askyesno("확인", "초기화 하시겠습니까?"):
            self.elapsed_seconds = 0
            self.update_timer_display()
            self.save_config()

    def is_user_active(self):
        try:
            if IS_MAC:
                session_dict = CGSessionCopyCurrentDictionary()
                if session_dict and session_dict.get("CGSSessionScreenIsLocked", False):
                    return False
                idle_time = CGEventSourceSecondsSinceLastEventType(
                    kCGEventSourceStateHIDSystemState, kCGAnyInputEventType)
                return idle_time < self.idle_threshold
            if IS_WIN:
                class LASTINPUTINFO(ctypes.Structure):
                    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]
                info = LASTINPUTINFO()
                info.cbSize = ctypes.sizeof(LASTINPUTINFO)
                ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info))
                idle = (ctypes.windll.kernel32.GetTickCount() - info.dwTime) / 1000.0
                return idle < self.idle_threshold
        except Exception:
            pass
        return True

    def is_tracked_app_active(self):
        if not self.tracked_apps: return False, None
        active_name = self.get_active_app_name()
        if not active_name: return False, None
        for tracked_app in self.tracked_apps:
            if tracked_app.lower() in active_name.lower() or active_name.lower() in tracked_app.lower():
                return True, active_name
        return False, None

    def monitoring_loop(self):
        last_update = time.time()
        while not self.stop_monitoring:
            try:
                current_time = time.time()
                user_active = self.is_user_active()
                app_active, active_app_name = self.is_tracked_app_active()

                if user_active and app_active:
                    if not self.is_running or self.last_active_app != active_app_name:
                        self.is_running = True
                        self.last_active_app = active_app_name
                        theme = self.color_themes[self.current_color_index]
                        complementary = self.get_complementary_color(theme['primary'])
                        self.root.after(0, lambda c=complementary: self.status_label.configure(text="▶ 집중 중", text_color=c))
                        self.root.after(0, lambda n=active_app_name: self.current_app_label.configure(text=n))

                    if current_time - last_update >= 1.0:
                        self.elapsed_seconds += 1
                        self.root.after(0, self.update_timer_display)
                        last_update = current_time
                else:
                    if self.is_running:
                        self.is_running = False
                        self.last_active_app = ""
                        msg = "⏸ 자리 비움" if not user_active else "⏸ 딴짓 중..."
                        self.root.after(0, lambda m=msg: self.status_label.configure(text=m, text_color='#757575'))
                        self.root.after(0, lambda: self.current_app_label.configure(text=""))

                if int(current_time) % 10 == 0: self.root.after(0, self.save_config)
                time.sleep(0.5)
            except Exception:
                time.sleep(1)

    def start_monitoring(self):
        self.stop_monitoring = False
        threading.Thread(target=self.monitoring_loop, daemon=True).start()

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.tracked_apps = config.get('tracked_apps', [])
                    if config.get('date') == datetime.now().strftime('%Y-%m-%d'):
                        self.elapsed_seconds = config.get('elapsed_seconds', 0)
                    loaded_index = config.get('color_index', 0)
                    self.current_color_index = loaded_index if loaded_index < len(self.color_themes) else 0
            except Exception:
                pass

    def save_config(self):
        try:
            config = {
                'tracked_apps': self.tracked_apps,
                'elapsed_seconds': self.elapsed_seconds,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'color_index': self.current_color_index
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
        except Exception:
            pass

    def on_closing(self):
        self.stop_monitoring = True
        self.save_config()
        self.root.destroy()


def main():
    root = ctk.CTk()
    app = WorkTimer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
