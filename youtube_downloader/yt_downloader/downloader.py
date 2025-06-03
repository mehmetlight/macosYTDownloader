from yt_dlp import YoutubeDL
import os
import subprocess
import re

def sanitize_filename(filename: str) -> str:
    filename = re.sub(r'[\\/*?:"<>|]', '', filename)
    filename = filename.replace('\n', '').replace('\r', '')
    filename = filename.strip()
    return filename

def convert_to_quicktime_compatible_inplace(file_path):
    ffmpeg_path = "/opt/homebrew/bin/ffmpeg"
    temp_output = file_path + ".temp.mp4"

    command = [
        ffmpeg_path,
        '-i', file_path,
        '-c:v', 'libx264',
        '-preset', 'slow',
        '-crf', '22',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-movflags', '+faststart',
        temp_output
    ]

    try:
        subprocess.run(command, check=True)
        os.remove(file_path)  # Eski dosyayı sil
        os.rename(temp_output, file_path)  # Yeni dosyayı eski adla kaydet
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg dönüştürme hatası: {e}")

def cleanup_temp_files(path):
    for file in os.listdir(path):
        if file.lower().startswith("temp") and file.lower().endswith(".mp4"):
            file_path = os.path.join(path, file)
            try:
                os.remove(file_path)
                print(f"Silindi: {file}")
            except Exception as e:
                print(f"Silinemedi: {file} - Hata: {e}")

def progress_hook(d):
    if d['status'] == 'downloading':
        print(f"İndiriliyor... {d.get('_percent_str', '')}")
    elif d['status'] == 'finished':
        print("İndirme tamamlandı, dönüştürülüyor...")

def get_unique_filepath(path, title, ext):
    base = os.path.join(path, title)
    full_path = f"{base}.{ext}"
    counter = 1
    while os.path.exists(full_path):
        full_path = f"{base} ({counter}).{ext}"
        counter += 1
    return full_path

def download_video(url, path, is_audio_only, selected_quality, progress_hook):
    ffmpeg_path = "/opt/homebrew/bin/ffmpeg"

    # FFmpeg var mı kontrolü
    try:
        subprocess.run([ffmpeg_path, "-version"], check=True, capture_output=True)
    except Exception as e:
        raise RuntimeError(f"FFmpeg bulunamadı! Hata: {str(e)}")

    # İlk önce video bilgilerini çek
    with YoutubeDL({'quiet': True}) as ydl:
        info = ydl.extract_info(url, download=False)
        raw_title = info.get('title', 'video')
        title = sanitize_filename(raw_title)
        ext = 'mp3' if is_audio_only else 'mp4'
        full_path = get_unique_filepath(path, title, ext)
        title = os.path.splitext(os.path.basename(full_path))[0]

    outtmpl = os.path.join(path, f"{title}.%(ext)s")

    ydl_opts = {
        'outtmpl': outtmpl,
        'progress_hooks': [progress_hook],
        'ffmpeg_location': ffmpeg_path,
        'nopart': True,
        'verbose': True,
        'quiet': False,
    }

    if is_audio_only:
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        format_str = f'bestvideo[ext=mp4][vcodec^=avc1][height<={selected_quality}]+bestaudio[ext=m4a]/best'
        ydl_opts.update({
            'format': format_str,
            'merge_output_format': 'mp4',
            # postprocessors kaldırdık, kendi ffmpeg ile dönüştürme yapacağız
        })

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        downloaded_file = os.path.join(path, f"{title}.mp3" if is_audio_only else f"{title}.mp4")

        if not os.path.exists(downloaded_file):
            raise FileNotFoundError(f"İndirilen dosya bulunamadı: {downloaded_file}")

        if not is_audio_only:
            convert_to_quicktime_compatible_inplace(downloaded_file)

        # İndirme bittikten sonra temp dosyaları temizle
        cleanup_temp_files(path)

        return downloaded_file

    except Exception as e:
        raise RuntimeError(f"İndirme veya dönüştürme başarısız: {str(e)}")

def main():
    download_folder = os.path.abspath("./downloads")
    os.makedirs(download_folder, exist_ok=True)

    print("Video İndirme Programı - Çıkmak için 'q' yazınız.")

    while True:
        url = input("İndirmek istediğiniz video URL'sini girin: ").strip()
        if url.lower() == 'q':
            print("Program sonlandırıldı.")
            break

        audio_only = input("Sadece ses indirilsin mi? (e/h): ").strip().lower() == 'e'
        quality_input = input("İndirilecek video kalitesini girin (örn: 1080, 720, 480): ").strip()

        try:
            quality = int(quality_input)
        except ValueError:
            print("Geçersiz kalite girdiniz, varsayılan 720 olarak ayarlandı.")
            quality = 720

        try:
            print("İndirme başlıyor...")
            result_path = download_video(url, download_folder, audio_only, quality, progress_hook)
            print(f"İndirme tamamlandı: {result_path}\n")
        except Exception as e:
            print(f"İndirme sırasında bir hata oluştu: {e}\n")

if __name__ == "__main__":
    main()
