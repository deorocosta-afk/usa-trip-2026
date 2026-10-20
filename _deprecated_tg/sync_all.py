import sys
import subprocess
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent

def sync():
    print("==================================================")
    print("🚀 СБОРКА И ПУБЛИКАЦИЯ ВЕБ-ПРЕЗЕНТАЦИИ")
    print("==================================================")

    # 1. Сборка и деплой на GitHub Pages
    deploy_script = PROJECT_ROOT / "deploy_to_web.py"
    res_deploy = subprocess.run([sys.executable, str(deploy_script)], cwd=str(PROJECT_ROOT))
    if res_deploy.returncode != 0:
        print("❌ Ошибка при деплое!")
        sys.exit(1)

    pages_url = "https://deorocosta-afk.github.io/usa-trip-2026/"
    print("\n==================================================")
    print(f"🎉 ВСЁ ГОТОВО!")
    print(f"Сайт обновлен: {pages_url}")
    print("==================================================")

if __name__ == "__main__":
    sync()
