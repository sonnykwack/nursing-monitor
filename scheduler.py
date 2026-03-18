import schedule
import time
import sqlite3
from utils.report import generate_report

# ── DB에서 설정 읽기 ─────────────────────────
def get_settings():
    conn   = sqlite3.connect("events.db")
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    rows   = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

# ── 리포트 생성 ──────────────────────────────
def weekly_report():
    print("📋 자동 리포트 생성 시작...")
    filename = generate_report()
    print(f"✅ 완료 → {filename}")

# ── 스케줄 등록 ──────────────────────────────
def setup_schedule():
    schedule.clear()
    settings = get_settings()

    interval = settings.get("report_interval", "weekly")
    at_time  = settings.get("report_time",     "09:00")
    day      = settings.get("report_day",      "monday")

    if interval == "daily":
        schedule.every().day.at(at_time).do(weekly_report)
        print(f"⏰ 매일 {at_time} 에 리포트 생성")

    elif interval == "weekly":
        getattr(schedule.every(), day).at(at_time).do(weekly_report)
        print(f"⏰ 매주 {day} {at_time} 에 리포트 생성")

    elif interval == "monthly":
        schedule.every(30).days.at(at_time).do(weekly_report)
        print(f"⏰ 매월 {at_time} 에 리포트 생성")

# ── 메인 루프 ────────────────────────────────
setup_schedule()
print("종료하려면 Ctrl+C 를 누르세요.")

last_settings = get_settings()

while True:
    # 설정 변경 감지 — 변경되면 스케줄 재등록
    current_settings = get_settings()
    if current_settings != last_settings:
        print("⚙️  설정 변경 감지! 스케줄 재등록 중...")
        setup_schedule()
        last_settings = current_settings

    schedule.run_pending()
    time.sleep(30)