import cv2
import pyaudio
import threading
from detectors import fall, sound, voice

# ── 음성 + 소리 감지 스레드 ─────────────────
def voice_thread_func():
    audio  = pyaudio.PyAudio()
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=4096
    )
    print("음성 + 소리 감지 시작!")

    while True:
        data = stream.read(4096, exception_on_overflow=False)
        sound.detect(data)
        voice.detect(data)

# ── 음성 백그라운드 실행 ─────────────────────
thread = threading.Thread(target=voice_thread_func, daemon=True)
thread.start()

# ── 낙상 감지 메인 루프 ──────────────────────
cap = cv2.VideoCapture(0)
print("낙상 감지 시작! 종료하려면 q를 누르세요.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = fall.detect(frame)

    cv2.imshow("Smart Nursing Monitor", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()