import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

def sync():
    print("==================================================")
    print("🚀 НАЧАЛО СКВОЗНОЙ СИНХРОНИЗАЦИИ (ONE-COMMAND SYNC)")
    print("==================================================")

    # 1. Сборка и деплой на GitHub Pages
    deploy_script = PROJECT_ROOT / "deploy_to_web.py"
    res_deploy = subprocess.run([sys.executable, str(deploy_script)], cwd=str(PROJECT_ROOT))
    if res_deploy.returncode != 0:
        print("❌ Ошибка при деплое на GitHub Pages!")
        sys.exit(1)

    # 2. Обновление кнопки и ссылки в Telegram Web App
    tg_script = PROJECT_ROOT / "scripts" / "setup_telegram_bot.py"
    if tg_script.exists():
        print("\n=== Обновление настроек Telegram Web App ===")
        res_tg = subprocess.run([sys.executable, str(tg_script)], cwd=str(PROJECT_ROOT))
        if res_tg.returncode != 0:
            print("⚠️ Предупреждение: Не удалось обновить настройки бота.")

    pages_url = "https://deorocosta-afk.github.io/usa-trip-2026/"
    print("\n==================================================")
    print(f"🎉 ВСЁ ГОТОВО!")
    print(f"Сайт обновлен: {pages_url}")
    print("Изменения уже доступны в Telegram Web App!")
    print("==================================================")

if __name__ == "__main__":
    sync()
