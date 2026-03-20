import sys
import os
import time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import threading
import subprocess
import tempfile
from datetime import datetime

# Глобальный импорт moviepy
try:
    from moviepy import ImageClip, VideoFileClip
    from moviepy.video.fx import Resize
    MOVIEPY_AVAILABLE = True
    print("✅ MoviePy доступен")
except ImportError as e:
    MOVIEPY_AVAILABLE = False
    print(f"⚠️ MoviePy не установлен: {e}")

# Проверка FFMPEG
FFMPEG_AVAILABLE = False
if MOVIEPY_AVAILABLE:
    try:
        import imageio_ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        FFMPEG_AVAILABLE = True
        print(f"✅ FFMPEG найден: {ffmpeg_path}")
    except:
        print("⚠️ FFMPEG не найден")

# Проверка PIL
try:
    from PIL import Image
    PIL_AVAILABLE = True
    print("✅ PIL (Pillow) доступен")
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️ PIL не установлен")

# Конфигурация приложения
VERSION = "4.3.0"  # Обновлена версия
DURATION = 10
FPS = 24

# Поддерживаемые форматы
IMAGE_OUTPUT_FORMATS = ["png", "jpg", "webp", "bmp", "tiff", "ico"]
VIDEO_OUTPUT_FORMATS = ["mp4", "avi", "mov", "mkv", "webm", "gif"]

# Цветовая схема
COLORS = {
    'bg': '#f0f0f0',
    'header': '#2c3e50',
    'status': '#ecf0f1',
    'footer': '#bdc3c7',
    'section1': '#e8f4f8',
    'section2': '#d1ecf1',
    'section3': '#fff3cd',
    'section4': '#d4edda',
    'success': '#27ae60',
    'warning': '#e67e22',
    'info': '#3498db',
    'about': '#95a5a6',
    'log': '#f8f9fa'
}

# Класс для управления логами
class Logger:
    def __init__(self):
        self.logs = []
        self.log_window = None
        self.log_text = None
        self.log_file = None
        self.setup_log_file()
    
    def setup_log_file(self):
        """Создание файла для логов"""
        try:
            log_dir = os.path.join(os.path.expanduser("~"), "VideoMakerPro_Logs")
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            log_filename = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            self.log_file = os.path.join(log_dir, log_filename)
            
            # Записываем заголовок
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write(f"=== Video Maker Pro v{VERSION} Лог ===\n")
                f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*50 + "\n\n")
        except:
            self.log_file = None
    
    def add(self, message, level="INFO"):
        """Добавление записи в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Эмодзи для разных уровней
        emoji = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "PROCESS": "🔄",
            "COMPLETE": "🎉"
        }.get(level, "📝")
        
        log_entry = f"[{timestamp}] {emoji} {message}"
        
        # Добавляем в память
        self.logs.append({
            'time': timestamp,
            'level': level,
            'message': message,
            'full': log_entry
        })
        
        # Выводим в консоль
        print(log_entry)
        
        # Записываем в файл
        if self.log_file:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry + "\n")
            except:
                pass
        
        # Обновляем окно логов если открыто
        self.update_log_window()
    
    def update_log_window(self):
        """Обновление окна логов"""
        if self.log_window and self.log_text:
            try:
                self.log_text.delete(1.0, tk.END)
                for log in self.logs[-100:]:  # Показываем последние 100 записей
                    self.log_text.insert(tk.END, log['full'] + "\n")
                self.log_text.see(tk.END)
            except:
                pass
    
    def show_window(self, parent):
        """Показать окно с логами"""
        if self.log_window:
            try:
                self.log_window.lift()
                return
            except:
                self.log_window = None
        
        self.log_window = tk.Toplevel(parent)
        self.log_window.title("📋 Логи программы")
        self.log_window.geometry("700x500")
        self.log_window.resizable(True, True)
        
        # Верхняя панель
        header = tk.Frame(self.log_window, bg=COLORS['header'], height=40)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(header, text="📋 Журнал событий", font=("Segoe UI", 12, "bold"),
                bg=COLORS['header'], fg="white").pack(expand=True)
        
        # Панель инструментов
        toolbar = tk.Frame(self.log_window, bg=COLORS['status'], height=35)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)
        
        # Кнопки управления
        tk.Button(toolbar, text="🔄 Обновить", font=("Segoe UI", 9),
                 bg=COLORS['info'], fg="white", relief="flat",
                 command=self.update_log_window).pack(side="left", padx=5, pady=3)
        
        tk.Button(toolbar, text="🗑️ Очистить", font=("Segoe UI", 9),
                 bg=COLORS['warning'], fg="white", relief="flat",
                 command=self.clear_logs).pack(side="left", padx=5, pady=3)
        
        tk.Button(toolbar, text="💾 Сохранить", font=("Segoe UI", 9),
                 bg=COLORS['success'], fg="white", relief="flat",
                 command=self.save_logs).pack(side="left", padx=5, pady=3)
        
        tk.Button(toolbar, text="📂 Открыть папку", font=("Segoe UI", 9),
                 bg=COLORS['about'], fg="white", relief="flat",
                 command=self.open_log_folder).pack(side="left", padx=5, pady=3)
        
        # Фильтры
        tk.Label(toolbar, text="Фильтр:", font=("Segoe UI", 9),
                bg=COLORS['status']).pack(side="left", padx=(20,5))
        
        self.filter_var = tk.StringVar(value="Все")
        filter_menu = ttk.Combobox(toolbar, textvariable=self.filter_var,
                                   values=["Все", "INFO", "SUCCESS", "WARNING", "ERROR", "PROCESS"],
                                   width=10, state="readonly")
        filter_menu.pack(side="left", padx=5)
        filter_menu.bind('<<ComboboxSelected>>', lambda e: self.apply_filter())
        
        # Текстовое поле с логами
        text_frame = tk.Frame(self.log_window)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD,
                                                  font=("Consolas", 9),
                                                  bg=COLORS['log'],
                                                  fg="#2c3e50")
        self.log_text.pack(fill="both", expand=True)
        
        # Нижняя панель
        footer = tk.Frame(self.log_window, bg=COLORS['footer'], height=25)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        
        total_logs = len(self.logs)
        tk.Label(footer, text=f"Всего записей: {total_logs} | Файл: {os.path.basename(self.log_file) if self.log_file else 'нет'}",
                font=("Segoe UI", 8), bg=COLORS['footer'], fg="#2c3e50").pack(expand=True)
        
        # Заполняем логами
        self.update_log_window()
    
    def apply_filter(self):
        """Применить фильтр к логам"""
        filter_by = self.filter_var.get()
        
        if self.log_text:
            self.log_text.delete(1.0, tk.END)
            
            for log in self.logs:
                if filter_by == "Все" or log['level'] == filter_by:
                    self.log_text.insert(tk.END, log['full'] + "\n")
            
            self.log_text.see(tk.END)
    
    def clear_logs(self):
        """Очистить логи"""
        if messagebox.askyesno("Подтверждение", "Очистить все логи?"):
            self.logs = []
            if self.log_text:
                self.log_text.delete(1.0, tk.END)
            self.add("Логи очищены", "INFO")
    
    def save_logs(self):
        """Сохранить логи в файл"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=f"videolog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"=== Video Maker Pro v{VERSION} Лог ===\n")
                    f.write(f"Дата экспорта: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("="*50 + "\n\n")
                    
                    for log in self.logs:
                        f.write(log['full'] + "\n")
                
                self.add(f"Логи сохранены в {filename}", "SUCCESS")
                messagebox.showinfo("Успех", f"Логи сохранены в:\n{filename}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить логи: {e}")
    
    def open_log_folder(self):
        """Открыть папку с логами"""
        try:
            log_dir = os.path.join(os.path.expanduser("~"), "VideoMakerPro_Logs")
            if os.path.exists(log_dir):
                os.startfile(log_dir)
            else:
                messagebox.showinfo("Информация", "Папка с логами еще не создана")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку: {e}")

class VideoMakerPro:
    """Главный класс приложения"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"Video Maker Pro v{VERSION}")
        self.root.geometry("900x800")  # Увеличен начальный размер
        self.root.minsize(800, 600)    # Минимальный размер
        self.root.configure(bg=COLORS['bg'])
        
        self.center_window()
        self.setup_styles()
        
        # Инициализация логгера
        self.logger = Logger()
        self.logger.add("Программа запущена", "INFO")
        self.logger.add(f"Версия: {VERSION}", "INFO")
        self.logger.add(f"PIL: {'Доступен' if PIL_AVAILABLE else 'Не установлен'}", "INFO")
        self.logger.add(f"MoviePy: {'Доступен' if MOVIEPY_AVAILABLE else 'Не установлен'}", "INFO")
        self.logger.add(f"FFMPEG: {'Доступен' if FFMPEG_AVAILABLE else 'Не найден'}", "WARNING" if not FFMPEG_AVAILABLE else "INFO")
        
        self.current_mode = None
        self.video_ext = None
        self.cancel_flag = False
        self.progress_win = None
        self.temp_dir = tempfile.mkdtemp(prefix="video_maker_")
        self.logger.add(f"Временная папка: {self.temp_dir}", "INFO")
        
        # Переменные для хранения значений
        self.convert_format_var = tk.StringVar(value="png")
        self.quality_var = tk.StringVar(value="95")
        self.ico_size_var = tk.StringVar(value="256")
        self.video_conv_format_var = tk.StringVar(value="mp4")
        self.video_quality_var = tk.StringVar(value="medium")
        
        self.setup_menu()  # Добавляем меню
        self.setup_ui()

    def center_window(self):
        """Центрирование окна на экране"""
        self.root.update_idletasks()
        width, height = 900, 800
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def setup_menu(self):
        """Создание меню программы"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Меню Файл
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="📁 Файл", menu=file_menu)
        file_menu.add_command(label="📂 Выбрать фото", command=lambda: self.select_files("photo"))
        file_menu.add_command(label="🎬 Выбрать видео", command=lambda: self.select_files("video"))
        file_menu.add_separator()
        file_menu.add_command(label="📁 Выбрать папку", command=self.select_output_directory)
        file_menu.add_separator()
        file_menu.add_command(label="❌ Выход", command=self.root.quit)
        
        # Меню Вид
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="👁️ Вид", menu=view_menu)
        
        # Подменю размеров окна
        size_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="📏 Размер окна", menu=size_menu)
        
        # Предустановленные размеры
        size_menu.add_command(label="Маленький (800x600)", 
                             command=lambda: self.set_window_size(800, 600))
        size_menu.add_command(label="Средний (900x700)", 
                             command=lambda: self.set_window_size(900, 700))
        size_menu.add_command(label="Большой (1024x768)", 
                             command=lambda: self.set_window_size(1024, 768))
        size_menu.add_command(label="Очень большой (1280x960)", 
                             command=lambda: self.set_window_size(1280, 960))
        size_menu.add_separator()
        size_menu.add_command(label="На весь экран", command=self.toggle_fullscreen)
        
        view_menu.add_separator()
        view_menu.add_command(label="📋 Показать логи", command=self.show_logs)
        view_menu.add_command(label="🔄 Обновить интерфейс", command=self.refresh_ui)
        
        # Меню Инструменты
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="🛠️ Инструменты", menu=tools_menu)
        tools_menu.add_command(label="📦 Установить зависимости", command=self.install_dependencies)
        tools_menu.add_command(label="🎬 Скачать VLC", command=self.install_vlc)
        tools_menu.add_separator()
        tools_menu.add_command(label="🧹 Очистить временные файлы", command=self.clean_temp_files)
        
        # Меню Помощь
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="❓ Помощь", menu=help_menu)
        help_menu.add_command(label="ℹ️ О программе", command=self.show_info)
        help_menu.add_command(label="📖 Инструкция", command=self.show_help)
        help_menu.add_separator()
        help_menu.add_command(label="🐛 Сообщить об ошибке", command=self.report_bug)
    
    def set_window_size(self, width, height):
        """Установка размера окна"""
        self.root.geometry(f"{width}x{height}")
        self.logger.add(f"Размер окна изменен на {width}x{height}", "INFO")
    
    def toggle_fullscreen(self):
        """Переключение полноэкранного режима"""
        self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen"))
        self.logger.add("Режим полного экрана " + ("включен" if self.root.attributes("-fullscreen") else "выключен"), "INFO")
    
    def refresh_ui(self):
        """Обновление интерфейса"""
        self.logger.add("Обновление интерфейса", "INFO")
        # Перестраиваем UI
        for widget in self.root.winfo_children():
            widget.destroy()
        self.setup_menu()
        self.setup_ui()
    
    def clean_temp_files(self):
        """Очистка временных файлов"""
        try:
            count = 0
            for file in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    count += 1
            self.logger.add(f"Очищено временных файлов: {count}", "SUCCESS")
            messagebox.showinfo("Очистка", f"Удалено {count} временных файлов")
        except Exception as e:
            self.logger.add(f"Ошибка при очистке: {e}", "ERROR")
            messagebox.showerror("Ошибка", f"Не удалось очистить временные файлы: {e}")
    
    def show_help(self):
        """Показать инструкцию"""
        help_text = """📖 ИНСТРУКЦИЯ ПО ИСПОЛЬЗОВАНИЮ

📷 РАЗДЕЛ 1: КОНВЕРТЕР ФОТО
1. Выберите формат (PNG, JPG, WEBP, BMP, TIFF, ICO)
2. Установите качество (для JPG)
3. Для ICO выберите размер
4. Нажмите "Конвертировать фото"
5. Выберите файлы и папку

🎬 РАЗДЕЛ 2: КОНВЕРТЕР ВИДЕО
1. Выберите выходной формат
2. Установите качество
3. Нажмите "Конвертировать видео"
4. Выберите видео файлы и папку

🎥 РАЗДЕЛ 3: СОЗДАТЕЛЬ ВИДЕО
1. Нажмите на нужный формат (MP4, AVI, MOV)
2. Выберите фото
3. Укажите папку для сохранения
4. Видео создастся автоматически

🔧 РАЗДЕЛ 4: ДОПОЛНИТЕЛЬНО
• Установка зависимостей
• Скачивание VLC
• Просмотр логов

⌨️ ГОРЯЧИЕ КЛАВИШИ:
• Ctrl+O - выбрать фото
• Ctrl+Shift+O - выбрать видео
• Ctrl+S - выбрать папку
• Ctrl+L - открыть логи
• F11 - полный экран
• Esc - выход из полного экрана

📋 СОВЕТЫ:
• Используйте MP4 для лучшей совместимости
• Проверяйте логи при ошибках
• Регулярно очищайте временные файлы
"""
        messagebox.showinfo("Инструкция", help_text)
    
    def report_bug(self):
        """Сообщить об ошибке"""
        bug_window = tk.Toplevel(self.root)
        bug_window.title("🐛 Сообщить об ошибке")
        bug_window.geometry("500x400")
        
        tk.Label(bug_window, text="Опишите проблему:", font=("Segoe UI", 10)).pack(pady=10)
        
        text_area = tk.Text(bug_window, height=10, font=("Segoe UI", 9))
        text_area.pack(padx=10, pady=5, fill="both", expand=True)
        
        # Добавляем информацию из логов
        log_info = "\n\n--- ЛОГИ ---\n"
        for log in self.logger.logs[-20:]:
            log_info += log['full'] + "\n"
        text_area.insert(tk.END, log_info)
        
        def send_report():
            # Копируем в буфер обмена
            bug_window.clipboard_clear()
            bug_window.clipboard_append(text_area.get(1.0, tk.END))
            messagebox.showinfo("Готово", "Текст ошибки скопирован в буфер обмена!\nОтправьте его разработчику.")
            bug_window.destroy()
        
        tk.Button(bug_window, text="📋 Копировать и закрыть", 
                 command=send_report, bg=COLORS['success'], fg="white").pack(pady=10)

    def setup_styles(self):
        """Настройка стилей интерфейса"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.style.configure("TButton", 
                           font=("Segoe UI", 10, "bold"),
                           padding=10,
                           background=COLORS['info'],
                           foreground="white",
                           borderwidth=0)

    def create_section(self, parent, title, bg_color, fg_color):
        """Создание секции"""
        frame = tk.Frame(parent, bg=bg_color, relief="solid", bd=2)
        frame.pack(fill="x", pady=10, ipady=10, padx=10)
        
        tk.Label(frame, text=title, font=("Segoe UI", 12, "bold"),
                bg=bg_color, fg=fg_color).pack(anchor="w", padx=10, pady=5)
        
        return frame

    def create_button(self, parent, text, color, command, state=True, width=None):
        """Создание кнопки"""
        return tk.Button(parent, text=text, font=("Segoe UI", 11, "bold"),
                        bg=color, fg="white", relief="flat", cursor="hand2",
                        state="normal" if state else "disabled",
                        command=command, width=width)

    def setup_ui(self):
        """Создание пользовательского интерфейса"""
        # Верхняя панель
        header_frame = tk.Frame(self.root, bg=COLORS['header'], height=80)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="🎬 Video Maker Pro", 
                font=("Segoe UI", 18, "bold"), bg=COLORS['header'], fg="white").pack(expand=True)
        tk.Label(header_frame, text="Конвертер фото, видео и создатель видео",
                font=("Segoe UI", 10), bg=COLORS['header'], fg="#bdc3c7").pack()
        
        # Панель статуса
        status_frame = tk.Frame(self.root, bg=COLORS['status'], height=60)
        status_frame.pack(fill="x")
        status_frame.pack_propagate(False)
        
        status_text = f"PIL: {'✅' if PIL_AVAILABLE else '❌'} | MoviePy: {'✅' if MOVIEPY_AVAILABLE else '❌'} | FFMPEG: {'✅' if FFMPEG_AVAILABLE else '⚠️'}"
        tk.Label(status_frame, text=status_text, font=("Segoe UI", 10),
                bg=COLORS['status'], fg="#34495e").pack(anchor="w", padx=10, pady=10)
        
        # Область с прокруткой
        canvas = tk.Canvas(self.root, bg=COLORS['bg'], highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=COLORS['bg'])
        
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=(20,0))
        scrollbar.pack(side="right", fill="y")
        
        # ===== РАЗДЕЛ 1: КОНВЕРТЕР ФОТО =====
        section1 = self.create_section(scrollable, "📷 РАЗДЕЛ 1: КОНВЕРТЕР ФОТО", 
                                      COLORS['section1'], "#0c5460")
        
        # Формат
        frame1 = tk.Frame(section1, bg=COLORS['section1'])
        frame1.pack(fill="x", padx=10, pady=5)
        
        tk.Label(frame1, text="Формат:", font=("Segoe UI", 10), 
                bg=COLORS['section1']).pack(side="left")
        ttk.Combobox(frame1, textvariable=self.convert_format_var,
                    values=IMAGE_OUTPUT_FORMATS, width=10, 
                    state="readonly").pack(side="left", padx=10)
        
        tk.Label(frame1, text="Качество:", font=("Segoe UI", 10),
                bg=COLORS['section1']).pack(side="left", padx=(20,5))
        tk.Spinbox(frame1, from_=1, to=100, textvariable=self.quality_var,
                  width=5).pack(side="left")
        
        # Размер ICO
        frame2 = tk.Frame(section1, bg=COLORS['section1'])
        frame2.pack(fill="x", padx=10, pady=5)
        
        tk.Label(frame2, text="Размер ICO:", font=("Segoe UI", 10),
                bg=COLORS['section1']).pack(side="left")
        ttk.Combobox(frame2, textvariable=self.ico_size_var,
                    values=["16","32","48","64","128","256"], 
                    width=5, state="readonly").pack(side="left", padx=10)
        
        # Кнопка
        self.create_button(section1, "🔄 Конвертировать фото", COLORS['success'],
                          self.start_converter, PIL_AVAILABLE).pack(fill="x", padx=10, pady=10, ipady=8)
        
        # ===== РАЗДЕЛ 2: КОНВЕРТЕР ВИДЕО =====
        section2 = self.create_section(scrollable, "🎬 РАЗДЕЛ 2: КОНВЕРТЕР ВИДЕО",
                                      COLORS['section2'], "#0c5460")
        
        tk.Label(section2, text="Конвертировать видео в другой формат",
                font=("Segoe UI", 10), bg=COLORS['section2'], 
                fg="#0c5460").pack(anchor="w", padx=10)
        
        # Формат
        frame3 = tk.Frame(section2, bg=COLORS['section2'])
        frame3.pack(fill="x", padx=10, pady=10)
        
        tk.Label(frame3, text="Выходной формат:", font=("Segoe UI", 10),
                bg=COLORS['section2']).pack(side="left")
        ttk.Combobox(frame3, textvariable=self.video_conv_format_var,
                    values=VIDEO_OUTPUT_FORMATS, width=8,
                    state="readonly").pack(side="left", padx=10)
        
        # Качество
        frame4 = tk.Frame(section2, bg=COLORS['section2'])
        frame4.pack(fill="x", padx=10, pady=5)
        
        tk.Label(frame4, text="Качество:", font=("Segoe UI", 10),
                bg=COLORS['section2']).pack(side="left")
        
        qualities = [("Низкое", "low"), ("Среднее", "medium"), ("Высокое", "high")]
        for text, val in qualities:
            tk.Radiobutton(frame4, text=text, variable=self.video_quality_var,
                          value=val, bg=COLORS['section2'],
                          font=("Segoe UI", 8)).pack(side="left", padx=2)
        
        # Кнопка
        self.create_button(section2, "🔄 Конвертировать видео", "#17a2b8",
                          self.start_video_converter, MOVIEPY_AVAILABLE).pack(fill="x", padx=10, pady=10, ipady=8)
        
        # ===== РАЗДЕЛ 3: СОЗДАТЕЛЬ ВИДЕО =====
        section3 = self.create_section(scrollable, "🎥 РАЗДЕЛ 3: СОЗДАТЕЛЬ ВИДЕО",
                                      COLORS['section3'], "#856404")
        
        tk.Label(section3, text="Создать 10-секундное видео из фото",
                font=("Segoe UI", 10), bg=COLORS['section3'],
                fg="#856404").pack(anchor="w", padx=10)
        
        # Кнопки форматов
        frame5 = tk.Frame(section3, bg=COLORS['section3'])
        frame5.pack(fill="x", padx=10, pady=10)
        
        video_formats = [("📹 MP4", "mp4", COLORS['success']),
                        ("🎥 AVI", "avi", COLORS['warning']),
                        ("🍎 MOV", "mov", COLORS['info'])]
        
        for text, val, color in video_formats:
            btn = tk.Button(frame5, text=text, font=("Segoe UI", 10, "bold"),
                          bg=color, fg="white", relief="flat", cursor="hand2",
                          state="normal" if MOVIEPY_AVAILABLE else "disabled",
                          command=lambda v=val: self.start_video_creator(v))
            btn.pack(side="left", padx=5, expand=True, fill="x", ipady=5)
        
        # ===== РАЗДЕЛ 4: ДОПОЛНИТЕЛЬНО =====
        section4 = self.create_section(scrollable, "🔧 ДОПОЛНИТЕЛЬНО",
                                      COLORS['section4'], "#155724")
        
        frame6 = tk.Frame(section4, bg=COLORS['section4'])
        frame6.pack(fill="x", padx=10, pady=10)
        
        tools = [
            ("📦 Установить зависимости", COLORS['info'], self.install_dependencies),
            ("🎬 Скачать VLC", COLORS['warning'], self.install_vlc),
            ("ℹ️ Информация", COLORS['about'], self.show_info),
            ("📋 Просмотр логов", COLORS['success'], self.show_logs)
        ]
        
        for text, color, cmd in tools:
            self.create_button(frame6, text, color, cmd).pack(side="left", padx=5, expand=True, fill="x", ipady=5)
        
        # Нижняя панель
        footer_frame = tk.Frame(self.root, bg=COLORS['footer'], height=30)
        footer_frame.pack(fill="x", side="bottom")
        footer_frame.pack_propagate(False)
        
        footer_text = f"Версия {VERSION} | 1.Фото | 2.Конвертер видео | 3.Создатель видео | 4.Инструменты | Меню для изменения размера"
        tk.Label(footer_frame, text=footer_text, font=("Segoe UI", 8),
                bg=COLORS['footer'], fg="#2c3e50").pack(expand=True)

    # === МЕТОДЫ ДЛЯ КОНВЕРТЕРА ФОТО ===
    def start_converter(self):
        if not PIL_AVAILABLE:
            self.logger.add("Попытка запуска конвертера фото без PIL", "ERROR")
            messagebox.showerror("Ошибка", "PIL (Pillow) не установлен!")
            return
            
        self.current_mode = "converter"
        self.root.withdraw()
        self.cancel_flag = False
        self.logger.add("Запуск конвертера фото", "PROCESS")
        threading.Thread(target=self.process_converter, daemon=True).start()
    
    def process_converter(self):
        try:
            files = self.select_files("photo")
            if not files: 
                self.logger.add("Конвертер фото: файлы не выбраны", "WARNING")
                return self.show_warning("Файлы не выбраны!")

            out_dir = self.select_output_directory()
            if not out_dir: 
                self.logger.add("Конвертер фото: папка не выбрана", "WARNING")
                return self.show_warning("Папка не выбрана!")

            self.logger.add(f"Конвертер фото: выбрано {len(files)} файлов", "INFO")
            self.convert_images(files, out_dir)
        except Exception as e:
            self.logger.add(f"Ошибка в конвертере фото: {str(e)}", "ERROR")
            self.show_error(f"Ошибка: {str(e)}")
        finally:
            if not self.cancel_flag: self.cleanup()
    
    def convert_images(self, files, out_dir):
        target = self.convert_format_var.get()
        quality = int(self.quality_var.get())
        ico_size = int(self.ico_size_var.get())
        
        self.logger.add(f"Конвертация фото в формат {target.upper()}, качество {quality}%", "PROCESS")
        if target == 'ico':
            self.logger.add(f"Размер ICO: {ico_size}x{ico_size}", "INFO")
        
        self.show_progress_window(len(files))
        success, failed = 0, 0

        for i, path in enumerate(files, 1):
            if self.cancel_flag: 
                self.logger.add("Конвертация фото прервана пользователем", "WARNING")
                break
            try:
                name = Path(path).stem
                out = os.path.join(out_dir, f"{name}.{target}")
                
                with Image.open(path) as img:
                    if target in ['jpg', 'jpeg'] and img.mode in ['RGBA', 'P']:
                        img = img.convert('RGB')
                    
                    if target == 'ico':
                        img.save(out, format='ICO', sizes=[(ico_size, ico_size)])
                    elif target in ['jpg', 'jpeg']:
                        img.save(out, quality=quality, optimize=True)
                    else:
                        img.save(out)
                
                success += 1
                self.update_progress(i, len(files), f"✓ {name}.{target}")
            except Exception as e:
                failed += 1
                self.logger.add(f"Ошибка при конвертации {Path(path).name}: {str(e)}", "ERROR")
                self.update_progress(i, len(files), f"✗ {Path(path).name}")

        self.logger.add(f"Конвертация фото завершена: успешно {success}, ошибок {failed}", 
                       "SUCCESS" if failed == 0 else "WARNING")

        if not self.cancel_flag:
            self.show_result("Конвертация фото завершена", success, failed, out_dir)

    # === МЕТОДЫ ДЛЯ КОНВЕРТЕРА ВИДЕО ===
    def start_video_converter(self):
        if not MOVIEPY_AVAILABLE:
            self.logger.add("Попытка запуска конвертера видео без MoviePy", "ERROR")
            messagebox.showerror("Ошибка", "MoviePy не установлен!")
            return
            
        self.current_mode = "video_converter"
        self.root.withdraw()
        self.cancel_flag = False
        self.logger.add("Запуск конвертера видео", "PROCESS")
        threading.Thread(target=self.process_video_converter, daemon=True).start()
    
    def process_video_converter(self):
        try:
            files = self.select_files("video")
            if not files: 
                self.logger.add("Конвертер видео: файлы не выбраны", "WARNING")
                return self.show_warning("Файлы не выбраны!")

            out_dir = self.select_output_directory()
            if not out_dir: 
                self.logger.add("Конвертер видео: папка не выбрана", "WARNING")
                return self.show_warning("Папка не выбрана!")

            self.logger.add(f"Конвертер видео: выбрано {len(files)} файлов", "INFO")
            self.convert_videos(files, out_dir)
        except Exception as e:
            self.logger.add(f"Ошибка в конвертере видео: {str(e)}", "ERROR")
            self.show_error(f"Ошибка: {str(e)}")
        finally:
            if not self.cancel_flag: self.cleanup()
    
    def convert_videos(self, files, out_dir):
        target = self.video_conv_format_var.get()
        quality = self.video_quality_var.get()
        
        q_settings = {'low': {'bitrate': '500k', 'preset': 'ultrafast'},
                     'medium': {'bitrate': '1000k', 'preset': 'medium'},
                     'high': {'bitrate': '2000k', 'preset': 'slow'}}
        q_config = q_settings.get(quality, q_settings['medium'])
        
        self.logger.add(f"Конвертация видео в формат {target.upper()}, качество {quality}", "PROCESS")
        
        self.show_progress_window(len(files))
        success, failed = 0, 0

        for i, path in enumerate(files, 1):
            if self.cancel_flag: 
                self.logger.add("Конвертация видео прервана пользователем", "WARNING")
                break
            try:
                name = Path(path).stem
                out = os.path.join(out_dir, f"{name}.{target}")
                
                with VideoFileClip(path) as video:
                    self.logger.add(f"Обработка {name}. Длительность: {video.duration:.1f}с", "INFO")
                    
                    if target == 'gif':
                        video.write_gif(out, fps=10, program='ffmpeg', opt='optimizeplus')
                    else:
                        codec = {'mp4':'libx264','avi':'libx264','mov':'libx264',
                                'mkv':'libx264','webm':'libvpx'}.get(target, 'libx264')
                        
                        video.write_videofile(out, codec=codec, audio_codec='aac',
                                             bitrate=q_config['bitrate'],
                                             preset=q_config['preset'], logger=None)
                
                success += 1
                self.update_progress(i, len(files), f"✓ {name}.{target}")
            except Exception as e:
                failed += 1
                self.logger.add(f"Ошибка при конвертации {Path(path).name}: {str(e)}", "ERROR")
                self.update_progress(i, len(files), f"✗ {Path(path).name}")

        self.logger.add(f"Конвертация видео завершена: успешно {success}, ошибок {failed}", 
                       "SUCCESS" if failed == 0 else "WARNING")

        if not self.cancel_flag:
            self.show_result("Конвертация видео завершена", success, failed, out_dir)

    # === МЕТОДЫ ДЛЯ СОЗДАТЕЛЯ ВИДЕО ===
    def fix_image_size(self, image_path):
        """Исправление размеров изображения для видео (делает размеры четными)"""
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                
                # Проверяем, нужно ли изменять размер
                if width % 2 != 0 or height % 2 != 0:
                    new_width = width if width % 2 == 0 else width + 1
                    new_height = height if height % 2 == 0 else height + 1
                    
                    self.logger.add(f"Исправление размера: {width}x{height} -> {new_width}x{new_height}", "INFO")
                    
                    # Создаем временный файл с исправленным размером
                    temp_filename = f"fixed_{Path(image_path).stem}_{int(time.time())}.png"
                    temp_path = os.path.join(self.temp_dir, temp_filename)
                    
                    # Изменяем размер изображения
                    img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    img_resized.save(temp_path, format='PNG')
                    
                    return temp_path
                else:
                    return image_path
        except Exception as e:
            self.logger.add(f"Ошибка при исправлении размера: {e}", "WARNING")
            return image_path

    def start_video_creator(self, fmt):
        if not MOVIEPY_AVAILABLE:
            self.logger.add("Попытка запуска создателя видео без MoviePy", "ERROR")
            messagebox.showerror("Ошибка", "MoviePy не установлен!")
            return
            
        self.current_mode = "video_creator"
        self.video_ext = fmt
        self.root.withdraw()
        self.cancel_flag = False
        self.logger.add(f"Запуск создателя видео, формат {fmt.upper()}", "PROCESS")
        threading.Thread(target=self.process_video_creator, daemon=True).start()
    
    def process_video_creator(self):
        try:
            files = self.select_files("photo")
            if not files: 
                self.logger.add("Создатель видео: файлы не выбраны", "WARNING")
                return self.show_warning("Файлы не выбраны!")

            out_dir = self.select_output_directory()
            if not out_dir: 
                self.logger.add("Создатель видео: папка не выбрана", "WARNING")
                return self.show_warning("Папка не выбрана!")

            self.logger.add(f"Создатель видео: выбрано {len(files)} файлов", "INFO")
            self.create_videos(files, out_dir)
        except Exception as e:
            self.logger.add(f"Ошибка в создателе видео: {str(e)}", "ERROR")
            self.show_error(f"Ошибка: {str(e)}")
        finally:
            if not self.cancel_flag: 
                self.cleanup()
    
    def create_videos(self, files, out_dir):
        self.show_progress_window(len(files))
        success, failed = 0, 0
        temp_files = []  # Для отслеживания временных файлов

        for i, path in enumerate(files, 1):
            if self.cancel_flag: 
                self.logger.add("Создание видео прервано пользователем", "WARNING")
                break
            try:
                name = Path(path).stem
                out = os.path.join(out_dir, f"{name}.{self.video_ext}")
                
                # Исправляем размер изображения если нужно
                working_path = self.fix_image_size(path)
                if working_path != path:
                    temp_files.append(working_path)
                
                # Создаем видео
                with ImageClip(working_path).with_duration(DURATION) as clip:
                    clip.fps = FPS
                    # Добавляем дополнительные параметры FFMPEG для совместимости
                    clip.write_videofile(
                        out, 
                        codec='libx264', 
                        audio=False,
                        logger=None, 
                        ffmpeg_params=[
                            "-pix_fmt", "yuv420p",
                            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2"  # Принудительно делаем размеры четными
                        ]
                    )
                
                success += 1
                self.update_progress(i, len(files), f"✓ {name}.{self.video_ext}")
                self.logger.add(f"Создано видео: {name}.{self.video_ext}", "SUCCESS")
                
            except Exception as e:
                failed += 1
                self.logger.add(f"Ошибка при создании видео из {Path(path).name}: {str(e)}", "ERROR")
                self.update_progress(i, len(files), f"✗ {Path(path).name}")

        # Очищаем временные файлы
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass

        self.logger.add(f"Создание видео завершено: успешно {success}, ошибок {failed}", 
                       "SUCCESS" if failed == 0 else "WARNING")

        if not self.cancel_flag:
            self.show_result("Видео созданы", success, failed, out_dir)

    # === ОБЩИЕ МЕТОДЫ ===
    def select_files(self, file_type):
        try:
            if file_type == "photo":
                types = [("Изображения", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.gif *.ico")]
                title = "Выберите фотографии"
            else:
                types = [("Видео", "*.mp4 *.avi *.mov *.mkv *.webm *.flv *.wmv *.m4v")]
                title = "Выберите видео файлы"
            
            files = filedialog.askopenfilenames(title=title, filetypes=types)
            if files:
                self.logger.add(f"Выбрано файлов: {len(files)}", "INFO")
            return files if files else None
        except Exception as e:
            self.logger.add(f"Ошибка при выборе файлов: {str(e)}", "ERROR")
            return None

    def select_output_directory(self):
        try:
            out_dir = filedialog.askdirectory(title="Выберите папку для сохранения")
            if out_dir:
                self.logger.add(f"Выбрана папка: {out_dir}", "INFO")
            return out_dir or None
        except Exception as e:
            self.logger.add(f"Ошибка при выборе папки: {str(e)}", "ERROR")
            return None

    def show_progress_window(self, total):
        self.progress_win = tk.Toplevel(self.root)
        self.progress_win.title("Обработка")
        self.progress_win.geometry("400x150")
        
        self.status_label = tk.Label(self.progress_win, text="Обработка...")
        self.status_label.pack(pady=20)
        
        self.progress_bar = ttk.Progressbar(self.progress_win, length=300,
                                           mode='determinate', maximum=total)
        self.progress_bar.pack(pady=10)
        
        tk.Button(self.progress_win, text="Отмена",
                 command=self.cancel_processing).pack()

    def update_progress(self, current, total, status):
        if self.progress_bar:
            self.progress_bar['value'] = current
        if self.status_label:
            self.status_label.config(text=f"{current}/{total}: {status}")
        self.progress_win.update()

    def cancel_processing(self):
        self.cancel_flag = True
        self.logger.add("Операция отменена пользователем", "WARNING")
        if self.progress_win:
            self.progress_win.destroy()
        self.root.deiconify()

    def show_result(self, title, success, failed, out_dir):
        if self.progress_win:
            self.progress_win.destroy()
        
        msg = f"✅ {title}!\n\nУспешно: {success}\nОшибок: {failed}\n\nПапка: {out_dir}"
        self.logger.add(f"{title}: успешно {success}, ошибок {failed}", 
                       "SUCCESS" if failed == 0 else "WARNING")
        
        if failed == 0:
            messagebox.showinfo("Готово", msg)
        else:
            messagebox.showwarning("Завершено", msg)
        self.cleanup()

    def show_warning(self, msg):
        self.logger.add(msg, "WARNING")
        self.root.deiconify()
        messagebox.showwarning("Внимание", msg)

    def show_error(self, msg):
        self.logger.add(msg, "ERROR")
        self.root.deiconify()
        messagebox.showerror("Ошибка", msg)

    def log_message(self, msg):
        self.logger.add(msg, "INFO")

    def cleanup(self):
        try:
            if self.progress_win:
                self.progress_win.destroy()
            self.root.deiconify()
        except:
            pass

    # === МЕТОДЫ ДЛЯ ЛОГОВ ===
    def show_logs(self):
        """Показать окно с логами"""
        self.logger.show_window(self.root)

    # === ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ===
    def install_dependencies(self):
        try:
            win = tk.Toplevel(self.root)
            win.title("Установка")
            win.geometry("600x400")
            
            tk.Label(win, text="📦 Установка зависимостей",
                    font=("Segoe UI", 12, "bold")).pack(pady=10)
            
            txt = tk.Text(win, height=15, font=("Consolas", 9))
            txt.pack(pady=10, padx=20, fill="both", expand=True)
            
            def append(t):
                txt.insert(tk.END, t + "\n")
                txt.see(tk.END)
                win.update()
            
            def install():
                self.logger.add("Начало установки зависимостей", "PROCESS")
                for pkg in ["pillow", "moviepy", "imageio-ffmpeg"]:
                    append(f"🔄 Установка {pkg}...")
                    self.logger.add(f"Установка {pkg}...", "INFO")
                    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", pkg])
                append("\n✅ Установка завершена! Перезапустите программу.")
                self.logger.add("Установка зависимостей завершена", "SUCCESS")
            
            threading.Thread(target=install, daemon=True).start()
        except Exception as e:
            self.logger.add(f"Ошибка при установке зависимостей: {str(e)}", "ERROR")
            messagebox.showerror("Ошибка", str(e))

    def install_vlc(self):
        import webbrowser
        self.logger.add("Открытие страницы загрузки VLC", "INFO")
        webbrowser.open("https://www.videolan.org/vlc/download-windows.html")

    def show_info(self):
        self.logger.add("Просмотр информации о программе", "INFO")
        info = f"""🎬 Video Maker Pro v{VERSION}

📷 РАЗДЕЛ 1: КОНВЕРТЕР ФОТО
• PNG, JPG, WEBP, BMP, TIFF, ICO

🎬 РАЗДЕЛ 2: КОНВЕРТЕР ВИДЕО
• MP4, AVI, MOV, MKV, WEBM, GIF

🎥 РАЗДЕЛ 3: СОЗДАТЕЛЬ ВИДЕО
• 10 сек видео из фото (MP4, AVI, MOV)
• Автоматическое исправление размеров

📋 НОВОЕ: Просмотр логов
• Все операции записываются
• Фильтрация по типам событий
• Сохранение в файл

📦 Зависимости: PIL, MoviePy, FFMPEG"""
        messagebox.showinfo("О программе", info)

def main():
    print(f"\n{'='*60}")
    print(f"🎬 Video Maker Pro v{VERSION}")
    print(f"{'='*60}")
    print(f"PIL: {'✅' if PIL_AVAILABLE else '❌'}")
    print(f"MoviePy: {'✅' if MOVIEPY_AVAILABLE else '❌'}")
    print(f"FFMPEG: {'✅' if FFMPEG_AVAILABLE else '⚠️'}")
    print(f"{'='*60}\n")
    
    try:
        VideoMakerPro().root.mainloop()
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        input("Нажмите Enter...")

if __name__ == "__main__":
    main()
