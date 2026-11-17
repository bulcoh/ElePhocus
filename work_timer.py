"""
ElePhocus - Work Time Tracker  v1.3
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
from datetime import datetime, timedelta
import threading
import time
import re
import webbrowser
import urllib.request
import ssl

IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"
VERSION = "1.3"
GITHUB_REPO = "bulcoh/ElePhocus"
LATEST_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases"
UPDATE_CHECK_INTERVAL = 12 * 3600   # 켜둔 채로 있어도 12시간마다 다시 확인

# 시계의 ':' 를 위로 끌어올리는 양(px). 너무 높으면 줄이고, 아직 낮으면 키우세요.
COLON_LIFT = 4

# 창 높이(축소 상태). 잘리면 윈도우 숫자만 키우세요. 펼친 높이는 자동으로 같이 늘어납니다.
COMPACT_HEIGHT = 205 if IS_WIN else 182
SETTINGS_PANEL_HEIGHT = 340

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
        _font_files = []
        _fdir = resource_path("fonts")          # fonts/ 폴더 안의 ttf/otf 전부 등록
        if os.path.isdir(_fdir):
            _font_files += [os.path.join(_fdir, f) for f in sorted(os.listdir(_fdir))
                            if f.lower().endswith((".ttf", ".otf", ".ttc"))]
        for _fp in _font_files:
            ctypes.windll.gdi32.AddFontResourceExW(_fp, 0x10, 0)  # FR_PRIVATE
    except Exception:
        pass

def detect_lang():
    """OS에 설정된 언어 코드(ko, en, ja, zh ...)"""
    try:
        if IS_MAC:
            from Foundation import NSLocale
            return str(NSLocale.preferredLanguages()[0]).split("-")[0].lower()
        if IS_WIN:
            buf = ctypes.create_unicode_buffer(85)
            ctypes.windll.kernel32.GetUserDefaultLocaleName(buf, 85)
            return buf.value.split("-")[0].lower()
    except Exception:
        pass
    try:
        import locale
        return (locale.getdefaultlocale()[0] or "en").split("_")[0].lower()
    except Exception:
        return "en"


_EN_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def format_date(d, lang):
    if lang == "ko":
        return f"{d.month}월 {d.day}일"
    if lang in ("ja", "zh"):
        return f"{d.month}月{d.day}日"
    return f"{_EN_MONTHS[d.month - 1]} {d.day}"


def parse_version(s):
    return tuple(int(x) for x in re.findall(r"\d+", s or ""))


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class WorkTimer:
    def __init__(self, root):
        self.root = root
        self.root.title("ElePhocus")
        self.set_window_icon()

        self.lang = detect_lang()
        self.font = self.pick_font()

        self.compact_height = COMPACT_HEIGHT
        self.expanded_height = COMPACT_HEIGHT + SETTINGS_PANEL_HEIGHT
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
        self._update_info = None
        self._update_checking = False

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
        self.schedule_midnight()
        self.root.after(3000, self.start_update_check)

    # ---------- 창 아이콘 (윈도우 타이틀바/작업표시줄) ----------
    def set_window_icon(self):
        if not IS_WIN:
            return
        ico = resource_path("app_icon.ico")
        if not os.path.exists(ico):
            return

        def apply():
            try:
                self.root.iconbitmap(ico)
            except Exception:
                pass
        apply()
        # customtkinter가 약 200ms 뒤에 자기 기본 아이콘으로 덮어쓰는 경우를 대비해 한 번 더
        self.root.after(300, apply)

    # ---------- 폰트 ----------
    def pick_font(self):
        self.timer_family = "Segoe UI"
        if IS_WIN:
            try:
                # 'Pretendard', 'Pretendard Medium' 등 어떤 이름으로 등록됐든 찾아서 사용
                pret = [f for f in tkfont.families(self.root) if f.lower().startswith("pretendard")]
                if pret:
                    pret.sort(key=lambda f: (f != "Pretendard", len(f)))
                    self.timer_family = pret[0]
                    return pret[0]
            except Exception:
                pass
            return "Segoe UI"      # Pretendard 로딩 실패 시에만 (한글은 윈도우가 맑은 고딕으로 대신 채움)
        # 맥: 1.0 때 customtkinter 기본값이던 시스템 폰트(SF) 사용. 한글은 자동으로 Apple SD Gothic Neo
        self.timer_family = "SF Pro Display"
        return "SF Pro Display"

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

        self._shown_date = datetime.now().date()
        self.header_label = ctk.CTkLabel(header_frame,
                                         text=f"  {format_date(self._shown_date, self.lang)}",
                                         font=(F, 11, "bold"))
        self.header_label.pack(side="left")

        self.settings_btn = ctk.CTkButton(header_frame, text="⚙", width=40,
                                          command=self.toggle_settings,
                                          font=("Segoe UI Symbol", 15) if IS_WIN else (F, 18),
                                          height=28,
                                          fg_color="transparent",
                                          hover_color=("gray70", "gray30"))
        self.settings_btn.pack(side="right",pady=(3, 0) if IS_WIN else 0)

        # 새 버전 알림 버튼 (새 버전이 있을 때만 show_update_button()에서 표시)
        self.update_btn = ctk.CTkButton(header_frame, text="", width=60, height=24,
                                        font=(F, 11, "bold"),
                                        fg_color="transparent",
                                        hover_color=("gray70", "gray30"),
                                        command=self.open_update_page)

        # 시계: 시/분/초와 ':'를 따로 그려서 ':'를 숫자 높이 중앙으로 맞춘다
        TS = 42
        timer_font = ctk.CTkFont(family=self.timer_family, size=TS, weight="bold")
        probe = tkfont.Font(root=self.root, family=self.timer_family, size=-TS, weight="bold")
        digit_w = max(probe.measure(d) for d in "0123456789")
        self.seg_w = digit_w * 2 + 4
        self.timer_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        self.timer_frame.pack()
        self.timer_parts = []
        for i in range(3):
            if i:
                colon = ctk.CTkLabel(self.timer_frame, text=":", font=timer_font, width=0)
                colon.pack(side="left", pady=(0, COLON_LIFT * 2))
                self.timer_parts.append(colon)
            seg = ctk.CTkLabel(self.timer_frame, text="00", font=timer_font, width=self.seg_w)
            seg.pack(side="left")
            self.timer_parts.append(seg)
        self.timer_segments = [self.timer_parts[0], self.timer_parts[2], self.timer_parts[4]]

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
        for w in self.timer_parts:
            w.configure(text_color=theme['primary'])
        self.header_label.configure(text_color=theme['primary'])
        self.current_app_label.configure(text_color=theme['primary'])

        text_color = self.get_text_color(theme['primary'])

        self.color_btn.configure(text=f"🎨 {theme['name']}",
                                 fg_color=theme['primary'],
                                 hover_color=theme['primary'],
                                 text_color=text_color)
        self.settings_btn.configure(text_color=theme['primary'])
        self.update_btn.configure(text_color=theme['primary'])

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
        t = self.elapsed_seconds
        h, m, s = t // 3600, (t % 3600) // 60, t % 60
        hs = f"{h:02d}"
        self.timer_segments[0].configure(text=hs, width=self.seg_w if len(hs) <= 2 else self.seg_w * 3 // 2)
        self.timer_segments[1].configure(text=f"{m:02d}")
        self.timer_segments[2].configure(text=f"{s:02d}")

    # ---------- 날짜 갱신: 다음 자정까지 대기했다가 딱 한 번만 깨어남 ----------
    def schedule_midnight(self):
        now = datetime.now()
        nxt = (now + timedelta(days=1)).replace(hour=0, minute=0, second=1, microsecond=0)
        ms = max(1000, int((nxt - now).total_seconds() * 1000))
        self.root.after(ms, self.on_midnight)

    def on_midnight(self):
        today = datetime.now().date()
        self._shown_date = today
        self.header_label.configure(text=f"  {format_date(today, self.lang)}")
        self.schedule_midnight()

    # ---------- 업데이트 확인: 시작 3초 뒤 1회 + 12시간마다 ----------
    def start_update_check(self):
        if not self._update_checking:
            self._update_checking = True
            threading.Thread(target=self.check_for_update, daemon=True).start()
        self.root.after(UPDATE_CHECK_INTERVAL * 1000, self.start_update_check)

    def show_update_button(self):
        if self._update_info and not self.update_btn.winfo_ismapped():
            self.update_btn.configure(text=f"↑ {self._update_info[0]}")
            self.update_btn.pack(side="right", padx=(0, 2))

    def check_for_update(self):
        try:
            try:
                import certifi
                ctx = ssl.create_default_context(cafile=certifi.where())
            except Exception:
                ctx = ssl.create_default_context()
            req = urllib.request.Request(LATEST_API, headers={
                "User-Agent": f"ElePhocus/{VERSION}",
                "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req, timeout=8, context=ctx) as r:
                data = json.load(r)
            tag = data.get("tag_name", "")
            if parse_version(tag) > parse_version(VERSION):
                url = data.get("html_url") or RELEASES_URL
                if not url.startswith("https://github.com/"):
                    url = RELEASES_URL
                self._update_info = (tag, url)
                self.root.after(0, self.show_update_button)
        except Exception:
            pass          # 오프라인 등 - 조용히 무시
        finally:
            self._update_checking = False

    def open_update_page(self):
        if not self._update_info:
            return
        tag, url = self._update_info
        if messagebox.askyesno("업데이트",
                               f"새 버전 {tag} 이(가) 나왔어요. (현재 v{VERSION})\n다운로드 페이지를 열까요?"):
            webbrowser.open(url)

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
                    self.elapsed_seconds = config.get('elapsed_seconds', 0)   # 0 초기화는 초기화 버튼으로만
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
