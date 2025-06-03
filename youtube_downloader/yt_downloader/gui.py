import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
from downloader import download_video
import subprocess
import re
import os

def convert_to_quicktime_compatible_inplace_with_progress(file_path, progress_callback, total_duration_sec):
    ffmpeg_path = "/opt/homebrew/bin/ffmpeg"  # Mac için ffmpeg yolu, seninki farklıysa değiştir
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

    process = subprocess.Popen(command, stderr=subprocess.PIPE, universal_newlines=True)

    time_pattern = re.compile(r'time=(\d+):(\d+):(\d+\.\d+)')

    while True:
        line = process.stderr.readline()
        if not line:
            break

        match = time_pattern.search(line)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = float(match.group(3))
            elapsed = hours * 3600 + minutes * 60 + seconds

            progress = min(elapsed / total_duration_sec * 100, 100)
            progress_callback(progress)
    process.wait()

    if process.returncode != 0:
        raise RuntimeError("FFmpeg dönüştürme hatası!")

    os.remove(file_path)
    os.rename(temp_output, file_path)


def run_app():
    def progress_hook(d):
        if d['status'] == 'downloading':
            downloaded = d.get('_percent_str', '').strip().replace('%', '')
            try:
                progress = float(downloaded)
                progress_var.set(progress)
                status_label.config(text=f"⬇️ %{int(progress)} indiriliyor...")
            except ValueError:
                pass
        elif d['status'] == 'finished':
            progress_var.set(100)
            status_label.config(text="🕣 Dosyalar birleştiriliyor, lütfen bekleyiniz!\n(Bu biraz zaman alabilir)")

    def start_download():
        url = url_entry.get().strip()
        path = path_var.get().strip()
        is_audio_only = format_var.get() == "mp3"
        selected_quality = audio_quality_var.get() if is_audio_only else quality_var.get()

        if not url:
            messagebox.showwarning("Uyarı", "Lütfen YouTube URL'sini girin.")
            return

        if not path:
            messagebox.showwarning("Uyarı", "Lütfen kaydedilecek klasörü seçin.")
            return

        progress_var.set(0)
        status_label.config(text="📡 İndirme başlatıldı...")
        start_button.config(state="disabled", bg="#2af445")

        threading.Thread(
            target=lambda: threaded_download(url, path, is_audio_only, selected_quality),
            daemon=True
        ).start()

    def threaded_download(url, path, is_audio_only, selected_quality):
        try:
            from yt_dlp import YoutubeDL
            with YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
            duration = info.get('duration', 0)

            download_video(url, path, is_audio_only, selected_quality, progress_hook)

            if not is_audio_only:
                def ffmpeg_progress(p):
                    progress_var.set(p)
                    status_label.config(text=f"🕣 Dönüştürme %{int(p)} devam ediyor...")

                # İndirilen dosya yolu (dosya adı tam olarak buraya göre olmalı)
                downloaded_file = os.path.join(path, f"{info.get('title','video')}.mp4")

                convert_to_quicktime_compatible_inplace_with_progress(downloaded_file, ffmpeg_progress, duration)

            messagebox.showinfo("✅ Başarılı", "Video başarıyla indirildi!")
        except Exception as e:
            messagebox.showerror("❌ Hata", f"İndirme sırasında bir hata oluştu:\n{e}")
        finally:
            progress_var.set(0)
            status_label.config(text="")
            start_button.config(state="normal", bg="#3a3f55")

    def browse_folder():
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            path_var.set(folder_selected)

    def clear_url():
        url_entry.delete(0, tk.END)

    window = tk.Tk()
    window.title("📥 YouTube İndirici (MP4 - MP3 - QuickTime Uyumlu)")
    window.geometry("550x440")
    window.configure(bg="#1e1e1e")
    window.resizable(False, False)

    label_style = {"bg": "#1e1e1e", "fg": "white", "font": ("Helvetica", 11)}
    entry_style = {"bg": "#2d2d2d", "fg": "white", "insertbackground": "white"}

    tk.Label(window, text="🎬 YouTube Video / Müzik İndirici", font=("Helvetica", 16, "bold"), bg="#1e1e1e", fg="white").pack(pady=15)

    # URL kısmı
    tk.Label(window, text="YouTube URL'si:", **label_style).pack(anchor="w", padx=30)

    frame_url = tk.Frame(window, bg="#1e1e1e")
    frame_url.pack(padx=30, pady=5, fill="x")

    url_entry = tk.Entry(frame_url, width=50, **entry_style, relief="flat")
    url_entry.pack(side="left", fill="x", expand=True)

    clear_button = tk.Button(
        frame_url, text="✖", command=clear_url, bg="#3a3a3a", fg="red",
        relief="flat", font=("Helvetica", 10, "bold"), padx=6, pady=1,
        activebackground="#2d2d2d"
    )
    clear_button.pack(side="left", padx=5)

    # Kaydedilecek klasör seçimi
    tk.Label(window, text="Kaydedilecek Klasör:", **label_style).pack(anchor="w", padx=30, pady=(10, 0))
    frame_path = tk.Frame(window, bg="#1e1e1e")
    frame_path.pack(padx=30, pady=5, fill="x")
    path_var = tk.StringVar()
    path_entry = tk.Entry(frame_path, textvariable=path_var, width=45, **entry_style, relief="flat")
    path_entry.pack(side="left", fill="x", expand=True)
    tk.Button(frame_path, text="Gözat", command=browse_folder, bg="#3a3a3a", fg="brown", relief="flat").pack(side="left", padx=5)

    # Format seçimi (mp4 / mp3)
    tk.Label(window, text="İndirme Formatı:", **label_style).pack(anchor="w", padx=30, pady=(10, 0))

    format_var = tk.StringVar(value="mp4")

    frame_format = tk.Frame(window, bg="#1e1e1e")
    frame_format.pack(padx=30, pady=5, anchor="w")

    tk.Radiobutton(frame_format, text="🎥 MP4", variable=format_var, value="mp4",
                   bg="#1e1e1e", fg="white", selectcolor="#2d2d2d", activebackground="#2d2d2d").pack(side="left")
    tk.Radiobutton(frame_format, text="🎵 MP3", variable=format_var, value="mp3",
                   bg="#1e1e1e", fg="white", selectcolor="#2d2d2d", activebackground="#2d2d2d").pack(side="left", padx=10)

    # Kalite başlığı (dinamik)
    label_quality_title = tk.Label(window, text="Video Kalitesi:", **label_style)
    label_quality_title.pack(anchor="w", padx=30, pady=(10, 0))

    # Burada kalite seçenekleri için ortak container oluşturduk
    frame_quality_container = tk.Frame(window, bg="#1e1e1e")
    frame_quality_container.pack(padx=30, pady=5, anchor="w")

    # Video kalitesi seçenekleri frame'i
    quality_var = tk.StringVar(value="1080")
    frame_video_quality = tk.Frame(frame_quality_container, bg="#1e1e1e")
    frame_video_quality.pack(fill="x")

    quality_buttons = []
    q1 = tk.Radiobutton(frame_video_quality, text="🔽 720p", variable=quality_var, value="720",
                        bg="#1e1e1e", fg="white", selectcolor="#2d2d2d", activebackground="#2d2d2d")
    q1.pack(side="left")
    quality_buttons.append(q1)

    q2 = tk.Radiobutton(frame_video_quality, text="🎯 1080p", variable=quality_var, value="1080",
                        bg="#1e1e1e", fg="white", selectcolor="#2d2d2d", activebackground="#2d2d2d")
    q2.pack(side="left", padx=10)
    quality_buttons.append(q2)

    q3 = tk.Radiobutton(frame_video_quality, text="🚀 1440p", variable=quality_var, value="1440",
                        bg="#1e1e1e", fg="white", selectcolor="#2d2d2d", activebackground="#2d2d2d")
    q3.pack(side="left")
    quality_buttons.append(q3)

    q4 = tk.Radiobutton(frame_video_quality, text="⚡ 2160p", variable=quality_var, value="2160",
                        bg="#1e1e1e", fg="white", selectcolor="#2d2d2d", activebackground="#2d2d2d")
    q4.pack(side="left", padx=10)
    quality_buttons.append(q4)

    # Ses kalitesi seçenekleri frame'i (başta gizli)
    audio_quality_var = tk.StringVar(value="192")
    frame_audio_quality = tk.Frame(frame_quality_container, bg="#1e1e1e")

    a1 = tk.Radiobutton(frame_audio_quality, text="🎧 128 kbps", variable=audio_quality_var, value="128",
                        bg="#1e1e1e", fg="white", selectcolor="#2d2d2d", activebackground="#2d2d2d")
    a1.pack(side="left")
    a2 = tk.Radiobutton(frame_audio_quality, text="🎶 192 kbps", variable=audio_quality_var, value="192",
                        bg="#1e1e1e", fg="white", selectcolor="#2d2d2d", activebackground="#2d2d2d")
    a2.pack(side="left", padx=10)

    def toggle_quality_options():
        if format_var.get() == "mp3":
            frame_video_quality.pack_forget()
            frame_audio_quality.pack(fill="x")
            label_quality_title.config(text="Ses Kalitesi:")
        else:
            frame_audio_quality.pack_forget()
            frame_video_quality.pack(fill="x")
            label_quality_title.config(text="Video Kalitesi:")

    format_var.trace("w", lambda *args: toggle_quality_options())
    toggle_quality_options()

    # İndirme butonu ve ilerleme göstergesi
    progress_var = tk.DoubleVar()
    start_button = tk.Button(window, text="▶️ İndir", font=("Helvetica", 14, "bold"),
                             bg="#3a3f55", fg="white", relief="flat", command=start_download)
    start_button.pack(pady=20, ipadx=20, ipady=7)

    progress_bar = ttk.Progressbar(window, variable=progress_var, maximum=100, length=400)
    progress_bar.pack(pady=5)

    status_label = tk.Label(window, text="", font=("Helvetica", 10), bg="#1e1e1e", fg="#88f")
    status_label.pack()

    window.mainloop()


if __name__ == "__main__":
    run_app()
