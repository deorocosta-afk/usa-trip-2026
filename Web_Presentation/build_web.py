import os
import re
import json
import glob
import subprocess
from pathlib import Path

# Paths relative to project structure
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
NOTES_DIR = PROJECT_ROOT / "Notes"
PHOTOS_DIR = PROJECT_ROOT / "Photos"
PHOTOS_WEB_DIR = PROJECT_ROOT / "Photos_web"
MEDIA_CACHE_DIR = SCRIPT_DIR / "media_cache"
OUTPUT_HTML = SCRIPT_DIR / "index.html"
ROOT_OUTPUT_HTML = PROJECT_ROOT / "index.html"

def get_browser_media_url(media_file, is_video=False):
    web_media_path = PHOTOS_WEB_DIR / media_file
    if web_media_path.exists() and web_media_path.stat().st_size > 0:
        return f"./Photos_web/{media_file}"
    return f"./Photos_web/{media_file}"

def extract_day_number(filename):
    match = re.search(r"Day\s*(\d+)", filename, re.IGNORECASE)
    return int(match.group(1)) if match else 999

def clean_location_title(raw_title):
    cleaned = re.sub(r"^[>\s]*\[!quote\]\s*", "", raw_title).strip()
    cleaned = re.sub(r"^[>\s]*📍\s*", "", cleaned).strip()
    parts = cleaned.split("|")
    first_part = parts[0].strip()
    first_part = re.sub(r"[*_]{2,}", "", first_part)
    first_part = re.sub(r"[*_]", "", first_part)
    return first_part.strip()

def clean_story_text(lines):
    full_text = " ".join([l.strip().lstrip(">").strip() for l in lines if l.strip()])
    full_text = re.sub(r"\*\*История кадра(?:\s*\([^)]*\))?:\*\*", "", full_text, flags=re.IGNORECASE)
    full_text = re.sub(r"\*\*Микро-история(?:\s*\([^)]*\))?:\*\*", "", full_text, flags=re.IGNORECASE)
    full_text = re.sub(r"История кадра(?:\s*\([^)]*\))?:", "", full_text, flags=re.IGNORECASE)
    full_text = re.sub(r"Микро-история(?:\s*\([^)]*\))?:", "", full_text, flags=re.IGNORECASE)
    full_text = re.sub(r"\s+", " ", full_text).strip()
    return full_text

def parse_day_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    day_title = ""
    title_match = re.search(r"^#{1,2}\s+((?:ROADBOOK:\s*)?(?:DAY|ДЕНЬ)\s*\d+[^\n\r]*)$", content, re.MULTILINE | re.IGNORECASE)
    if title_match:
        day_title = title_match.group(1).strip()
        sub_match = re.search(r"^##\s+([^\n\r#]+)$", content, re.MULTILINE)
        if sub_match and "ROADBOOK" in day_title.upper():
            day_title = f"{day_title} — {sub_match.group(1).strip()}"
    else:
        title_match2 = re.search(r"^#{1,2}\s+(.+)$", content, re.MULTILINE)
        if title_match2:
            day_title = title_match2.group(1).strip()
        else:
            day_title = file_path.stem

    lines = content.splitlines()
    slides = []
    
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].strip()
        media_match = re.match(r"!\[\[(?:Photos/)?([^\]|#]+)(?:\|.*?)?\]\]", line)
        if media_match:
            media_file = media_match.group(1).strip()
            is_video = media_file.lower().endswith(".mp4")
            media_url = get_browser_media_url(media_file, is_video=is_video)
            
            raw_title = ""
            story_lines = []
            j = i + 1
            while j < n and not lines[j].strip().startswith(">"):
                if lines[j].strip() in ["", "---"]:
                    j += 1
                else:
                    break
            
            if j < n and lines[j].strip().startswith(">"):
                raw_title = lines[j].strip()
                j += 1
                while j < n and lines[j].strip().startswith(">"):
                    story_lines.append(lines[j].strip())
                    j += 1
            
            loc_title = clean_location_title(raw_title)
            story = clean_story_text(story_lines)
            
            if media_file:
                slides.append({
                    "media": media_url,
                    "is_video": is_video,
                    "title": loc_title,
                    "story": story
                })
            i = j
        else:
            i += 1

    return {
        "file": file_path.name,
        "day_num": extract_day_number(file_path.name),
        "title": day_title,
        "slides": slides
    }

def collect_all_days():
    files = glob.glob(str(NOTES_DIR / "Day *.md"))
    parsed_days = []
    for f in sorted(files, key=extract_day_number):
        data = parse_day_file(Path(f))
        if data["slides"]:
            parsed_days.append(data)
    return parsed_days

def generate_html(days_data):
    days_json = json.dumps(days_data, ensure_ascii=False, indent=2)
    
    html_template = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, viewport-fit=cover">
  <title>Экспедиция: Калифорния 2026</title>
  <!-- Telegram WebApp SDK -->
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700&family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-main: #121212;
      --bg-card: #1a1a1a;
      --bg-card-hover: #222222;
      --accent-gold: #e5b567;
      --accent-gold-dim: rgba(229, 181, 103, 0.2);
      --text-main: #f0f0f0;
      --text-muted: #a0a0a0;
      --text-dim: #707070;
      --border: rgba(255, 255, 255, 0.08);
      --font-display: 'Cinzel', serif;
      --font-body: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      --nav-height: 64px;
      --bottom-bar-height: 68px;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      background-color: var(--bg-main);
      color: var(--text-main);
      font-family: var(--font-body);
      min-height: 100vh;
      overflow-x: hidden;
      -webkit-font-smoothing: antialiased;
      -webkit-tap-highlight-color: transparent;
    }}

    /* TOP NAVIGATION (Desktop & Tablet) */
    header.top-nav {{
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      height: var(--nav-height);
      background: rgba(18, 18, 18, 0.88);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 2rem;
      z-index: 1000;
      transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), background 0.3s ease;
    }}

    .nav-brand {{
      display: flex;
      align-items: center;
      gap: 0.6rem;
      font-family: var(--font-display);
      font-size: 1.15rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      color: var(--accent-gold);
      text-transform: uppercase;
      cursor: pointer;
      user-select: none;
    }}

    .nav-brand span.icon {{
      font-size: 1.3rem;
    }}

    .nav-center {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
      background: rgba(255, 255, 255, 0.04);
      padding: 4px;
      border-radius: 999px;
      border: 1px solid var(--border);
      max-width: 60vw;
      overflow-x: auto;
      scrollbar-width: none;
    }}
    .nav-center::-webkit-scrollbar {{
      display: none;
    }}

    .day-pill {{
      padding: 0.4rem 1rem;
      border-radius: 999px;
      font-size: 0.85rem;
      font-weight: 500;
      color: var(--text-muted);
      cursor: pointer;
      background: transparent;
      border: none;
      transition: all 0.2s ease;
      white-space: nowrap;
    }}

    .day-pill:hover {{
      color: var(--text-main);
      background: rgba(255, 255, 255, 0.06);
    }}

    .day-pill.active {{
      color: #121212;
      background: var(--accent-gold);
      font-weight: 600;
      box-shadow: 0 2px 10px rgba(229, 181, 103, 0.3);
    }}

    .nav-controls {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }}

    .view-toggle {{
      display: flex;
      background: rgba(255, 255, 255, 0.04);
      border-radius: 8px;
      padding: 3px;
      border: 1px solid var(--border);
    }}

    .toggle-btn {{
      padding: 0.4rem 0.85rem;
      font-size: 0.8rem;
      border: none;
      background: transparent;
      color: var(--text-muted);
      border-radius: 6px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.4rem;
      transition: all 0.2s ease;
      font-family: var(--font-body);
      user-select: none;
    }}

    .toggle-btn.active {{
      background: rgba(255, 255, 255, 0.12);
      color: var(--text-main);
      font-weight: 500;
    }}

    /* MAIN CONTAINER */
    main.view-container {{
      margin-top: var(--nav-height);
      min-height: calc(100vh - var(--nav-height));
      -webkit-overflow-scrolling: touch;
    }}

    /* 1. SLIDESHOW VIEW (Desktop / Mobile) */
    .slideshow-view {{
      position: fixed;
      top: var(--nav-height);
      left: 0;
      right: 0;
      bottom: 0;
      display: flex;
      background: #0a0a0a;
      overflow: hidden;
    }}

    .slide-media {{
      flex: 0 0 70%;
      height: 100%;
      position: relative;
      background: #000;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      touch-action: pan-y;
    }}

    .slide-media img, .slide-media video {{
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
      box-shadow: 0 0 40px rgba(0,0,0,0.8);
      transition: opacity 0.35s ease, transform 0.4s ease;
    }}

    /* Mobile Mute/Unmute Tap Overlay */
    .video-sound-btn {{
      position: absolute;
      bottom: 1.25rem;
      right: 1.25rem;
      width: 48px;
      height: 48px;
      border-radius: 50%;
      background: rgba(0, 0, 0, 0.65);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      border: 1px solid rgba(255, 255, 255, 0.2);
      color: #ffffff;
      display: none;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      z-index: 25;
      transition: transform 0.2s ease, background 0.2s ease;
    }}
    .video-sound-btn:active {{
      transform: scale(0.92);
      background: rgba(229, 181, 103, 0.85);
      color: #121212;
    }}
    .video-sound-btn svg {{
      width: 22px;
      height: 22px;
      pointer-events: none;
    }}

    .slide-sidebar {{
      flex: 0 0 30%;
      height: 100%;
      background: #141414;
      border-left: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding: 3rem 2.5rem;
      overflow-y: auto;
      -webkit-overflow-scrolling: touch;
    }}

    .slide-meta {{
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }}

    .slide-day-tag {{
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      font-family: var(--font-display);
      font-size: 0.85rem;
      color: var(--accent-gold);
      letter-spacing: 0.1em;
      text-transform: uppercase;
    }}

    .slide-title {{
      font-size: 1.75rem;
      font-weight: 600;
      line-height: 1.3;
      color: var(--text-main);
      letter-spacing: -0.01em;
    }}

    .slide-divider {{
      width: 40px;
      height: 2px;
      background: var(--accent-gold);
      opacity: 0.8;
    }}

    .slide-story {{
      font-size: 1.05rem;
      line-height: 1.75;
      color: #d0d0d0;
      font-weight: 300;
    }}

    .slide-controls {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-top: 1.5rem;
      border-top: 1px solid var(--border);
    }}

    .slide-counter {{
      font-size: 0.9rem;
      color: var(--text-dim);
      font-variant-numeric: tabular-nums;
    }}

    .slide-nav-buttons {{
      display: flex;
      gap: 0.75rem;
    }}

    .nav-arrow {{
      width: 48px;
      height: 48px;
      min-width: 48px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border);
      color: var(--text-main);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.2rem;
      transition: all 0.2s ease;
      touch-action: manipulation;
    }}

    .nav-arrow:hover {{
      background: var(--accent-gold);
      color: #121212;
      border-color: var(--accent-gold);
    }}

    .nav-arrow:active {{
      transform: scale(0.92);
    }}

    /* Title Screen Overlay */
    .title-slide-container {{
      position: absolute;
      inset: 0;
      background: radial-gradient(circle at center, #1e1e1e 0%, #0d0d0d 100%);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 2.5rem 1.5rem;
      z-index: 10;
    }}

    .title-slide-day {{
      font-family: var(--font-display);
      font-size: 1.25rem;
      color: var(--accent-gold);
      letter-spacing: 0.2em;
      margin-bottom: 1rem;
      text-transform: uppercase;
    }}

    .title-slide-route {{
      font-size: 2.2rem;
      font-weight: 700;
      max-width: 850px;
      line-height: 1.3;
      margin-bottom: 2rem;
      color: #fff;
    }}

    .title-slide-btn {{
      padding: 0.9rem 2.2rem;
      background: var(--accent-gold);
      color: #121212;
      border: none;
      border-radius: 999px;
      font-weight: 600;
      font-size: 1rem;
      cursor: pointer;
      box-shadow: 0 4px 20px rgba(229, 181, 103, 0.3);
      transition: transform 0.2s ease, box-shadow 0.2s ease;
      touch-action: manipulation;
    }}

    .title-slide-btn:hover {{
      transform: translateY(-2px);
      box-shadow: 0 6px 25px rgba(229, 181, 103, 0.45);
    }}

    /* 2. LONGFROM / ALBUM VIEW */
    .album-view {{
      max-width: 1000px;
      margin: 0 auto;
      padding: 3.5rem 2rem 8rem;
      -webkit-overflow-scrolling: touch;
    }}

    .album-day-section {{
      margin-bottom: 5rem;
    }}

    .album-day-header {{
      text-align: center;
      margin-bottom: 3rem;
      padding-bottom: 2rem;
      border-bottom: 1px solid var(--border);
    }}

    .album-day-tag {{
      font-family: var(--font-display);
      font-size: 0.95rem;
      color: var(--accent-gold);
      letter-spacing: 0.15em;
      text-transform: uppercase;
      margin-bottom: 0.6rem;
    }}

    .album-day-title {{
      font-size: 2.1rem;
      font-weight: 700;
      line-height: 1.3;
      color: #ffffff;
    }}

    .album-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 16px;
      margin-bottom: 3.5rem;
      overflow: hidden;
      box-shadow: 0 16px 36px rgba(0,0,0,0.4);
      transition: transform 0.3s ease, border-color 0.3s ease;
    }}

    .album-card:hover {{
      border-color: rgba(229, 181, 103, 0.3);
      transform: translateY(-3px);
    }}

    .album-image-wrapper {{
      position: relative;
      background: #000;
      width: 100%;
      height: 580px;
      cursor: zoom-in;
      overflow: hidden;
    }}

    .album-image-wrapper img, .album-image-wrapper video {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform 0.6s cubic-bezier(0.16, 1, 0.3, 1);
      display: block;
    }}

    .album-image-wrapper:hover img {{
      transform: scale(1.02);
    }}

    .album-caption {{
      padding: 2.2rem 2.5rem;
    }}

    .album-loc-title {{
      font-size: 1.45rem;
      font-weight: 600;
      color: var(--text-main);
      margin-bottom: 1rem;
      display: flex;
      align-items: baseline;
      gap: 0.5rem;
    }}

    .album-story {{
      font-size: 1.05rem;
      line-height: 1.75;
      color: #c8c8c8;
      font-weight: 300;
    }}

    /* Lightbox Modal */
    .lightbox {{
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.95);
      z-index: 3000;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 1.5rem;
      cursor: zoom-out;
    }}

    .lightbox.active {{
      display: flex;
      animation: fadeIn 0.2s ease forwards;
    }}

    .lightbox img, .lightbox video {{
      max-width: 95vw;
      max-height: 92vh;
      object-fit: contain;
      border-radius: 8px;
      box-shadow: 0 0 50px rgba(0,0,0,0.9);
    }}

    @keyframes fadeIn {{
      from {{ opacity: 0; }}
      to {{ opacity: 1; }}
    }}

    /* MOBILE FLOATING BOTTOM BAR (Thumb-friendly Navigation) */
    .mobile-bottom-bar {{
      display: none;
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      height: var(--bottom-bar-height);
      background: rgba(18, 18, 18, 0.94);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border-top: 1px solid var(--border);
      z-index: 1000;
      padding: 0 1rem;
      padding-bottom: env(safe-area-inset-bottom, 0px);
      align-items: center;
      justify-content: space-between;
      gap: 0.75rem;
    }}

    .mobile-day-selector {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
      flex: 1;
      overflow-x: auto;
      scrollbar-width: none;
      -webkit-overflow-scrolling: touch;
      padding: 4px 0;
    }}
    .mobile-day-selector::-webkit-scrollbar {{
      display: none;
    }}

    .mobile-day-pill {{
      padding: 0.45rem 0.9rem;
      min-height: 38px;
      border-radius: 999px;
      font-size: 0.85rem;
      font-weight: 500;
      color: var(--text-muted);
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border);
      white-space: nowrap;
      cursor: pointer;
      user-select: none;
      touch-action: manipulation;
    }}
    .mobile-day-pill.active {{
      color: #121212;
      background: var(--accent-gold);
      border-color: var(--accent-gold);
      font-weight: 600;
    }}

    .mobile-view-toggle {{
      display: flex;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 2px;
      min-width: 90px;
    }}
    .mobile-view-toggle button {{
      flex: 1;
      height: 38px;
      min-width: 44px;
      border: none;
      background: transparent;
      color: var(--text-muted);
      border-radius: 8px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      touch-action: manipulation;
    }}
    .mobile-view-toggle button.active {{
      background: rgba(255, 255, 255, 0.15);
      color: var(--text-main);
    }}

    /* ==========================================================================
       RESPONSIVE & MOBILE-FIRST MEDIA QUERIES (Screens < 768px & Tablets < 992px)
       ========================================================================== */
    @media (max-width: 992px) {{
      .slide-media {{
        flex: 0 0 60%;
      }}
      .slide-sidebar {{
        flex: 0 0 40%;
        padding: 2rem 1.75rem;
      }}
      .album-image-wrapper {{
        height: 460px;
      }}
    }}

    @media (max-width: 768px) {{
      /* Hide top nav day pills and toggle on mobile, show brand only */
      header.top-nav {{
        padding: 0 1rem;
        height: 54px;
      }}
      :root {{
        --nav-height: 54px;
      }}
      .nav-center, .nav-controls {{
        display: none !important;
      }}
      .mobile-bottom-bar {{
        display: flex;
      }}

      /* Slideshow in Mobile: Stack layout with touch-friendly controls */
      .slideshow-view {{
        flex-direction: column;
        bottom: var(--bottom-bar-height);
        background: #101010;
      }}

      .slide-media {{
        flex: 0 0 45vh;
        width: 100%;
        height: 45vh;
        background: #000;
        position: relative;
      }}
      .slide-media img, .slide-media video {{
        width: 100%;
        height: 100%;
        object-fit: contain;
      }}

      .video-sound-btn {{
        display: flex;
      }}

      .slide-sidebar {{
        flex: 1;
        width: 100%;
        border-left: none;
        border-top: 1px solid var(--border);
        padding: 1.25rem 1rem 1rem;
        justify-content: flex-start;
        gap: 1rem;
      }}

      .slide-meta {{
        gap: 0.75rem;
      }}

      .slide-title {{
        font-size: 1.25rem;
        line-height: 1.35;
      }}

      .slide-story {{
        font-size: 0.95rem;
        line-height: 1.6;
        color: #d8d8d8;
      }}

      .slide-controls {{
        padding-top: 0.85rem;
        margin-top: auto;
      }}

      .title-slide-container {{
        padding: 1.5rem;
      }}
      .title-slide-route {{
        font-size: 1.5rem;
        line-height: 1.35;
        margin-bottom: 1.5rem;
      }}

      /* Longform / Album in Mobile: Premium Mobile Journal */
      .album-view {{
        padding: 1.25rem 0.85rem calc(var(--bottom-bar-height) + 2rem);
      }}

      .album-day-section {{
        margin-bottom: 3.5rem;
      }}

      .album-day-header {{
        margin-bottom: 2rem;
        padding-bottom: 1.25rem;
      }}
      .album-day-title {{
        font-size: 1.45rem;
        line-height: 1.3;
      }}

      .album-card {{
        border-radius: 12px;
        margin-bottom: 2.25rem;
        border: 1px solid rgba(255, 255, 255, 0.07);
      }}

      .album-image-wrapper {{
        height: auto;
        aspect-ratio: 16 / 9;
        max-height: 60vh;
      }}

      .album-caption {{
        padding: 1.25rem 1rem 1.4rem;
      }}

      .album-loc-title {{
        font-size: 1.2rem;
        line-height: 1.35;
        margin-bottom: 0.75rem;
      }}

      .album-story {{
        font-size: 0.98rem;
        line-height: 1.65;
        color: #d0d0d0;
      }}
    }}
  </style>
</head>
<body>

  <!-- Top Navigation (Desktop / Mobile brand) -->
  <header class="top-nav" id="topNav">
    <div class="nav-brand" onclick="goToDay(0, true)">
      <span class="icon">🏔️</span> California 2026
    </div>

    <div class="nav-center" id="dayPillsContainer"></div>

    <div class="nav-controls">
      <div class="view-toggle">
        <button class="toggle-btn active" id="btnSlideshow" onclick="switchView('slideshow')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
          Слайд-шоу
        </button>
        <button class="toggle-btn" id="btnAlbum" onclick="switchView('album')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
          Фотоальбом
        </button>
      </div>
    </div>
  </header>

  <!-- View Container -->
  <main class="view-container">
    
    <!-- 1. SLIDESHOW VIEW -->
    <div class="slideshow-view" id="slideshowContainer">
      <div class="title-slide-container" id="titleSlideOverlay" style="display: none;">
        <div class="title-slide-day" id="titleDayTag">DAY 1</div>
        <div class="title-slide-route" id="titleRouteText">Маршрут дня</div>
        <button class="title-slide-btn" onclick="startDaySlides()">Смотреть историю дня</button>
      </div>

      <div class="slide-media" id="slideMediaWrapper">
        <img id="slideImg" src="" alt="Медиа экспедиции" />
        <video id="slideVideo" src="" autoplay loop muted playsinline preload="metadata" style="display:none;"></video>
        
        <!-- Touch-friendly Mute/Unmute Button -->
        <button class="video-sound-btn" id="videoSoundBtn" onclick="toggleSlideVideoAudio(event)" title="Включить / выключить звук" aria-label="Звук">
          <svg id="soundIconMuted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="1" y1="1" x2="23" y2="23"></line>
            <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6"></path>
            <path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23"></path>
            <line x1="12" y1="19" x2="12" y2="23"></line>
            <line x1="8" y1="23" x2="16" y2="23"></line>
          </svg>
          <svg id="soundIconUnmuted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display:none;">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
          </svg>
        </button>
      </div>

      <div class="slide-sidebar">
        <div class="slide-meta">
          <div class="slide-day-tag" id="slideDayTag">
            <span style="color:var(--accent-gold);">●</span> <span id="slideDayLabel">ДЕНЬ 1</span>
          </div>
          <h2 class="slide-title" id="slideTitle">Название локации</h2>
          <div class="slide-divider"></div>
          <p class="slide-story" id="slideStory">Художественное описание...</p>
        </div>

        <div class="slide-controls">
          <div class="slide-counter" id="slideCounter">1 / 15</div>
          <div class="slide-nav-buttons">
            <button class="nav-arrow" onclick="prevSlide()" title="Предыдущий (←)">←</button>
            <button class="nav-arrow" onclick="nextSlide()" title="Следующий (→ / Пробел)">→</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 2. ALBUM / LONGFROM VIEW -->
    <div class="album-view" id="albumContainer" style="display: none;"></div>

  </main>

  <!-- Mobile Floating Bottom Bar (Thumb-friendly UX) -->
  <aside class="mobile-bottom-bar" id="mobileBottomBar" aria-label="Мобильная навигация">
    <div class="mobile-day-selector" id="mobileDaySelector"></div>
    <div class="mobile-view-toggle">
      <button id="mBtnSlideshow" class="active" onclick="switchView('slideshow')" title="Слайды" aria-label="Слайды">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
      </button>
      <button id="mBtnAlbum" onclick="switchView('album')" title="Альбом" aria-label="Альбом">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
      </button>
    </div>
  </aside>

  <!-- Lightbox Modal -->
  <div class="lightbox" id="lightboxModal" onclick="closeLightbox()">
    <img id="lightboxImg" src="" alt="Zoomed" style="display:none;" />
    <video id="lightboxVideo" src="" controls autoplay loop playsinline preload="metadata" style="display:none;"></video>
  </div>

  <script>
    const daysData = {days_json};

    let currentDayIndex = 0;
    let currentSlideIndex = 0;
    let currentView = 'slideshow';

    function init() {{
      if (window.Telegram && window.Telegram.WebApp) {{
        const tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();
        tg.enableClosingConfirmation();
      }}

      renderNavPills();
      renderMobileDaySelector();
      renderAlbumView();
      setupTouchSwipes();
      goToDay(0, false);
      
      window.addEventListener('keydown', (e) => {{
        if (currentView !== 'slideshow') return;
        if (e.key === 'ArrowRight' || e.key === ' ') {{
          e.preventDefault();
          nextSlide();
        }} else if (e.key === 'ArrowLeft') {{
          e.preventDefault();
          prevSlide();
        }}
      }});
    }}

    function renderNavPills() {{
      const container = document.getElementById('dayPillsContainer');
      container.innerHTML = '';
      daysData.forEach((day, index) => {{
        const btn = document.createElement('button');
        btn.className = 'day-pill' + (index === currentDayIndex ? ' active' : '');
        btn.textContent = `День ${{day.day_num}}`;
        btn.onclick = () => goToDay(index, true);
        container.appendChild(btn);
      }});
    }}

    function renderMobileDaySelector() {{
      const container = document.getElementById('mobileDaySelector');
      container.innerHTML = '';
      daysData.forEach((day, index) => {{
        const btn = document.createElement('button');
        btn.className = 'mobile-day-pill' + (index === currentDayIndex ? ' active' : '');
        btn.textContent = `День ${{day.day_num}}`;
        btn.onclick = () => {{
          goToDay(index, true);
          btn.scrollIntoView({{ behavior: 'smooth', inline: 'center', block: 'nearest' }});
        }};
        container.appendChild(btn);
      }});
    }}

    function updatePills() {{
      const pills = document.querySelectorAll('.day-pill');
      pills.forEach((p, idx) => {{
        if (idx === currentDayIndex) p.classList.add('active');
        else p.classList.remove('active');
      }});

      const mPills = document.querySelectorAll('.mobile-day-pill');
      mPills.forEach((p, idx) => {{
        if (idx === currentDayIndex) {{
          p.classList.add('active');
          p.scrollIntoView({{ behavior: 'smooth', inline: 'center', block: 'nearest' }});
        }} else {{
          p.classList.remove('active');
        }}
      }});
    }}

    function switchView(view) {{
      currentView = view;
      const ssContainer = document.getElementById('slideshowContainer');
      const alContainer = document.getElementById('albumContainer');
      const btnSS = document.getElementById('btnSlideshow');
      const btnAL = document.getElementById('btnAlbum');
      const mBtnSS = document.getElementById('mBtnSlideshow');
      const mBtnAL = document.getElementById('mBtnAlbum');

      if (view === 'slideshow') {{
        ssContainer.style.display = 'flex';
        alContainer.style.display = 'none';
        btnSS.classList.add('active');
        btnAL.classList.remove('active');
        mBtnSS.classList.add('active');
        mBtnAL.classList.remove('active');
        updateSlideshow();
      }} else {{
        ssContainer.style.display = 'none';
        alContainer.style.display = 'block';
        btnSS.classList.remove('active');
        btnAL.classList.add('active');
        mBtnSS.classList.remove('active');
        mBtnAL.classList.add('active');
        const daySec = document.getElementById(`album-day-${{daysData[currentDayIndex].day_num}}`);
        if (daySec) {{
          daySec.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
        }}
      }}
    }}

    function goToDay(dayIndex, showTitle = true) {{
      currentDayIndex = dayIndex;
      currentSlideIndex = 0;
      updatePills();

      if (currentView === 'slideshow') {{
        if (showTitle) {{
          showDayTitleScreen();
        }} else {{
          hideDayTitleScreen();
          updateSlideshow();
        }}
      }} else {{
        const daySec = document.getElementById(`album-day-${{daysData[dayIndex].day_num}}`);
        if (daySec) {{
          daySec.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
        }}
      }}
    }}

    function showDayTitleScreen() {{
      const overlay = document.getElementById('titleSlideOverlay');
      const dayData = daysData[currentDayIndex];
      document.getElementById('titleDayTag').textContent = `ДЕНЬ ${{dayData.day_num}}`;
      document.getElementById('titleRouteText').textContent = dayData.title.replace(/^##\s*/, '');
      overlay.style.display = 'flex';
    }}

    function hideDayTitleScreen() {{
      const overlay = document.getElementById('titleSlideOverlay');
      overlay.style.display = 'none';
    }}

    function startDaySlides() {{
      hideDayTitleScreen();
      updateSlideshow();
    }}

    function updateSlideshow() {{
      const dayData = daysData[currentDayIndex];
      if (!dayData || !dayData.slides.length) return;

      const slide = dayData.slides[currentSlideIndex];
      const img = document.getElementById('slideImg');
      const video = document.getElementById('slideVideo');
      const soundBtn = document.getElementById('videoSoundBtn');
      
      if (slide.is_video) {{
        img.style.display = 'none';
        video.style.display = 'block';
        video.style.opacity = '1';
        video.src = slide.media;
        video.muted = true;
        video.load();
        video.play().catch(() => {{}});
        if (soundBtn) {{
          soundBtn.style.display = 'flex';
          updateSoundBtnState(true);
        }}
      }} else {{
        video.pause();
        video.removeAttribute('src');
        video.style.display = 'none';
        if (soundBtn) soundBtn.style.display = 'none';
        img.style.display = 'block';
        img.style.opacity = '0';
        img.src = slide.media;
        img.onload = () => {{
          img.style.opacity = '1';
        }};
      }}

      document.getElementById('slideDayLabel').textContent = `ДЕНЬ ${{dayData.day_num}}`;
      document.getElementById('slideTitle').textContent = slide.title || 'Красивая точка маршрута';
      document.getElementById('slideStory').textContent = slide.story;
      document.getElementById('slideCounter').textContent = `${{currentSlideIndex + 1}} / ${{dayData.slides.length}}`;
    }}

    function toggleSlideVideoAudio(e) {{
      if (e) e.stopPropagation();
      const video = document.getElementById('slideVideo');
      if (!video) return;
      video.muted = !video.muted;
      updateSoundBtnState(video.muted);
    }}

    function toggleCardVideoAudio(videoEl, btnEl, e) {{
      if (e) e.stopPropagation();
      if (!videoEl) return;
      videoEl.muted = !videoEl.muted;
      const isMuted = videoEl.muted;
      const mutedIcon = btnEl.querySelector('.icon-muted');
      const unmutedIcon = btnEl.querySelector('.icon-unmuted');
      if (mutedIcon && unmutedIcon) {{
        mutedIcon.style.display = isMuted ? 'block' : 'none';
        unmutedIcon.style.display = isMuted ? 'none' : 'block';
      }}
    }}

    function updateSoundBtnState(isMuted) {{
      const mutedIcon = document.getElementById('soundIconMuted');
      const unmutedIcon = document.getElementById('soundIconUnmuted');
      if (mutedIcon && unmutedIcon) {{
        mutedIcon.style.display = isMuted ? 'block' : 'none';
        unmutedIcon.style.display = isMuted ? 'none' : 'block';
      }}
    }}

    function nextSlide() {{
      const dayData = daysData[currentDayIndex];
      if (currentSlideIndex < dayData.slides.length - 1) {{
        currentSlideIndex++;
        updateSlideshow();
      }} else if (currentDayIndex < daysData.length - 1) {{
        goToDay(currentDayIndex + 1, true);
      }}
    }}

    function prevSlide() {{
      if (currentSlideIndex > 0) {{
        currentSlideIndex--;
        updateSlideshow();
      }} else if (currentDayIndex > 0) {{
        currentDayIndex--;
        currentSlideIndex = daysData[currentDayIndex].slides.length - 1;
        updatePills();
        updateSlideshow();
      }}
    }}

    /* Touch & Swiping Support for Slideshow */
    function setupTouchSwipes() {{
      const container = document.getElementById('slideshowContainer');
      let touchStartX = 0;
      let touchStartY = 0;
      let touchEndX = 0;
      let touchEndY = 0;

      container.addEventListener('touchstart', (e) => {{
        touchStartX = e.changedTouches[0].screenX;
        touchStartY = e.changedTouches[0].screenY;
      }}, {{ passive: true }});

      container.addEventListener('touchend', (e) => {{
        touchEndX = e.changedTouches[0].screenX;
        touchEndY = e.changedTouches[0].screenY;
        handleSwipe();
      }}, {{ passive: true }});

      function handleSwipe() {{
        const deltaX = touchEndX - touchStartX;
        const deltaY = touchEndY - touchStartY;
        // Check horizontal swipe gesture (min 45px, more horizontal than vertical)
        if (Math.abs(deltaX) > 45 && Math.abs(deltaX) > Math.abs(deltaY) * 1.5) {{
          if (deltaX < 0) {{
            nextSlide();
          }} else {{
            prevSlide();
          }}
        }}
      }}
    }}

    function renderAlbumView() {{
      const container = document.getElementById('albumContainer');
      container.innerHTML = '';

      daysData.forEach((day) => {{
        const section = document.createElement('section');
        section.className = 'album-day-section';
        section.id = `album-day-${{day.day_num}}`;

        const header = document.createElement('div');
        header.className = 'album-day-header';
        header.innerHTML = `
          <div class="album-day-tag">ДЕНЬ ${{day.day_num}}</div>
          <h1 class="album-day-title">${{day.title.replace(/^##\s*/, '')}}</h1>
        `;
        section.appendChild(header);

        day.slides.forEach((slide) => {{
          const card = document.createElement('div');
          card.className = 'album-card';
          
          let mediaHtml = '';
          if (slide.is_video) {{
            mediaHtml = `
              <div class="album-image-wrapper">
                <video src="${{slide.media}}" autoplay loop muted playsinline preload="metadata" onclick="openLightbox('${{slide.media}}', true)"></video>
                <button class="video-sound-btn" style="display:flex;" onclick="toggleCardVideoAudio(this.previousElementSibling, this, event)" title="Включить / выключить звук" aria-label="Звук">
                  <svg class="icon-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="1" y1="1" x2="23" y2="23"></line>
                    <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6"></path>
                    <path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23"></path>
                    <line x1="12" y1="19" x2="12" y2="23"></line>
                    <line x1="8" y1="23" x2="16" y2="23"></line>
                  </svg>
                  <svg class="icon-unmuted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display:none;">
                    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                    <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
                  </svg>
                </button>
              </div>
            `;
          }} else {{
            mediaHtml = `
              <div class="album-image-wrapper" onclick="openLightbox('${{slide.media}}', false)">
                <img src="${{slide.media}}" alt="${{slide.title}}" loading="lazy" />
              </div>
            `;
          }}

          card.innerHTML = `
            ${{mediaHtml}}
            <div class="album-caption">
              <h3 class="album-loc-title">📍 ${{slide.title}}</h3>
              <p class="album-story">${{slide.story}}</p>
            </div>
          `;
          section.appendChild(card);
        }});

        container.appendChild(section);
      }});
    }}

    function openLightbox(src, isVideo) {{
      const modal = document.getElementById('lightboxModal');
      const img = document.getElementById('lightboxImg');
      const video = document.getElementById('lightboxVideo');

      if (isVideo) {{
        img.style.display = 'none';
        video.style.display = 'block';
        video.src = src;
        video.play().catch(() => {{}});
      }} else {{
        video.pause();
        video.style.display = 'none';
        img.style.display = 'block';
        img.src = src;
      }}
      modal.classList.add('active');
    }}

    function closeLightbox() {{
      const modal = document.getElementById('lightboxModal');
      const video = document.getElementById('lightboxVideo');
      video.pause();
      modal.classList.remove('active');
    }}

    window.addEventListener('DOMContentLoaded', init);
  </script>
</body>
</html>
"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_template)
    with open(ROOT_OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"Presentation successfully generated at: {ROOT_OUTPUT_HTML} and {OUTPUT_HTML}")

if __name__ == "__main__":
    days = collect_all_days()
    print(f"Collected {len(days)} days with ready photo/video slides:")
    for d in days:
        print(f" - {d['file']}: {len(d['slides'])} slides parsed.")
    generate_html(days)
