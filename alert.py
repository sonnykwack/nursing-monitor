import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

# 여기에 본인 정보 입력해요
MY_EMAIL    = "sonny.kwack@gmail.com"
APP_PASSWORD = "zorr rbfg bmqm imzz"         # 방금 발급받은 거
NURSE_EMAIL  = "sonny.kwack@gmail.com"   # 테스트할 때는 본인 이메일로 해도 돼요
SERVER_URL   = "http://127.0.0.1:8000"

def send_alert(reason="이상 감지", room="101호"):
    # 1. 서버에 이벤트 저장
    try:
        requests.post(f"{SERVER_URL}/event", json={
            "room": room,
            "type": reason,
            "message": f"{reason}"
        })
        print(f"✅ 서버 이벤트 저장 완료")
    except Exception as e:
        print(f"❌ 서버 전송 실패: {e}")

    # 2. 이메일 알림 전송
    try:
        msg = MIMEMultipart()
        msg["From"]    = MY_EMAIL
        msg["To"]      = NURSE_EMAIL
        msg["Subject"] = f"🚨 [긴급] {room} 환자 이상 감지"

        body = f"""
안녕하세요, 요양사님.

{room} 환자 모니터링 시스템에서 이상이 감지되었습니다.

감지 내용: {reason}
즉시 확인 바랍니다.

- 스마트 요양 모니터링 시스템
        """

        msg.attach(MIMEText(body, "plain", "utf-8"))
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(MY_EMAIL, APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ 이메일 알림 전송 완료 → {NURSE_EMAIL}")

    except Exception as e:
        print(f"❌ 이메일 전송 실패: {e}")