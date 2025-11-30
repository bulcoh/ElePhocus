import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime
from AppKit import NSWorkspace, NSApplication
from Quartz import CGSessionCopyCurrentDictionary, CGEventSourceSecondsSinceLastEventType, kCGEventSourceStateHIDSystemState, kCGAnyInputEventType
import threading
import time

class WorkTimer:
    def __init__(self, root):
        self.root = root
        self.root.title("ElePhocus")
        
        # --- 사이즈 설정 ---
        self.compact_height = 180
        self.expanded_height = 550
        
        # 초기 시작: 콤팩트 모드
        self.root.geometry(f"300x{self.compact_height}")
        self.root.resizable(False, False)
        
        # 항상 위에 표시
        self.root.attributes('-topmost', True)
        
        # macOS 메뉴바 설정
        self.setup_menubar()
        
        # 설정 파일 경로
        self.config_file = os.path.expanduser("~/Library/Application Support/ElePhocus/config.json")
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        # 변수 초기화
        self.tracked_apps = []
        self.elapsed_seconds = 0
        self.is_running = False
        self.monitoring_thread = None
        self.stop_monitoring = False
        self.last_active_app = ""
        self.idle_threshold = 30
        self.is_settings_expanded = False
        
        # 컬러 테마 - 튜플로 묶여있음!
        self.color_list = [
            ('#FF6B6B', 'Strawberry'),
            ('#4ECDC4', 'Ocean'),
            ('#45B7D1', 'Cloud'),
            ('#FFA07A', 'Tangerine'),
            ('#98D8C8', 'Spearmint'),
            ('#F7DC6F', 'Lemon'),
            ('#C44569', 'Cherry'),
            ('#A29BFE', 'Lavender'),
            ('#74B9FF', 'Blueberry'),
            ('#FD79A8', 'Rose'),
            ('#FDCB6E', 'Honey'),
            ('#6C5CE7', 'Grape'),
            ('#00B894', 'Lime'),
            ('#E17055', 'Apricot'),
            ('#81ECEC', 'Mint'),
            ('#FAB1A0', 'Peach'),
            ('#FF7675', 'Watermelon'),
            ('#DFE6E9', 'Pearl'),
            ('#55EFC4', 'Emerald'),
            ('#FFEAA7', 'Vanilla')
        ]
        self.current_color_index = 0
        
        # 설정 로드
        self.load_config()
        
        # UI 구성
        self.setup_ui()
        
        # 초기값 업데이트
        self.update_timer_display()
        
        # 모니터링 시작
        self.start_monitoring()
        
        # 종료 이벤트
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_menubar(self):
        """macOS 메뉴바에 About 메뉴 추가"""
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
        """About 메뉴 클릭 시 호출"""
        about_text = """ElePhocus

개발자: 붉은코끼리
버전: 0.1.2

작업 시간을 추적하는 
미니멀 타이머 앱입니다."""
        messagebox.showinfo("About ElePhocus", about_text)
    
    def setup_ui(self):
        style = ttk.Style()
        style.configure('Timer.TLabel', font=('Helvetica', 42, 'bold'))
        style.configure('Status.TLabel', font=('Helvetica', 11))
        style.configure('Sub.TLabel', font=('Helvetica', 10), foreground='gray')
        
        # 상단 영역
        self.top_frame = ttk.Frame(self.root, padding="15")
        self.top_frame.pack(fill=tk.X, side=tk.TOP)
        
        # 헤더
        header_frame = ttk.Frame(self.top_frame)
        header_frame.pack(fill='x', pady=(0, 5))
        
        date_str = datetime.now().strftime("%m월 %d일")
        self.header_label = ttk.Label(header_frame, text=f"ElePhocus • {date_str}", 
                                       font=('Helvetica', 11, 'bold'), foreground='#999999')
        self.header_label.pack(side=tk.LEFT, anchor='center')
        
        self.settings_btn = ttk.Button(header_frame, text="⚙️", width=3, command=self.toggle_settings)
        self.settings_btn.pack(side=tk.RIGHT)
        
        # 타이머
        self.timer_label = ttk.Label(self.top_frame, text="00:00:00", style='Timer.TLabel')
        self.timer_label.pack(pady=(5, 0))
        
        # 상태
        self.status_frame = ttk.Frame(self.top_frame)
        self.status_frame.pack(fill='x', pady=(5, 0))
        
        self.status_label = ttk.Label(self.status_frame, text="⏸ 대기 중", style='Status.TLabel', anchor='center')
        self.status_label.pack(fill='x')
        
        self.current_app_label = ttk.Label(self.top_frame, text="", style='Sub.TLabel')
        self.current_app_label.pack()

        # 통계
        self.stats_label = ttk.Label(self.top_frame, text="Today: 0m", font=('Helvetica', 9), foreground='#888888')
        self.stats_label.pack(pady=(5, 0))
        
        # 컬러 버튼
        self.color_btn = ttk.Button(self.top_frame, text="🎨 Color", command=self.change_color)
        self.color_btn.pack(pady=(8, 0))

        # 설정 영역
        self.settings_container = ttk.Frame(self.root)

        ttk.Separator(self.settings_container, orient='horizontal').pack(fill='x', padx=10, pady=5)
        
        settings_inner = ttk.Frame(self.settings_container, padding="15")
        settings_inner.pack(fill='both', expand=True)

        # 앱 목록
        ttk.Label(settings_inner, text="추적 대상 앱", font=('Helvetica', 11, 'bold')).pack(anchor='w', pady=(0, 5))
        
        list_frame = ttk.Frame(settings_inner)
        list_frame.pack(fill='both', expand=True, pady=(0, 5))
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill='y')
        
        self.app_listbox = tk.Listbox(list_frame, height=5, font=('Helvetica', 11), yscrollcommand=scrollbar.set)
        self.app_listbox.pack(side=tk.LEFT, fill='both', expand=True)
        scrollbar.config(command=self.app_listbox.yview)
        
        btn_frame = ttk.Frame(settings_inner)
        btn_frame.pack(fill='x', pady=(0, 15))
        ttk.Button(btn_frame, text="선택 삭제", command=self.remove_selected_app).pack(side=tk.LEFT, fill='x', expand=True, padx=(0, 2))
        ttk.Button(btn_frame, text="전체 비우기", command=self.clear_all_apps).pack(side=tk.LEFT, fill='x', expand=True, padx=(2, 0))

        # 앱 추가
        ttk.Label(settings_inner, text="앱 추가", font=('Helvetica', 11, 'bold')).pack(anchor='w', pady=(0, 5))
        
        combo_frame = ttk.Frame(settings_inner)
        combo_frame.pack(fill='x', pady=(0, 5))
        
        self.running_apps_var = tk.StringVar()
        self.running_apps_combo = ttk.Combobox(combo_frame, textvariable=self.running_apps_var, state='readonly', width=12) 
        self.running_apps_combo.pack(side=tk.LEFT)
        
        ttk.Button(combo_frame, text="↻", width=2, command=self.refresh_running_apps).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(combo_frame, text="추가", width=6, command=self.add_from_running_apps).pack(side=tk.LEFT, padx=(2, 0))
        
        # 직접 입력
        entry_frame = ttk.Frame(settings_inner)
        entry_frame.pack(fill='x', pady=(0, 15))
        self.app_entry_var = tk.StringVar()
        self.app_entry = tk.Entry(entry_frame, textvariable=self.app_entry_var, width=18, 
                                   font=('Helvetica', 11), relief='solid', borderwidth=1)
        self.app_entry.pack(side=tk.LEFT, fill='x', expand=True)
        
        self.setup_placeholder(self.app_entry, "대소문자 정확히 입력")
        
        ttk.Button(entry_frame, text="직접 추가", width=8, command=self.add_manual_app).pack(side=tk.LEFT, padx=(5, 0))

        # 초기화 버튼
        ttk.Button(settings_inner, text="⚠️ 타이머 0으로 초기화", command=self.reset_timer).pack(fill='x', side=tk.BOTTOM)

        self.refresh_running_apps()
        self.update_app_list()
        
        # 초기 컬러 적용
        self.apply_color()
    
    def setup_placeholder(self, entry_widget, placeholder_text):
        entry_widget.placeholder = placeholder_text
        entry_widget.placeholder_active = True
        
        entry_widget.insert(0, placeholder_text)
        entry_widget.config(fg='#999999')
        
        def on_focus_in(event):
            if entry_widget.placeholder_active:
                entry_widget.delete(0, tk.END)
                entry_widget.config(fg='#000000')
                entry_widget.placeholder_active = False
        
        def on_focus_out(event):
            if not entry_widget.get():
                entry_widget.insert(0, placeholder_text)
                entry_widget.config(fg='#999999')
                entry_widget.placeholder_active = True
        
        entry_widget.bind('<FocusIn>', on_focus_in)
        entry_widget.bind('<FocusOut>', on_focus_out)
    
    def change_color(self):
        self.current_color_index = (self.current_color_index + 1) % len(self.color_list)
        self.apply_color()
        self.save_config()
    
    def apply_color(self):
        color_code, color_name = self.color_list[self.current_color_index]
        
        # 타이머 색상
        self.timer_label.configure(foreground=color_code)
        
        # 버튼 텍스트
        self.color_btn.configure(text=f"🎨 {color_name}")
        
        # 집중 중 상태
        if self.is_running:
            self.status_label.configure(foreground=color_code)

    def toggle_settings(self):
        if self.is_settings_expanded:
            self.settings_container.pack_forget()
            self.root.geometry(f"300x{self.compact_height}")
            self.is_settings_expanded = False
        else:
            self.settings_container.pack(fill='both', expand=True)
            self.root.geometry(f"300x{self.expanded_height}")
            self.is_settings_expanded = True

    def format_time(self, seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def update_timer_display(self):
        self.timer_label.config(text=self.format_time(self.elapsed_seconds))
        total_minutes = self.elapsed_seconds // 60
        self.stats_label.config(text=f"Today: {total_minutes} min")
    
    def update_app_list(self):
        self.app_listbox.delete(0, tk.END)
        for app in self.tracked_apps:
            self.app_listbox.insert(tk.END, app)
    
    def refresh_running_apps(self):
        workspace = NSWorkspace.sharedWorkspace()
        running_apps = workspace.runningApplications()
        app_names = []
        for app in running_apps:
            name = app.localizedName()
            if name and name not in ['Python', 'python', 'loginwindow', 'Finder']:
                if not name.startswith('com.apple.'):
                    app_names.append(name)
        app_names = sorted(set(app_names))
        self.running_apps_combo['values'] = app_names
        if app_names:
            self.running_apps_combo.current(0)
    
    def add_from_running_apps(self):
        selected_app = self.running_apps_var.get().strip()
        if not selected_app: return
        if selected_app in self.tracked_apps: return
        self.tracked_apps.append(selected_app)
        self.update_app_list()
        self.save_config()
    
    def add_manual_app(self):
        app_name = self.app_entry_var.get().strip()
        if not app_name or app_name == self.app_entry.placeholder: return
        if app_name in self.tracked_apps: return
        self.tracked_apps.append(app_name)
        self.update_app_list()
        self.app_entry_var.set("")
        self.app_entry.insert(0, self.app_entry.placeholder)
        self.app_entry.config(fg='#999999')
        self.app_entry.placeholder_active = True
        self.save_config()
    
    def remove_selected_app(self):
        selection = self.app_listbox.curselection()
        if not selection: return
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
            session_dict = CGSessionCopyCurrentDictionary()
            if session_dict and session_dict.get("CGSSessionScreenIsLocked", False): return False
            idle_time = CGEventSourceSecondsSinceLastEventType(kCGEventSourceStateHIDSystemState, kCGAnyInputEventType)
            return idle_time < self.idle_threshold
        except: return True
    
    def is_tracked_app_active(self):
        if not self.tracked_apps: return False, None
        workspace = NSWorkspace.sharedWorkspace()
        active_app = workspace.activeApplication()
        active_name = active_app['NSApplicationName']
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
                        color_code, color_name = self.color_list[self.current_color_index]
                        self.root.after(0, lambda: self.status_label.config(text="▶ 집중 중", foreground=color_code))
                        self.root.after(0, lambda n=active_app_name: self.current_app_label.config(text=n))
                    
                    if current_time - last_update >= 1.0:
                        self.elapsed_seconds += 1
                        self.root.after(0, self.update_timer_display)
                        last_update = current_time
                else:
                    if self.is_running:
                        self.is_running = False
                        self.last_active_app = ""
                        msg = "⏸ 자리 비움" if not user_active else "⏸ 딴짓 중..."
                        self.root.after(0, lambda m=msg: self.status_label.config(text=m, foreground='#757575'))
                        self.root.after(0, lambda: self.current_app_label.config(text=""))
                
                if int(current_time) % 10 == 0: self.root.after(0, self.save_config)
                time.sleep(0.5)
            except: time.sleep(1)
    
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
                    self.current_color_index = config.get('color_index', 0)
            except: pass
    
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
        except: pass
    
    def on_closing(self):
        self.stop_monitoring = True
        self.save_config()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = WorkTimer(root)
    root.mainloop()

if __name__ == "__main__":
    main()