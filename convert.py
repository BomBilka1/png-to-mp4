import os

from moviepy import ImageClip 

# Настройки
INPUT_FOLDER = "Фото"
OUTPUT_FOLDER = "Видео"
DURATION = 10

def convert():
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    # Ищем все PNG файлы
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith('.png')]

    if not files:
        print(f"В папке '{INPUT_FOLDER}' нет PNG-файлов!")
        return

    print(f"Найдено картинок: {len(files)}")

    for filename in files:
        img_path = os.path.join(INPUT_FOLDER, filename)
        
        # Меняем расширение на .mp4
        video_name = os.path.splitext(filename)[0] + ".mp4"
        output_path = os.path.join(OUTPUT_FOLDER, video_name)

        print(f"Обрабатываю: {filename}...")
        
        try:
            # В MoviePy 2.0 используем .with_duration вместо .set_duration
            clip = ImageClip(img_path).with_duration(DURATION)
            
            # В новых версиях FPS можно задать прямо при записи
            clip.write_videofile(output_path, codec="libx264", fps=24, logger=None)
        except Exception as e:
            print(f"Ошибка в файле {filename}: {e}")

    print("\nГотово! Все видео лежат в папке 'Видео'")

if __name__ == "__main__":
    convert()


