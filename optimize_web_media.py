import os
import sys
import shutil
import subprocess
from pathlib import Path
from PIL import Image

# Ensure UTF-8 console output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent
PHOTOS_DIR = PROJECT_ROOT / "Photos"
PHOTOS_WEB_DIR = PROJECT_ROOT / "Photos_web"
PHOTOS_HDR_BACKUP_DIR = PROJECT_ROOT / "Photos_HDR_Backup"

PHOTOS_WEB_DIR.mkdir(parents=True, exist_ok=True)
PHOTOS_HDR_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def get_ffmpeg_path():
    """Locate ffmpeg executable via system PATH or imageio_ffmpeg."""
    ff = shutil.which("ffmpeg")
    if ff:
        return ff
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    raise RuntimeError("ffmpeg executable not found. Install imageio-ffmpeg or add ffmpeg to PATH.")

def is_video_hdr(video_path, ffmpeg_bin):
    """Detect if video is HDR / HLG (10-bit HEVC, bt2020, arib-std-b67, smpte2084)."""
    cmd = [ffmpeg_bin, "-i", str(video_path)]
    res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True, errors="replace")
    info = res.stderr.lower()
    
    is_10bit = "yuv420p10" in info or "10-bit" in info or "10 bit" in info
    is_hdr_color = "bt2020" in info or "arib-std-b67" in info or "smpte2084" in info or "hlg" in info
    return is_10bit or is_hdr_color

def get_video_dimensions(video_path, ffmpeg_bin):
    """Retrieve video width and height using ffmpeg info output."""
    cmd = [ffmpeg_bin, "-i", str(video_path)]
    res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True, errors="replace")
    import re
    match = re.search(r"(\d{3,4})x(\d{3,4})", res.stderr)
    if match:
        return int(match.group(1)), int(match.group(2))
    return 1920, 1080

def optimize_video(input_path, output_path=None, force=False):
    """
    Оптимизация видео по утверждённому стандарту:
    - Проверка HDR: если HDR/HLG -> бэкап в Photos_HDR_Backup, тонирование в BT.709.
    - Разрешение: масштабирование до 1080p по длинной стороне (1920x1080 горизонт, 1080x1920 верт).
    - Кодек: libx264, preset fast, CRF 23.
    - Частота кадров: 60 fps (-r 60).
    - Звук: AAC 128 kbps.
    - Метаданные: +faststart.
    """
    input_path = Path(input_path)
    if output_path is None:
        output_path = PHOTOS_WEB_DIR / input_path.name
    output_path = Path(output_path)

    if output_path.exists() and not force:
        print(f"  [Пропуск видео] Уже существует: {output_path.name}")
        return output_path

    ffmpeg_bin = get_ffmpeg_path()
    is_hdr = is_video_hdr(input_path, ffmpeg_bin)

    if is_hdr:
        backup_path = PHOTOS_HDR_BACKUP_DIR / input_path.name
        if not backup_path.exists():
            shutil.copy2(input_path, backup_path)
            print(f"  [HDR Бэкап] Оригинал сохранён в: {backup_path.name}")

    w, h = get_video_dimensions(input_path, ffmpeg_bin)
    is_horizontal = w >= h

    # Scale filter preserving aspect ratio up to 1080 on longest dimension
    if is_horizontal:
        scale_filter = "scale=w='min(1920,iw)':h=-2"
    else:
        scale_filter = "scale=w=-2:h='min(1920,ih)'"

    if is_hdr:
        # Calibrated HDR/HLG Mobius tonemapping to BT.709 SDR
        vf = f"zscale=t=linear:npl=500,format=gbrpf32le,tonemap=mobius:desat=0,zscale=p=bt709:t=bt709:m=bt709:r=tv,format=yuv420p,{scale_filter}"
    else:
        vf = scale_filter

    tmp_out = output_path.with_suffix(".tmp.mp4")
    cmd = [
        ffmpeg_bin, "-y",
        "-i", str(input_path),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-r", "60",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        str(tmp_out)
    ]

    print(f"  [Конвертация видео] {input_path.name} -> {output_path.name} (HDR={is_hdr}, 60fps, 1080p)...")
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, errors="replace")
    if res.returncode != 0:
        if tmp_out.exists():
            tmp_out.unlink()
        raise RuntimeError(f"FFmpeg error on {input_path.name}:\n{res.stderr[-500:]}")

    tmp_out.replace(output_path)
    print(f"  [Готово] {output_path.name} ({output_path.stat().st_size / (1024*1024):.1f} MB)")
    return output_path

def optimize_photo(input_path, output_path=None, force=False):
    """
    Оптимизация фото по утверждённому стандарту:
    - Оригинал в Photos/ не изменяется.
    - Разрешение: масштабирование до 2560 px по длинной стороне (Lanczos).
    - Сжатие: Progressive JPEG, quality=85, optimize=True.
    - Метаданные: полное сохранение оригинальных EXIF-тегов.
    """
    input_path = Path(input_path)
    if output_path is None:
        output_path = PHOTOS_WEB_DIR / input_path.name
    output_path = Path(output_path)

    if output_path.exists() and not force:
        return output_path

    with Image.open(input_path) as img:
        exif_data = img.info.get("exif")
        w, h = img.size
        max_dim = 2560

        if max(w, h) > max_dim:
            if w >= h:
                new_w = max_dim
                new_h = int(round(h * (max_dim / w)))
            else:
                new_h = max_dim
                new_w = int(round(w * (max_dim / h)))
            img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        else:
            img_resized = img.copy()

        if img_resized.mode in ("RGBA", "P"):
            img_resized = img_resized.convert("RGB")

        save_kwargs = {
            "format": "JPEG",
            "quality": 85,
            "optimize": True,
            "progressive": True
        }
        if exif_data:
            save_kwargs["exif"] = exif_data

        tmp_out = output_path.with_suffix(".tmp.jpg")
        img_resized.save(tmp_out, **save_kwargs)
        tmp_out.replace(output_path)

    print(f"  [Фото оптимизировано] {output_path.name} ({output_path.stat().st_size / 1024:.0f} KB)")
    return output_path

def optimize_all_photos_dir(force=False):
    """Process all photos and videos in Photos/ and save to Photos_web/."""
    video_exts = {".mp4", ".mov", ".m4v"}
    photo_exts = {".jpg", ".jpeg", ".png", ".webp"}

    all_files = sorted(PHOTOS_DIR.iterdir())
    print(f"Найдено {len(all_files)} файлов в {PHOTOS_DIR}...")
    
    count_v = 0
    count_p = 0
    for f in all_files:
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        if ext in video_exts:
            optimize_video(f, force=force)
            count_v += 1
        elif ext in photo_exts:
            optimize_photo(f, force=force)
            count_p += 1

    print(f"\nОбработка завершена: {count_v} видео, {count_p} фото проверено/обработано.")

if __name__ == "__main__":
    optimize_all_photos_dir()
