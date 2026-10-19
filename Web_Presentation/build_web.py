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

def parse_header_meta(raw_title):
    cleaned = re.sub(r"^[>\s]*\[!quote\]\s*", "", raw_title).strip()
    cleaned = re.sub(r"^[>\s]*📍\s*", "", cleaned).strip()
    parts = [p.strip() for p in cleaned.split("|")]
    
    first_part = parts[0] if parts else ""
    first_part = re.sub(r"[*_]{2,}", "", first_part)
    first_part = re.sub(r"[*_]", "", first_part).strip()
    
    sub_info = ""
    if len(parts) > 1:
        rest = " • ".join(parts[1:])
        rest = re.sub(r"[*_]{2,}", "", rest)
        rest = re.sub(r"[*_]", "", rest)
        sub_info = rest.strip()
    
    return first_part, sub_info

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
            
            loc_title, meta_info = parse_header_meta(raw_title)
            story = clean_story_text(story_lines)
            
            if media_file:
                slides.append({
                    "media": media_url,
                    "is_video": is_video,
                    "title": loc_title,
                    "meta": meta_info,
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
  <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,300;1,400&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-black: #000000;
      --accent-gold: #e5b567;
      --text-white: #ffffff;
      --text-muted: rgba(255, 255, 255, 0.65);
      --border-light: rgba(255, 255, 255, 0.15);
      --font-display: 'Cinzel', serif;
      --font-body: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    html, body {{
      width: 100vw;
      height: 100vh;
      height: 100svh;
      background-color: var(--bg-black);
      color: var(--text-white);
      font-family: var(--font-body);
      overflow: hidden;
      -webkit-font-smoothing: antialiased;
      -webkit-tap-highlight-color: transparent;
      user-select: none;
    }}

    /* ==========================================================================
       1. NATIVE TELEGRAM MEDIA VIEWER HEADER (Top Overlay)
       ========================================================================== */
    .tg-header-overlay {{
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      z-index: 30;
      padding: 12px 16px 18px 16px;
      padding-top: max(12px, env(safe-area-inset-top, 12px));
      background: linear-gradient(to bottom, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.5) 60%, transparent 100%);
      display: flex;
      flex-direction: column;
      gap: 6px;
      transition: opacity 0.25s ease, transform 0.25s ease, visibility 0.25s;
    }}

    .tg-header-top-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      width: 100%;
    }}

    .tg-header-left {{
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
      flex: 1;
    }}

    .tg-back-btn {{
      width: 36px;
      height: 36px;
      min-width: 36px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.1);
      border: none;
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      touch-action: manipulation;
    }}
    .tg-back-btn svg {{
      width: 20px;
      height: 20px;
    }}

    .tg-header-titles {{
      display: flex;
      flex-direction: column;
      min-width: 0;
    }}

    .tg-header-loc-title {{
      font-size: 16px;
      font-weight: 700;
      color: #ffffff;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      line-height: 1.25;
      letter-spacing: -0.01em;
      text-shadow: 0 1px 3px rgba(0,0,0,0.8);
    }}

    .tg-header-submeta {{
      font-size: 12px;
      color: var(--text-muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      line-height: 1.2;
      margin-top: 1px;
    }}

    .tg-header-right {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    .tg-icon-btn {{
      width: 38px;
      height: 38px;
      min-width: 38px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.12);
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      touch-action: manipulation;
      transition: background 0.2s ease, transform 0.2s ease;
    }}
    .tg-icon-btn:active {{
      transform: scale(0.92);
      background: rgba(255, 255, 255, 0.25);
    }}
    .tg-icon-btn svg {{
      width: 18px;
      height: 18px;
      pointer-events: none;
    }}

    /* Compact Frame Counter (like Telegram 7838 из 7845) */
    .tg-header-counter-bar {{
      text-align: center;
      font-size: 13px;
      font-weight: 500;
      color: #ffffff;
      letter-spacing: 0.2px;
      text-shadow: 0 1px 4px rgba(0,0,0,0.9);
      user-select: none;
    }}

    /* ==========================================================================
       2. CENTRAL MEDIA DISPLAY (Fit with zero cropping)
       ========================================================================== */
    .tg-media-viewport {{
      position: absolute;
      inset: 0;
      width: 100vw;
      height: 100vh;
      height: 100svh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #000000;
      overflow: hidden;
      z-index: 10;
    }}

    .tg-media-viewport img,
    .tg-media-viewport video {{
      width: 100%;
      height: 100%;
      max-width: 100%;
      max-height: 100%;
      object-fit: contain; /* Full frame fits without cropping */
      display: block;
      background: #000000;
      pointer-events: none; /* Never intercept touches/clicks from container */
    }}

    /* Circular Play/Pause Indicator (Overlay like Instagram/Telegram) */
    .tg-play-indicator {{
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 64px;
      height: 64px;
      border-radius: 50%;
      background: rgba(0, 0, 0, 0.5);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      border: 1px solid rgba(255, 255, 255, 0.2);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 15;
      pointer-events: none;
      transition: opacity 0.2s ease, transform 0.2s ease;
    }}
    .tg-play-indicator svg {{
      width: 28px;
      height: 28px;
      fill: #ffffff;
      margin-left: 3px;
    }}

    /* ==========================================================================
       3. BOTTOM OVERLAY: STORY CAPTION + CUSTOM TELEGRAM TIMELINE
       ========================================================================== */
    .tg-bottom-overlay {{
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      z-index: 30;
      padding: 8px 16px calc(env(safe-area-inset-bottom, 8px) + 8px) 16px;
      background: linear-gradient(to top, rgba(0,0,0,0.92) 0%, rgba(0,0,0,0.65) 60%, transparent 100%);
      display: flex;
      flex-direction: column;
      justify-content: flex-end;
      pointer-events: auto;
      transition: opacity 0.25s ease, transform 0.25s ease, visibility 0.25s;
    }}

    /* Caption Story Text */
    .tg-caption-story {{
      font-size: 13px;
      line-height: 1.35;
      color: #ffffff;
      text-align: left;
      font-weight: 400;
      text-shadow: 0 1px 3px rgba(0,0,0,0.9);
      user-select: text;
      margin-bottom: 6px;
      max-height: 10vh;
      overflow-y: auto;
      -webkit-overflow-scrolling: touch;
      scrollbar-width: thin;
    }}

    /* Custom Telegram Video Timeline Bar */
    .tg-video-timeline {{
      display: flex;
      align-items: center;
      gap: 12px;
      width: 100%;
      padding-top: 4px;
    }}

    .tg-timeline-track {{
      flex: 1;
      height: 4px;
      background: rgba(255, 255, 255, 0.3);
      border-radius: 999px;
      position: relative;
      cursor: pointer;
      touch-action: none;
    }}

    .tg-timeline-fill {{
      height: 100%;
      background: #ffffff;
      border-radius: 999px;
      width: 0%;
      position: relative;
    }}

    /* Telegram Circular Playhead Scrubber */
    .tg-timeline-fill::after {{
      content: '';
      position: absolute;
      right: -6px;
      top: -4px;
      width: 12px;
      height: 12px;
      background: #ffffff;
      border-radius: 50%;
      box-shadow: 0 1px 4px rgba(0,0,0,0.8);
    }}

    .tg-timeline-timer {{
      font-size: 12px;
      font-weight: 500;
      color: rgba(255, 255, 255, 0.88);
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
      user-select: none;
    }}

    /* UI HIDDEN STATE (Tap to Hide / Immersive Clean Screen) */
    .tg-header, .tg-header-overlay, .tg-bottom-overlay, .caption-overlay, .slide-caption {{
      transition: opacity 0.22s ease, transform 0.22s ease;
    }}
    body.hide-ui .tg-header,
    body.hide-ui .tg-header-overlay {{
      opacity: 0 !important;
      pointer-events: none !important;
      transform: translateY(-8px) !important;
    }}
    body.hide-ui .tg-bottom-overlay,
    body.hide-ui .caption-overlay,
    body.hide-ui .slide-caption {{
      opacity: 0 !important;
      pointer-events: none !important;
      transform: translateY(8px) !important;
    }}
    .ui-hidden {{
      opacity: 0 !important;
      pointer-events: none !important;
      transform: translateY(8px) !important;
    }}

    /* Day Picker Modal Drawer */
    .tg-modal-drawer {{
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.85);
      z-index: 200;
      display: none;
      align-items: flex-end;
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
    }}
    .tg-modal-drawer.active {{
      display: flex;
    }}
    .tg-drawer-sheet {{
      width: 100%;
      max-height: 70vh;
      background: #1c1c1c;
      border-radius: 16px 16px 0 0;
      padding: 1.5rem 1rem calc(env(safe-area-inset-bottom, 12px) + 1rem);
      display: flex;
      flex-direction: column;
      gap: 1rem;
      border-top: 1px solid var(--border-light);
    }}
    .tg-drawer-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-bottom: 0.5rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }}
    .tg-drawer-title {{
      font-size: 16px;
      font-weight: 700;
      color: var(--accent-gold);
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }}
    .tg-drawer-close {{
      background: none;
      border: none;
      color: #fff;
      font-size: 20px;
      cursor: pointer;
    }}
    .tg-drawer-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
      gap: 0.6rem;
      overflow-y: auto;
      max-height: 50vh;
    }}
    .tg-drawer-btn {{
      padding: 0.75rem 0.5rem;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 10px;
      color: #fff;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      text-align: center;
    }}
    .tg-drawer-btn.active {{
      background: var(--accent-gold);
      color: #000;
      font-weight: 700;
    }}

    /* Title Screen Overlay */
    .title-slide-container {{
      position: absolute;
      inset: 0;
      background: radial-gradient(circle at center, #1c1c1c 0%, #000000 100%);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 2.5rem 1.5rem;
      z-index: 50;
    }}

    .title-slide-day {{
      font-family: var(--font-display);
      font-size: 1.2rem;
      color: var(--accent-gold);
      letter-spacing: 0.2em;
      margin-bottom: 0.8rem;
      text-transform: uppercase;
    }}

    .title-slide-route {{
      font-size: 1.8rem;
      font-weight: 700;
      max-width: 700px;
      line-height: 1.35;
      margin-bottom: 1.8rem;
      color: #fff;
    }}

    .title-slide-btn {{
      padding: 0.85rem 2rem;
      background: var(--accent-gold);
      color: #121212;
      border: none;
      border-radius: 999px;
      font-weight: 600;
      font-size: 0.95rem;
      cursor: pointer;
      box-shadow: 0 4px 20px rgba(229, 181, 103, 0.35);
      transition: transform 0.2s ease;
      touch-action: manipulation;
    }}

    /* Album / Longform View Container */
    .album-view {{
      position: absolute;
      inset: 0;
      width: 100vw;
      height: 100vh;
      overflow-y: auto;
      background: #0d0d0d;
      padding: calc(env(safe-area-inset-top, 20px) + 50px) 1.25rem 5rem;
      z-index: 10;
      -webkit-overflow-scrolling: touch;
    }}
    .album-day-header {{
      text-align: center;
      margin-bottom: 2rem;
    }}
    .album-day-tag {{
      font-size: 12px;
      color: var(--accent-gold);
      letter-spacing: 0.15em;
      text-transform: uppercase;
    }}
    .album-day-title {{
      font-size: 1.6rem;
      font-weight: 700;
      color: #fff;
    }}
    .album-card {{
      background: #181818;
      border: 1px solid var(--border-light);
      border-radius: 12px;
      margin-bottom: 2.5rem;
      overflow: hidden;
    }}
    .album-image-wrapper {{
      width: 100%;
      height: auto;
      aspect-ratio: 16 / 9;
      background: #000;
    }}
    .album-image-wrapper img, .album-image-wrapper video {{
      width: 100%;
      height: 100%;
      object-fit: cover;
    }}
    .album-caption {{
      padding: 1.25rem 1rem;
    }}
    .album-loc-title {{
      font-size: 1.15rem;
      font-weight: 700;
      color: #fff;
      margin-bottom: 0.6rem;
    }}
    .album-story {{
      font-size: 0.95rem;
      line-height: 1.6;
      color: #d0d0d0;
    }}
  </style>
</head>
<body>

  <!-- ==========================================================================
       1. NATIVE TELEGRAM MEDIA VIEWER HEADER (Top Overlay)
       ========================================================================== -->
  <header class="tg-header-overlay" id="tgHeader">
    <div class="tg-header-top-row">
      <div class="tg-header-left">
        <button class="tg-back-btn" onclick="openDayDrawer(event)" title="Выбрать день" aria-label="Выбрать день">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"></polyline></svg>
        </button>
        <div class="tg-header-titles">
          <div class="tg-header-loc-title" id="tgLocTitle">Загрузка...</div>
          <div class="tg-header-submeta" id="tgSubMeta">Калифорния 2026</div>
        </div>
      </div>

      <div class="tg-header-right">
        <!-- Sound Mute/Unmute Button -->
        <button class="tg-icon-btn" id="tgSoundBtn" onclick="toggleSlideVideoAudio(event)" title="Звук" aria-label="Звук" style="display:none;">
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

        <!-- View Switcher (Slideshow / Album) -->
        <button class="tg-icon-btn" id="tgViewSwitchBtn" onclick="toggleViewMode(event)" title="Сменить вид" aria-label="Вид">
          <svg id="iconAlbumView" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
          <svg id="iconSlideView" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display:none;"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
        </button>
      </div>
    </div>

    <!-- Frame Counter (like Telegram 7838 из 7845) -->
    <div class="tg-header-counter-bar" id="tgCounterBar">1 из 15</div>
  </header>

  <!-- ==========================================================================
       2. CENTRAL MEDIA VIEWPORT (Full Screen Fit)
       ========================================================================== -->
  <main class="tg-media-viewport" id="tgMediaViewport">
    <div class="title-slide-container" id="titleSlideOverlay" style="display: none;">
      <div class="title-slide-day" id="titleDayTag">DAY 1</div>
      <div class="title-slide-route" id="titleRouteText">Маршрут дня</div>
      <button class="title-slide-btn" onclick="startDaySlides()">Смотреть историю дня</button>
    </div>

    <img id="slideImg" src="" alt="Медиа экспедиции" />
    <video id="slideVideo" src="" autoplay loop muted playsinline webkit-playsinline preload="metadata" style="display:none;"></video>
    
    <!-- Circular Play/Pause Indicator -->
    <div class="tg-play-indicator" id="tgPlayIndicator">
      <svg viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
    </div>
  </main>

  <!-- ==========================================================================
       3. BOTTOM OVERLAY: STORY CAPTION + TELEGRAM TIMELINE
       ========================================================================== -->
  <footer class="tg-bottom-overlay" id="tgBottom">
    <div class="tg-caption-story" id="tgStoryText">Художественное описание...</div>
    
    <div class="tg-video-timeline" id="tgTimeline">
      <div class="tg-timeline-track" id="tgTimelineTrack">
        <div class="tg-timeline-fill" id="tgTimelineFill"></div>
      </div>
      <div class="tg-timeline-timer" id="tgTimelineTimer">00:00 / 00:00</div>
    </div>
  </footer>

  <!-- ==========================================================================
       4. DAY PICKER DRAWER MODAL
       ========================================================================== -->
  <div class="tg-modal-drawer" id="tgDrawerModal" onclick="closeDayDrawer()">
    <div class="tg-drawer-sheet" onclick="event.stopPropagation()">
      <div class="tg-drawer-header">
        <div class="tg-drawer-title">Выбор дня экспедиции</div>
        <button class="tg-drawer-close" onclick="closeDayDrawer()">✕</button>
      </div>
      <div class="tg-drawer-grid" id="tgDrawerGrid"></div>
    </div>
  </div>

  <!-- 5. LONGFROM ALBUM VIEW (Optional Scrollable Mode) -->
  <div class="album-view" id="albumContainer" style="display: none;"></div>

  <script>
    const daysData = {days_json};

    let currentDayIndex = 0;
    let currentSlideIndex = 0;
    let currentView = 'slideshow';
    let isUiHidden = false;

    function init() {{
      if (window.Telegram && window.Telegram.WebApp) {{
        const tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();
        tg.enableClosingConfirmation();
      }}

      renderDayDrawer();
      renderAlbumView();
      setupTouchAndTap();
      setupTimelineSeeking();
      goToDay(0, false);
      
      window.addEventListener('keydown', (e) => {{
        if (currentView !== 'slideshow') return;
        if (e.key === 'ArrowRight' || e.key === ' ') {{
          e.preventDefault();
          nextSlide();
        }} else if (e.key === 'ArrowLeft') {{
          e.preventDefault();
          prevSlide();
        }} else if (e.key === 't' || e.key === 'T') {{
          toggleUiVisibility();
        }}
      }});
    }}

    function renderDayDrawer() {{
      const grid = document.getElementById('tgDrawerGrid');
      grid.innerHTML = '';
      daysData.forEach((day, index) => {{
        const btn = document.createElement('button');
        btn.className = 'tg-drawer-btn' + (index === currentDayIndex ? ' active' : '');
        btn.textContent = `День ${{day.day_num}}`;
        btn.onclick = () => {{
          goToDay(index, true);
          closeDayDrawer();
        }};
        grid.appendChild(btn);
      }});
    }}

    function updateDrawerSelection() {{
      const btns = document.querySelectorAll('.tg-drawer-btn');
      btns.forEach((b, idx) => {{
        if (idx === currentDayIndex) b.classList.add('active');
        else b.classList.remove('active');
      }});
    }}

    function openDayDrawer(e) {{
      if (e) e.stopPropagation();
      document.getElementById('tgDrawerModal').classList.add('active');
    }}

    function closeDayDrawer() {{
      document.getElementById('tgDrawerModal').classList.remove('active');
    }}

    function toggleViewMode(e) {{
      if (e) e.stopPropagation();
      switchView(currentView === 'slideshow' ? 'album' : 'slideshow');
    }}

    function switchView(view) {{
      currentView = view;
      const ssViewport = document.getElementById('tgMediaViewport');
      const alContainer = document.getElementById('albumContainer');
      const iconAlbum = document.getElementById('iconAlbumView');
      const iconSlide = document.getElementById('iconSlideView');
      const bottomOverlay = document.getElementById('tgBottom');

      if (view === 'slideshow') {{
        ssViewport.style.display = 'flex';
        bottomOverlay.style.display = 'flex';
        alContainer.style.display = 'none';
        iconAlbum.style.display = 'block';
        iconSlide.style.display = 'none';
        updateSlideshow();
      }} else {{
        ssViewport.style.display = 'none';
        bottomOverlay.style.display = 'none';
        alContainer.style.display = 'block';
        iconAlbum.style.display = 'none';
        iconSlide.style.display = 'block';
        if (isUiHidden) toggleUiVisibility();
        const daySec = document.getElementById(`album-day-${{daysData[currentDayIndex].day_num}}`);
        if (daySec) {{
          daySec.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
        }}
      }}
    }}

    function goToDay(dayIndex, showTitle = true) {{
      currentDayIndex = dayIndex;
      currentSlideIndex = 0;
      updateDrawerSelection();

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

    function formatTime(seconds) {{
      if (isNaN(seconds)) return "00:00";
      const m = Math.floor(seconds / 60);
      const s = Math.floor(seconds % 60);
      return `${{m.toString().padStart(2, '0')}}:${{s.toString().padStart(2, '0')}}`;
    }}

    function updateSlideshow() {{
      const dayData = daysData[currentDayIndex];
      if (!dayData || !dayData.slides.length) return;

      const slide = dayData.slides[currentSlideIndex];
      const img = document.getElementById('slideImg');
      const video = document.getElementById('slideVideo');
      const soundBtn = document.getElementById('tgSoundBtn');
      const timeline = document.getElementById('tgTimeline');
      const timelineFill = document.getElementById('tgTimelineFill');
      const timelineTimer = document.getElementById('tgTimelineTimer');
      const playIndicator = document.getElementById('tgPlayIndicator');
      
      playIndicator.style.display = 'none';

      if (slide.is_video) {{
        img.style.display = 'none';
        video.style.display = 'block';
        video.style.opacity = '1';
        video.src = slide.media;
        video.muted = true;
        video.load();
        video.play().catch(() => {{}});
        soundBtn.style.display = 'flex';
        updateSoundBtnState(true);
        timeline.style.display = 'flex';
        timelineFill.style.width = '0%';
        
        video.onloadedmetadata = () => {{
          timelineTimer.textContent = `00:00 / ${{formatTime(video.duration)}}`;
        }};

        video.ontimeupdate = () => {{
          if (video.duration) {{
            const pct = (video.currentTime / video.duration) * 100;
            timelineFill.style.width = `${{pct}}%`;
            timelineTimer.textContent = `${{formatTime(video.currentTime)}} / ${{formatTime(video.duration)}}`;
          }}
        }};

        video.onpause = () => {{
          playIndicator.style.display = 'flex';
        }};
        video.onplay = () => {{
          playIndicator.style.display = 'none';
        }};
      }} else {{
        video.pause();
        video.removeAttribute('src');
        video.style.display = 'none';
        video.ontimeupdate = null;
        soundBtn.style.display = 'none';
        timeline.style.display = 'none';

        img.style.display = 'block';
        img.style.opacity = '0';
        img.src = slide.media;
        img.onload = () => {{
          img.style.opacity = '1';
        }};
      }}

      // Top Header Info
      document.getElementById('tgLocTitle').textContent = slide.title || `День ${{dayData.day_num}}`;
      document.getElementById('tgSubMeta').textContent = slide.meta ? `ДЕНЬ ${{dayData.day_num}} • ${{slide.meta}}` : `ДЕНЬ ${{dayData.day_num}} • Экспедиция 2026`;
      document.getElementById('tgCounterBar').textContent = `${{currentSlideIndex + 1}} из ${{dayData.slides.length}}`;

      // Bottom Story Text
      document.getElementById('tgStoryText').textContent = slide.story;
    }}

    function setupTimelineSeeking() {{
      const track = document.getElementById('tgTimelineTrack');
      let isSeeking = false;

      function seek(e) {{
        const video = document.getElementById('slideVideo');
        if (!video || !video.duration) return;
        const rect = track.getBoundingClientRect();
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clickX = clientX - rect.left;
        const pct = Math.max(0, Math.min(1, clickX / rect.width));
        video.currentTime = pct * video.duration;
      }}

      track.addEventListener('mousedown', (e) => {{
        isSeeking = true;
        seek(e);
      }});
      window.addEventListener('mousemove', (e) => {{
        if (isSeeking) seek(e);
      }});
      window.addEventListener('mouseup', () => {{
        isSeeking = false;
      }});

      track.addEventListener('touchstart', (e) => {{
        isSeeking = true;
        seek(e);
      }}, {{ passive: true }});
      window.addEventListener('touchmove', (e) => {{
        if (isSeeking) seek(e);
      }}, {{ passive: true }});
      window.addEventListener('touchend', () => {{
        isSeeking = false;
      }});
    }}

    function toggleSlideVideoAudio(e) {{
      if (e) e.stopPropagation();
      const video = document.getElementById('slideVideo');
      if (!video) return;
      video.muted = !video.muted;
      updateSoundBtnState(video.muted);
    }}

    function updateSoundBtnState(isMuted) {{
      const mutedIcon = document.getElementById('soundIconMuted');
      const unmutedIcon = document.getElementById('soundIconUnmuted');
      if (mutedIcon && unmutedIcon) {{
        mutedIcon.style.display = isMuted ? 'block' : 'none';
        unmutedIcon.style.display = isMuted ? 'none' : 'block';
      }}
    }}

    /* Toggle UI overlay on tap (Native Telegram Media Viewer Immersive Mode) */
    function toggleUiVisibility() {{
      if (currentView !== 'slideshow') return;
      isUiHidden = !isUiHidden;
      document.body.classList.toggle('hide-ui', isUiHidden);
      const header = document.getElementById('tgHeader');
      const bottom = document.getElementById('tgBottom');
      if (header) header.classList.toggle('ui-hidden', isUiHidden);
      if (bottom) bottom.classList.toggle('ui-hidden', isUiHidden);
    }}

    function nextSlide(e) {{
      if (e) e.stopPropagation();
      const dayData = daysData[currentDayIndex];
      if (currentSlideIndex < dayData.slides.length - 1) {{
        currentSlideIndex++;
        updateSlideshow();
      }} else if (currentDayIndex < daysData.length - 1) {{
        goToDay(currentDayIndex + 1, true);
      }}
    }}

    function prevSlide(e) {{
      if (e) e.stopPropagation();
      if (currentSlideIndex > 0) {{
        currentSlideIndex--;
        updateSlideshow();
      }} else if (currentDayIndex > 0) {{
        currentDayIndex--;
        currentSlideIndex = daysData[currentDayIndex].slides.length - 1;
        updateSlideshow();
      }}
    }}

    /* Touch Swiping and Single Tap Detection for Slideshow */
    function setupTouchAndTap() {{
      let touchStartX = 0;
      let touchStartY = 0;
      let touchStartTime = 0;
      let lastTouchEndTime = 0;

      // Handle touch on mobile
      document.addEventListener('touchstart', (e) => {{
        if (currentView !== 'slideshow') return;
        const titleOverlay = document.getElementById('titleSlideOverlay');
        if (titleOverlay && titleOverlay.style.display === 'flex') return;
        if (e.target.closest('#tgDrawerModal')) return;

        touchStartX = e.changedTouches[0].clientX;
        touchStartY = e.changedTouches[0].clientY;
        touchStartTime = Date.now();
      }}, {{ passive: true }});

      document.addEventListener('touchend', (e) => {{
        if (currentView !== 'slideshow') return;
        const titleOverlay = document.getElementById('titleSlideOverlay');
        if (titleOverlay && titleOverlay.style.display === 'flex') return;
        if (e.target.closest('#tgDrawerModal')) return;

        const touchEndX = e.changedTouches[0].clientX;
        const touchEndY = e.changedTouches[0].clientY;
        const duration = Date.now() - touchStartTime;
        const deltaX = touchEndX - touchStartX;
        const deltaY = touchEndY - touchStartY;
        lastTouchEndTime = Date.now();

        // 1. Horizontal Swipe (min 40px)
        if (Math.abs(deltaX) > 40 && Math.abs(deltaX) > Math.abs(deltaY) * 1.5) {{
          if (deltaX < 0) {{
            nextSlide();
          }} else {{
            prevSlide();
          }}
          return;
        }}

        // 2. Short Single Tap (< 300ms, displacement < 12px)
        if (Math.abs(deltaX) < 12 && Math.abs(deltaY) < 12 && duration < 300) {{
          const target = e.target;
          // Ignore tap ONLY if clicked directly on control buttons or timeline scrubber
          if (target.closest('.tg-icon-btn') || 
              target.closest('.tg-back-btn') || 
              target.closest('.tg-timeline-track') || 
              target.closest('.title-slide-btn') || 
              target.closest('input[type="range"]') ||
              target.closest('button')) {{
            return;
          }}
          // In all other cases (video, photo, background or story caption):
          toggleUiVisibility();
        }}
      }}, {{ passive: true }});

      // Desktop Click support (with ghost-click protection from touch)
      document.addEventListener('click', (e) => {{
        if (currentView !== 'slideshow') return;
        if (Date.now() - lastTouchEndTime < 400) return; // Prevent double-trigger on touch devices

        const titleOverlay = document.getElementById('titleSlideOverlay');
        if (titleOverlay && titleOverlay.style.display === 'flex') return;

        const target = e.target;
        if (target.closest('#tgDrawerModal') || 
            target.closest('.tg-icon-btn') || 
            target.closest('.tg-back-btn') || 
            target.closest('.tg-timeline-track') || 
            target.closest('.title-slide-btn') || 
            target.closest('input[type="range"]') ||
            target.closest('button')) {{
          return;
        }}

        toggleUiVisibility();
      }});
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
                <video src="${{slide.media}}" autoplay loop muted playsinline webkit-playsinline preload="metadata"></video>
              </div>
            `;
          }} else {{
            mediaHtml = `
              <div class="album-image-wrapper">
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
