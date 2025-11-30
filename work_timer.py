"""
ElePhocus - Work Time Tracker
Copyright (c) 2025 붉은코끼리 (Red Elephant)
Licensed under MIT License with commercial restriction

상업적 이용 또는 앱스토어 배포 시 사전 허가 필요
Contact: [khsx007@naver.com]
"""
import customtkinter as ctk
import tkinter as tk  # 일반 tkinter도 import!
from tkinter import messagebox
import json
import os
from datetime import datetime
from AppKit import NSWorkspace, NSApplication
from Quartz import CGSessionCopyCurrentDictionary, CGEventSourceSecondsSinceLastEventType, kCGEventSourceStateHIDSystemState, kCGAnyInputEventType
import threading
import time

# CustomTkinter 설정
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class WorkTimer:
    def __init__(self, root):
        self.root = root
        self.root.title("ElePhocus")
        
        # 사이즈 설정 (최적화됨!)
        self.compact_height = 170
        self.expanded_height = 500
        
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
        
        # 컬러 테마 (20가지!)
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
        about_text = """ElePhocus

개발자: 붉은코끼리
버전: 0.1.2

작업 시간을 추적하는 
미니멀 타이머 앱입니다."""
        messagebox.showinfo("About ElePhocus", about_text)
    
    def setup_ui(self):
        # 상단 영역
        self.top_frame = ctk.CTkFrame(self.root, corner_radius=10)
        self.top_frame.pack(fill="x", padx=15, pady=15)
        
        # 헤더
        header_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        header_frame.pack(fill='x', padx=10, pady=(5, 0))
        
        date_str = datetime.now().strftime("%m월 %d일")
        # 날짜 앞에 공백 (스페이스 2-3개)
        self.header_label = ctk.CTkLabel(header_frame, text=f"  {date_str}", 
                                          font=("Helvetica", 11, "bold"))
        self.header_label.pack(side="left")
        
        self.settings_btn = ctk.CTkButton(header_frame, text="⚙", width=40, 
                                           command=self.toggle_settings,
                                           font=("Helvetica", 18),
                                           fg_color="transparent",
                                           hover_color=("gray70", "gray30"))
        self.settings_btn.pack(side="right")
        
        # 타이머
        self.timer_label = ctk.CTkLabel(self.top_frame, text="00:00:00", 
                                         font=("Helvetica", 42, "bold"))
        self.timer_label.pack()  # pady 없음!
        
        # 상태
        self.status_label = ctk.CTkLabel(self.top_frame, text="⏸ 대기 중", 
                                          font=("Helvetica", 11))
        self.status_label.pack()  # pady 없음!
        
        # 현재 앱 (접었을 때도 보이게)
        self.current_app_label = ctk.CTkLabel(self.top_frame, text="", 
                                               font=("Helvetica", 10),
                                               height=10)  # 고정 높이!
        self.current_app_label.pack()  # pady 없음!
        
        # 컬러 버튼
        self.color_btn = ctk.CTkButton(self.top_frame, text="🎨 Color", 
                                        command=self.change_color, 
                                        height=35)
        self.color_btn.pack(pady=(5, 10))  # 위 5px 여백만!

        # 설정 영역
        self.settings_container = ctk.CTkFrame(self.root, fg_color="transparent")

        # 설정 내부
        settings_inner = ctk.CTkFrame(self.settings_container, fg_color="transparent")
        settings_inner.pack(fill='both', expand=True, padx=15, pady=(0, 10))

        # 앱 목록
        ctk.CTkLabel(settings_inner, text="추적 대상 앱", 
                     font=("Helvetica", 11, "bold")).pack(anchor='w', pady=(0, 5))
        
        # Listbox로 변경 (선택 가능한 리스트!)
        list_frame = ctk.CTkFrame(settings_inner, fg_color="transparent")
        list_frame.pack(fill='x', pady=(0, 5))
        
        # tkinter Listbox 사용 (선택 가능!)
        self.app_listbox = tk.Listbox(list_frame, height=4,  # 3 → 4 (크기 증가!)
                                       font=("Helvetica", 11),
                                       bg="#2b2b2b", fg="#ffffff",
                                       selectbackground="#4a9eff",
                                       selectforeground="#ffffff",
                                       relief="solid", borderwidth=1,
                                       highlightthickness=0)
        self.app_listbox.pack(fill='x')
        
        btn_frame = ctk.CTkFrame(settings_inner, fg_color="transparent")
        btn_frame.pack(fill='x', pady=(0, 15))
        
        self.remove_btn = ctk.CTkButton(btn_frame, text="선택 삭제", 
                                         command=self.remove_selected_app)
        self.remove_btn.pack(side="left", fill='x', expand=True, padx=(0, 5))
        
        self.clear_btn = ctk.CTkButton(btn_frame, text="전체 비우기", 
                                        command=self.clear_all_apps)
        self.clear_btn.pack(side="left", fill='x', expand=True)

        # 앱 추가
        ctk.CTkLabel(settings_inner, text="앱 추가", 
                     font=("Helvetica", 11, "bold")).pack(anchor='w', pady=(0, 5))
        
        combo_frame = ctk.CTkFrame(settings_inner, fg_color="transparent")
        combo_frame.pack(fill='x', pady=(0, 5))
        
        self.running_apps_var = ctk.StringVar()
        self.running_apps_combo = ctk.CTkComboBox(combo_frame, 
                                                   variable=self.running_apps_var,
                                                   state='readonly', 
                                                   border_width=1)
        self.running_apps_combo.pack(side="left", fill='x', expand=True, padx=(0, 5))
        
        self.refresh_btn = ctk.CTkButton(combo_frame, text="↻", width=50,
                                          command=self.refresh_running_apps,
                                          font=("Helvetica", 16))
        self.refresh_btn.pack(side="left", padx=(0, 5))
        
        self.add_combo_btn = ctk.CTkButton(combo_frame, text="추가", width=80,
                                            command=self.add_from_running_apps)
        self.add_combo_btn.pack(side="left")
        
        # 직접 입력
        entry_frame = ctk.CTkFrame(settings_inner, fg_color="transparent")
        entry_frame.pack(fill='x', pady=(0, 15))
        
        self.app_entry = ctk.CTkEntry(entry_frame, 
                                       placeholder_text="대소문자 정확히 입력",
                                       font=("Helvetica", 11),
                                       border_width=1)
        self.app_entry.pack(side="left", fill='x', expand=True, padx=(0, 5))
        
        self.add_manual_btn = ctk.CTkButton(entry_frame, text="직접 추가", width=80, 
                                             command=self.add_manual_app)
        self.add_manual_btn.pack(side="left")

        # 초기화 버튼
        self.reset_btn = ctk.CTkButton(settings_inner, text="⚠️ 타이머 0으로 초기화", 
                                        command=self.reset_timer)
        self.reset_btn.pack(fill='x', pady=(5, 0))

        self.refresh_running_apps()
        self.update_app_list()
        
        # 초기 컬러 적용
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
        """보색 계열의 밝고 선명한 색상 (레몬/허니 특별 처리)"""
        # 레몬 색상 체크
        if hex_color.upper() == '#F7DC6F':
            return '#00CED1'  # Cyan!
        
        # 허니 색상 체크
        if hex_color.upper() == '#FDCB6E':
            return '#5AADFF'  # 밝은 파랑!
        
        # 나머지 색상은 일반 보색 계산
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        
        # 보색 계산
        comp_r = 255 - r
        comp_g = 255 - g
        comp_b = 255 - b
        
        # 보색 밝기
        comp_brightness = (comp_r * 299 + comp_g * 587 + comp_b * 114) / 1000
        
        # 보색이 어두우면 밝게 조정
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
        
        # 추적중인 앱 색상 = 타이머색
        self.current_app_label.configure(text_color=theme['primary'])
        
        text_color = self.get_text_color(theme['primary'])
        
        self.color_btn.configure(text=f"🎨 {theme['name']}", 
                                 fg_color=theme['primary'],
                                 hover_color=theme['primary'],
                                 text_color=text_color)
        
        self.settings_btn.configure(text_color=theme['primary'])
        
        if hasattr(self, 'remove_btn'):
            self.remove_btn.configure(fg_color=theme['primary'], hover_color=theme['primary'], text_color=text_color)
        if hasattr(self, 'clear_btn'):
            self.clear_btn.configure(fg_color=theme['primary'], hover_color=theme['primary'], text_color=text_color)
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.configure(fg_color=theme['primary'], hover_color=theme['primary'], text_color=text_color)
        if hasattr(self, 'add_combo_btn'):
            self.add_combo_btn.configure(fg_color=theme['primary'], hover_color=theme['primary'], text_color=text_color)
        if hasattr(self, 'add_manual_btn'):
            self.add_manual_btn.configure(fg_color=theme['primary'], hover_color=theme['primary'], text_color=text_color)
        if hasattr(self, 'reset_btn'):
            self.reset_btn.configure(fg_color=theme['primary'], hover_color=theme['primary'], text_color=text_color)
        
        if hasattr(self, 'settings_container'):
            self.settings_container.configure(fg_color="transparent")
        
        # 집중 중 상태일 때 보색 적용
        if self.is_running:
            complementary = self.get_complementary_color(theme['primary'])
            self.status_label.configure(text_color=complementary)

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
        # 선택된 항목 삭제
        selection = self.app_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "삭제할 앱을 선택하세요.")
            return
        index = selection[0]
        self.tracked_apps.pop(index)
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
                        theme = self.color_themes[self.current_color_index]
                        # 집중중 = 보색!
                        complementary = self.get_complementary_color(theme['primary'])
                        self.root.after(0, lambda: self.status_label.configure(text="▶ 집중 중", text_color=complementary))
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
                    loaded_index = config.get('color_index', 0)
                    if loaded_index < len(self.color_themes):
                        self.current_color_index = loaded_index
                    else:
                        self.current_color_index = 0
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
    root = ctk.CTk()
    app = WorkTimer(root)
    root.mainloop()

if __name__ == "__main__":
    main()