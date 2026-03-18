import sys
import os
import time
import importlib.metadata
import importlib.util
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import subprocess
import tempfile
from PIL import Image
import math

# --- РАСШИРЕННАЯ ПРОВЕРКА MOVIEPY ---
print("="*60)
print("🔍 ДИАГНОСТИКА MOVIEPY")
print("="*60)

MOVIEPY_AVAILABLE = False
MOVIEPY_VERSION = None
FFMPEG_AVAILABLE = False

# Проверка через importlib.metadata
try:
    moviepy_version = importlib.metadata.version("moviepy")
    MOVIEPY_AVAILABLE = True
    MOVIEPY_VERSION = moviepy_version
    print(f"✅ MoviePy найден (версия {moviepy_version})")
except importlib.metadata.PackageNotFoundError:
    print("❌ MoviePy не найден в метаданных")
except Exception as e:
    print(f"⚠️ Ошибка при проверке метаданных: {e}")

# Проверка через прямой импорт
try:
    import moviepy
    MOVIEPY_AVAILABLE = True
    if not MOVIEPY_VERSION:
        MOVIEPY_VERSION = getattr(moviepy, "__version__", "неизвестно")
    print(f"✅ MoviePy импортирован (версия {MOVIEPY_VERSION})")
    print(f"   Путь: {moviepy.__file__}")
    
    # Проверка конкретных модулей
    from moviepy import ImageClip
    from moviepy.video.fx import Resize
    print("✅ ImageClip импортирован")
    
    # Проверка FFMPEG
    try:
        import imageio_ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        FFMPEG_AVAILABLE = True
        print(f"✅ FFMPEG найден: {ffmpeg_path}")
    except:
        print("⚠️ imageio_ffmpeg не найден")
        
except ImportError as e:
    print(f"❌ Ошибка импорта MoviePy: {e}")
except Exception as e:
    print(f"⚠️ Другая ошибка: {e}")

# Проверка PIL (всегда доступен)
try:
    from PIL import Image
    PIL_AVAILABLE = True
    print("✅ PIL (Pillow) доступен")
except:
    PIL_AVAILABLE = False
    print("❌ PIL (Pillow) не найден")

print("="*60 + "\n")

# --- ФИКС МЕТАДАННЫХ ДЛЯ EXE ---
if getattr(sys, 'frozen', False):
    orig_ver = importlib.metadata.version
    def patched_ver(pkg):
        return "2.33.0" if pkg == "imageio" else orig_ver(pkg)
    importlib.metadata.version = patched_ver

# Константы
DURATION = 10
FPS = 24
SUPPORTED_FORMATS = ["png", "jpg", "jpeg", "webp", "bmp", "tiff", "gif"]
SUPPORTED_OUTPUT_FORMATS = ["png", "jpg", "webp", "bmp", "tiff"]
MAX_WORKERS = 2
VERSION = "3.1.0"

class VideoMakerPro:
    """Главный класс приложения"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"Video Maker Pro v{VERSION}")
        self.root.geometry("700x750")
        self.root.resizable(False, False)
        self.root.configure(bg="#f0f0f0")
        
        self.center_window()
        self.setup_styles()
        
        self.current_mode = None
        self.video_ext = None
        self.setup_ui()
        
        # Переменные для обработки
        self.progress_win = None
        self.progress_bar = None
        self.status_label = None
        self.cancel_flag = False
        
        # Временная директория
        self.temp_dir = tempfile.mkdtemp(prefix="video_maker_")

    def center_window(self):
        """Центрирование окна на экране"""
        self.root.update_idletasks()
        width, height = 700, 750
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def setup_styles(self):
        """Настройка стилей интерфейса"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.style.configure("TButton", 
                           font=("Segoe UI", 10, "bold"),
                           padding=12,
                           background="#3498db",
                           foreground="white",
                           borderwidth=0,
                           focuscolor="none")
        
        self.style.map("TButton",
                      background=[('active', '#2980b9'),
                                ('pressed', '#21618c')])

    def setup_ui(self):
        """Создание пользовательского интерфейса"""
        # Верхняя панель
        header_frame = tk.Frame(self.root, bg="#2c3e50", height=80)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, 
                text="🎬 Video Maker Pro", 
                font=("Segoe UI", 18, "bold"),
                bg="#2c3e50",
                fg="white").pack(expand=True)
        
        tk.Label(header_frame,
                text="Конвертер фото и создатель видео",
                font=("Segoe UI", 10),
                bg="#2c3e50",
                fg="#bdc3c7").pack()
        
        # Панель диагностики
        diag_frame = tk.Frame(self.root, bg="#ecf0f1", height=80)
        diag_frame.pack(fill="x")
        diag_frame.pack_propagate(False)
        
        # Статус библиотек
        status_text = f"PIL: ✅ | MoviePy: {'✅' if MOVIEPY_AVAILABLE else '❌'} | FFMPEG: {'✅' if FFMPEG_AVAILABLE else '⚠️'}"
        tk.Label(diag_frame, 
                text=status_text, 
                font=("Segoe UI", 10),
                bg="#ecf0f1",
                fg="#34495e").pack(anchor="w", padx=10, pady=10)
        
        # Основной контент
        content_frame = tk.Frame(self.root, bg="#f0f0f0", padx=20, pady=20)
        content_frame.pack(fill="both", expand=True)
        
        # ========== РАЗДЕЛ 1: КОНВЕРТЕР ФОТО ==========
        converter_frame = tk.Frame(content_frame, bg="#e8f4f8", relief="solid", bd=2)
        converter_frame.pack(fill="x", pady=10, ipady=10)
        
        tk.Label(converter_frame, 
                text="📷 РАЗДЕЛ 1: КОНВЕРТЕР ФОТО", 
                font=("Segoe UI", 12, "bold"),
                bg="#e8f4f8",
                fg="#0c5460").pack(anchor="w", padx=10, pady=5)
        
        tk.Label(converter_frame, 
                text="Конвертировать фото в другой формат", 
                font=("Segoe UI", 10),
                bg="#e8f4f8",
                fg="#34495e").pack(anchor="w", padx=10)
        
        # Выбор формата для конвертации
        convert_format_frame = tk.Frame(converter_frame, bg="#e8f4f8")
        convert_format_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(convert_format_frame, 
                text="Формат:", 
                font=("Segoe UI", 10),
                bg="#e8f4f8").pack(side="left")
        
        self.convert_format_var = tk.StringVar(value="png")
        formats = ["png", "jpg", "webp", "bmp", "tiff"]
        
        format_menu = ttk.Combobox(convert_format_frame, 
                                   textvariable=self.convert_format_var,
                                   values=formats,
                                   width=10,
                                   state="readonly")
        format_menu.pack(side="left", padx=10)
        
        tk.Label(convert_format_frame, 
                text="Качество (для JPG):", 
                font=("Segoe UI", 10),
                bg="#e8f4f8").pack(side="left", padx=(20,5))
        
        self.quality_var = tk.StringVar(value="95")
        quality_spin = tk.Spinbox(convert_format_frame, 
                                  from_=1, to=100, 
                                  textvariable=self.quality_var,
                                  width=5)
        quality_spin.pack(side="left")
        
        # Кнопка конвертации
        convert_btn = tk.Button(converter_frame,
                               text="🔄 Конвертировать фото",
                               font=("Segoe UI", 11, "bold"),
                               bg="#27ae60",
                               fg="white",
                               relief="flat",
                               cursor="hand2",
                               command=self.start_converter)
        convert_btn.pack(fill="x", padx=10, pady=5, ipady=8)
        
        # ========== РАЗДЕЛ 2: СОЗДАТЕЛЬ ВИДЕО ==========
        video_frame = tk.Frame(content_frame, bg="#fff3cd", relief="solid", bd=2)
        video_frame.pack(fill="x", pady=10, ipady=10)
        
        tk.Label(video_frame, 
                text="🎥 РАЗДЕЛ 2: СОЗДАТЕЛЬ ВИДЕО", 
                font=("Segoe UI", 12, "bold"),
                bg="#fff3cd",
                fg="#856404").pack(anchor="w", padx=10, pady=5)
        
        tk.Label(video_frame, 
                text="Создать 10-секундное статическое видео из фото", 
                font=("Segoe UI", 10),
                bg="#fff3cd",
                fg="#856404").pack(anchor="w", padx=10)
        
        # Статус MoviePy для видео
        if not MOVIEPY_AVAILABLE:
            warn_label = tk.Label(video_frame, 
                                 text="⚠️ Для этого раздела требуется MoviePy!",
                                 font=("Segoe UI", 10, "bold"),
                                 bg="#fff3cd",
                                 fg="#c0392b")
            warn_label.pack(anchor="w", padx=10, pady=5)
        
        # Кнопки форматов видео
        video_formats_frame = tk.Frame(video_frame, bg="#fff3cd")
        video_formats_frame.pack(fill="x", padx=10, pady=10)
        
        video_formats = [
            ("📹 MP4 (Рекомендуется)", "mp4", "#27ae60"),
            ("🎥 AVI", "avi", "#e67e22"),
            ("🍎 MOV", "mov", "#3498db"),
        ]

        for text, val, color in video_formats:
            btn = tk.Button(video_formats_frame,
                          text=text,
                          font=("Segoe UI", 10, "bold"),
                          bg=color,
                          fg="white",
                          relief="flat",
                          cursor="hand2",
                          state="normal" if MOVIEPY_AVAILABLE else "disabled",
                          command=lambda v=val: self.start_video_workflow(v))
            btn.pack(side="left", padx=5, expand=True, fill="x", ipady=5)
        
        # Дополнительные настройки видео
        video_settings_frame = tk.Frame(video_frame, bg="#fff3cd")
        video_settings_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(video_settings_frame, 
                text="Размер видео:", 
                font=("Segoe UI", 9),
                bg="#fff3cd").pack(side="left")
        
        self.video_size_var = tk.StringVar(value="original")
        sizes = [("Оригинальный", "original"), ("1920x1080", "1920x1080"), ("1280x720", "1280x720"), ("854x480", "854x480")]
        
        for text, value in sizes:
            rb = tk.Radiobutton(video_settings_frame, 
                               text=text, 
                               variable=self.video_size_var, 
                               value=value,
                               bg="#fff3cd",
                               font=("Segoe UI", 8))
            rb.pack(side="left", padx=2)
        
        # ========== ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ==========
        tools_frame = tk.Frame(content_frame, bg="#d4edda", relief="solid", bd=2)
        tools_frame.pack(fill="x", pady=10, ipady=10)
        
        tk.Label(tools_frame, 
                text="🔧 ДОПОЛНИТЕЛЬНО", 
                font=("Segoe UI", 12, "bold"),
                bg="#d4edda",
                fg="#155724").pack(anchor="w", padx=10, pady=5)
        
        # Кнопки инструментов
        tools_btn_frame = tk.Frame(tools_frame, bg="#d4edda")
        tools_btn_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(tools_btn_frame,
                 text="📦 Установить MoviePy",
                 font=("Segoe UI", 10, "bold"),
                 bg="#3498db",
                 fg="white",
                 relief="flat",
                 cursor="hand2",
                 command=self.install_moviepy).pack(side="left", padx=5, expand=True, fill="x", ipady=5)
        
        tk.Button(tools_btn_frame,
                 text="🎬 Скачать VLC",
                 font=("Segoe UI", 10, "bold"),
                 bg="#e67e22",
                 fg="white",
                 relief="flat",
                 cursor="hand2",
                 command=self.install_vlc).pack(side="left", padx=5, expand=True, fill="x", ipady=5)
        
        tk.Button(tools_btn_frame,
                 text="ℹ️ Информация",
                 font=("Segoe UI", 10, "bold"),
                 bg="#95a5a6",
                 fg="white",
                 relief="flat",
                 cursor="hand2",
                 command=self.show_info).pack(side="left", padx=5, expand=True, fill="x", ipady=5)
        
        # Нижняя панель
        footer_frame = tk.Frame(self.root, bg="#bdc3c7", height=30)
        footer_frame.pack(fill="x", side="bottom")
        footer_frame.pack_propagate(False)
        
        tk.Label(footer_frame,
                text=f"Версия {VERSION} | Выберите раздел для работы",
                font=("Segoe UI", 8),
                bg="#bdc3c7",
                fg="#2c3e50").pack(expand=True)

    # ========== МЕТОДЫ ДЛЯ КОНВЕРТЕРА ФОТО ==========
    
    def start_converter(self):
        """Запуск конвертера фото"""
        self.current_mode = "converter"
        self.root.withdraw()
        self.cancel_flag = False
        
        threading.Thread(target=self.process_converter, daemon=True).start()
    
    def process_converter(self):
        """Процесс конвертации фото"""
        try:
            # Выбор файлов
            files = self.select_files()
            if not files:
                self.show_warning("Файлы не были выбраны!")
                self.root.deiconify()
                return

            # Выбор папки
            out_dir = self.select_output_directory()
            if not out_dir:
                self.show_warning("Папка не выбрана!")
                self.root.deiconify()
                return

            # Конвертация
            self.convert_images(files, out_dir)
            
        except Exception as e:
            self.show_error(f"Ошибка: {str(e)}")
        finally:
            if not self.cancel_flag:
                self.cleanup()
    
    def convert_images(self, files, out_dir):
        """Конвертация изображений"""
        target_format = self.convert_format_var.get()
        quality = int(self.quality_var.get())
        
        self.show_progress_window(len(files))
        
        self.log_message(f"\n{'='*70}")
        self.log_message(f"🔄 КОНВЕРТАЦИЯ ФОТО")
        self.log_message(f"📁 Выходной формат: {target_format.upper()}")
        self.log_message(f"🎯 Качество: {quality}%")
        self.log_message(f"📦 Файлов для обработки: {len(files)}")
        self.log_message(f"{'='*70}\n")

        successful = 0
        failed = 0
        failed_files = []

        for i, path in enumerate(files, 1):
            if self.cancel_flag:
                break
                
            try:
                clean_name = Path(path).stem
                out_path = os.path.join(out_dir, f"{clean_name}.{target_format}")
                
                # Открываем и конвертируем изображение
                with Image.open(path) as img:
                    # Конвертируем в RGB если нужно для JPEG
                    if target_format.lower() in ['jpg', 'jpeg'] and img.mode in ['RGBA', 'P']:
                        img = img.convert('RGB')
                    
                    # Сохраняем с нужным качеством
                    if target_format.lower() in ['jpg', 'jpeg']:
                        img.save(out_path, quality=quality, optimize=True)
                    else:
                        img.save(out_path)
                
                successful += 1
                self.log_message(f"[✅] {i}/{len(files)}: {clean_name}.{target_format}")
                self.update_progress(i, len(files), f"✓ {clean_name}")
                
            except Exception as e:
                failed += 1
                failed_files.append(Path(path).name)
                self.log_message(f"[❌] {i}/{len(files)}: {Path(path).name} - {str(e)}")
                self.update_progress(i, len(files), f"✗ Ошибка")

        if not self.cancel_flag:
            self.show_conversion_result(successful, failed, failed_files, out_dir)

    # ========== МЕТОДЫ ДЛЯ СОЗДАТЕЛЯ ВИДЕО ==========
    
    def start_video_workflow(self, fmt):
        """Запуск создателя видео"""
        if not MOVIEPY_AVAILABLE:
            messagebox.showerror("Ошибка", 
                               "MoviePy не установлен!\n\n"
                               "Нажмите 'Установить MoviePy' в разделе ДОПОЛНИТЕЛЬНО")
            return
            
        try:
            from moviepy import ImageClip
            from moviepy.video.fx import Resize
        except ImportError as e:
            messagebox.showerror("Ошибка импорта", 
                               f"Не удалось импортировать MoviePy: {e}")
            return
            
        self.current_mode = "video"
        self.video_ext = fmt
        self.root.withdraw()
        self.cancel_flag = False
        
        threading.Thread(target=self.process_video, daemon=True).start()
    
    def process_video(self):
        """Процесс создания видео"""
        try:
            files = self.select_files()
            if not files:
                self.show_warning("Файлы не были выбраны!")
                self.root.deiconify()
                return

            out_dir = self.select_output_directory()
            if not out_dir:
                self.show_warning("Папка не выбрана!")
                self.root.deiconify()
                return

            self.create_videos(files, out_dir)
            
        except Exception as e:
            self.show_error(f"Ошибка: {str(e)}")
        finally:
            if not self.cancel_flag:
                self.cleanup()
    
    def fix_image_size(self, img_path):
        """Исправление размера изображения для видео"""
        with Image.open(img_path) as img:
            width, height = img.size
            
            # Проверяем, нужно ли изменять размер
            if width % 2 != 0 or height % 2 != 0:
                # Новый размер с четными значениями
                new_width = width if width % 2 == 0 else width + 1
                new_height = height if height % 2 == 0 else height + 1
                
                # Создаем временный файл с исправленным размером
                temp_path = os.path.join(self.temp_dir, f"fixed_{Path(img_path).name}")
                
                # Изменяем размер изображения
                img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                img_resized.save(temp_path)
                
                return temp_path
        
        return img_path
    
    def create_videos(self, files, out_dir):
        """Создание видео из фото"""
        self.show_progress_window(len(files))
        
        self.log_message(f"\n{'='*70}")
        self.log_message(f"🎥 СОЗДАНИЕ ВИДЕО")
        self.log_message(f"📁 Формат: {self.video_ext.upper()}")
        self.log_message(f"⏱️ Длительность: {DURATION} сек")
        self.log_message(f"📦 Файлов для обработки: {len(files)}")
        self.log_message(f"{'='*70}\n")

        successful = 0
        failed = 0
        failed_files = []

        for i, path in enumerate(files, 1):
            if self.cancel_flag:
                break
                
            try:
                from moviepy import ImageClip
                
                clean_name = Path(path).stem
                out_path = os.path.join(out_dir, f"{clean_name}.{self.video_ext}")
                
                # Исправляем размер изображения если нужно
                fixed_path = self.fix_image_size(path)
                
                # Создаем видео
                with ImageClip(fixed_path).with_duration(DURATION) as clip:
                    clip.fps = FPS
                    
                    # Применяем изменение размера если выбрано
                    if self.video_size_var.get() != "original":
                        target_size = self.video_size_var.get().split('x')
                        target_width = int(target_size[0])
                        target_height = int(target_size[1])
                        
                        # Изменяем размер с сохранением пропорций
                        clip = clip.resized((target_width, target_height))
                    
                    # Дополнительные параметры для совместимости
                    ffmpeg_params = [
                        "-pix_fmt", "yuv420p",
                        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2"  # Принудительно делаем размеры четными
                    ]
                    
                    clip.write_videofile(
                        out_path,
                        codec='libx264',
                        audio=False,
                        logger=None,
                        preset='medium',
                        ffmpeg_params=ffmpeg_params
                    )
                
                # Удаляем временный файл
                if fixed_path != path and os.path.exists(fixed_path):
                    os.remove(fixed_path)
                
                successful += 1
                self.log_message(f"[✅] {i}/{len(files)}: {clean_name}.{self.video_ext}")
                self.update_progress(i, len(files), f"✓ {clean_name}")
                
            except Exception as e:
                failed += 1
                failed_files.append(Path(path).name)
                self.log_message(f"[❌] {i}/{len(files)}: {Path(path).name} - {str(e)}")
                self.update_progress(i, len(files), f"✗ Ошибка")

        if not self.cancel_flag:
            self.show_video_result(successful, failed, failed_files, out_dir)

    # ========== ОБЩИЕ МЕТОДЫ ==========
    
    def select_files(self):
        """Выбор файлов"""
        try:
            files = filedialog.askopenfilenames(
                title="Выберите фотографии",
                filetypes=[("Изображения", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.gif")]
            )
            return files if files else None
        except:
            return None

    def select_output_directory(self):
        """Выбор папки"""
        try:
            out_dir = filedialog.askdirectory(title="Выберите папку для сохранения")
            return out_dir if out_dir else None
        except:
            return None

    def show_progress_window(self, total):
        """Окно прогресса"""
        self.progress_win = tk.Toplevel(self.root)
        self.progress_win.title("Обработка")
        self.progress_win.geometry("400x150")
        
        self.status_label = tk.Label(self.progress_win, text="Обработка...")
        self.status_label.pack(pady=20)
        
        self.progress_bar = ttk.Progressbar(self.progress_win, length=300, mode='determinate', maximum=total)
        self.progress_bar.pack(pady=10)
        
        tk.Button(self.progress_win, text="Отмена", command=self.cancel_processing).pack()

    def update_progress(self, current, total, status):
        """Обновление прогресса"""
        if self.progress_bar:
            self.progress_bar['value'] = current
        if self.status_label:
            self.status_label.config(text=f"{current}/{total}: {status}")
        self.progress_win.update()

    def cancel_processing(self):
        """Отмена"""
        self.cancel_flag = True
        if self.progress_win:
            self.progress_win.destroy()
        self.root.deiconify()

    def show_conversion_result(self, successful, failed, failed_files, out_dir):
        """Результат конвертации"""
        if self.progress_win:
            self.progress_win.destroy()
        
        msg = f"✅ Конвертация завершена!\n\nУспешно: {successful}\nОшибок: {failed}\n\nПапка: {out_dir}"
        
        if failed == 0:
            messagebox.showinfo("Успех", msg)
        else:
            messagebox.showwarning("Завершено", msg)
        
        self.cleanup()

    def show_video_result(self, successful, failed, failed_files, out_dir):
        """Результат создания видео"""
        if self.progress_win:
            self.progress_win.destroy()
        
        msg = f"✅ Видео созданы!\n\nУспешно: {successful}\nОшибок: {failed}\n\nПапка: {out_dir}"
        
        if failed == 0:
            messagebox.showinfo("Успех", msg)
        else:
            error_details = "\n".join(failed_files[:5])
            if len(failed_files) > 5:
                error_details += f"\n... и еще {len(failed_files) - 5} файлов"
            msg += f"\n\nОшибки в файлах:\n{error_details}"
            messagebox.showwarning("Завершено с ошибками", msg)
        
        self.cleanup()

    def show_warning(self, message):
        """Предупреждение"""
        self.root.deiconify()
        messagebox.showwarning("Внимание", message)

    def show_error(self, message):
        """Ошибка"""
        self.root.deiconify()
        messagebox.showerror("Ошибка", message)

    def log_message(self, message):
        """Логирование"""
        print(message)

    def cleanup(self):
        """Очистка"""
        try:
            if self.progress_win:
                self.progress_win.destroy()
            self.root.deiconify()
        except:
            pass

    # ========== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ==========
    
    def install_moviepy(self):
        """Установка MoviePy"""
        try:
            install_win = tk.Toplevel(self.root)
            install_win.title("Установка MoviePy")
            install_win.geometry("600x400")
            
            install_win.update_idletasks()
            x = (install_win.winfo_screenwidth() // 2) - (600 // 2)
            y = (install_win.winfo_screenheight() // 2) - (400 // 2)
            install_win.geometry(f'600x400+{x}+{y}')
            
            tk.Label(install_win, 
                    text="📦 Установка MoviePy и зависимостей", 
                    font=("Segoe UI", 12, "bold"),
                    fg="#2c3e50").pack(pady=20)
            
            output_text = tk.Text(install_win, height=15, width=70, font=("Consolas", 9))
            output_text.pack(pady=10, padx=20)
            
            scrollbar = tk.Scrollbar(output_text)
            scrollbar.pack(side="right", fill="y")
            output_text.config(yscrollcommand=scrollbar.set)
            scrollbar.config(command=output_text.yview)
            
            status_label = tk.Label(install_win, 
                                   text="Подготовка...", 
                                   font=("Segoe UI", 10),
                                   fg="#7f8c8d")
            status_label.pack()
            
            def append_output(text):
                output_text.insert(tk.END, text + "\n")
                output_text.see(tk.END)
                install_win.update()
            
            def install():
                try:
                    append_output("🔄 Удаление старых версий...")
                    subprocess.run(
                        [sys.executable, "-m", "pip", "uninstall", "moviepy", "imageio-ffmpeg", "-y"],
                        capture_output=True,
                        text=True
                    )
                    
                    append_output("📥 Установка imageio-ffmpeg...")
                    result1 = subprocess.run(
                        [sys.executable, "-m", "pip", "install", "imageio-ffmpeg"],
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    append_output(result1.stdout)
                    
                    append_output("📥 Установка moviepy...")
                    result2 = subprocess.run(
                        [sys.executable, "-m", "pip", "install", "moviepy"],
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    append_output(result2.stdout)
                    
                    if result2.returncode == 0:
                        status_label.config(text="✅ Установка завершена! Перезапустите программу.", fg="#27ae60")
                        append_output("\n✅ MoviePy успешно установлен!")
                        append_output("🔄 Пожалуйста, перезапустите программу")
                    else:
                        status_label.config(text="❌ Ошибка установки", fg="#c0392b")
                        
                except Exception as e:
                    status_label.config(text=f"❌ Ошибка: {str(e)}", fg="#c0392b")
                    append_output(f"❌ {str(e)}")
            
            threading.Thread(target=install, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть окно установки: {e}")

    def install_vlc(self):
        """Скачать VLC"""
        import webbrowser
        webbrowser.open("https://www.videolan.org/vlc/download-windows.html")
        messagebox.showinfo("VLC Media Player", 
                          "Скачайте и установите VLC с открывшегося сайта")

    def show_info(self):
        """Показать информацию"""
        info = f"""🎬 Video Maker Pro v{VERSION}

📷 РАЗДЕЛ 1: КОНВЕРТЕР ФОТО
• Конвертирует фото в любой формат
• Поддерживает: PNG, JPG, WEBP, BMP, TIFF
• Настройка качества для JPG

🎥 РАЗДЕЛ 2: СОЗДАТЕЛЬ ВИДЕО
• Создает 10-секундное видео из фото
• Поддерживает: MP4, AVI, MOV
• Автоматически исправляет размеры изображений
• Выбор размера видео

📦 Зависимости:
• PIL (Pillow) - для конвертера
• MoviePy - для видео
• FFMPEG - для кодирования

⚡ Версия: {VERSION}
"""
        messagebox.showinfo("О программе", info)

def main():
    """Главная функция"""
    print("\n" + "="*60)
    print("🎬 Video Maker Pro v" + VERSION)
    print("="*60)
    print(f"Python: {sys.executable}")
    print(f"PIL: ✅ | MoviePy: {'✅' if MOVIEPY_AVAILABLE else '❌'}")
    print("="*60 + "\n")
    
    try:
        app = VideoMakerPro()
        app.root.mainloop()
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        input("\nНажмите Enter для выхода...")

if __name__ == "__main__":
    main()
