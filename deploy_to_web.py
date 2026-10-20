import os
import sys
import subprocess
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent

def run_cmd(cmd, check=True):
    print(f"Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, errors="replace")
    if res.stdout:
        print(res.stdout.strip())
    if res.stderr and res.returncode != 0:
        print("ERROR:", res.stderr.strip())
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed with code {res.returncode}")
    return res

def deploy():
    print("=== ЭТАП 1: Сборка веб-презентации ===")
    build_script = PROJECT_ROOT / "Web_Presentation" / "build_web.py"
    run_cmd([sys.executable, str(build_script)])

    print("\n=== ЭТАП 2: Подготовка Git и коммит ===")
    run_cmd(["git", "add", "index.html", "Photos_web", "Web_Presentation", "Notes", ".gitignore", "scripts", "deploy_to_web.py", "sync_all.py"])
    
    # Check if anything to commit
    status = run_cmd(["git", "status", "--porcelain"], check=False)
    if status.stdout.strip():
        run_cmd(["git", "commit", "-m", "Откат к чистой веб-презентации без Telegram UI"])
    else:
        print("Нет новых изменений для коммита.")

    print("\n=== ЭТАП 3: Публикация на GitHub Pages ===")
    run_cmd(["git", "push", "-u", "origin", "main"])

    print("\n=== Готово! ===")
    pages_url = "https://deorocosta-afk.github.io/usa-trip-2026/"
    print(f"Сайт опубликован и доступен по адресу: {pages_url}")
    return pages_url

if __name__ == "__main__":
    deploy()
