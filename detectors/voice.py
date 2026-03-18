import vosk
import json
from alert import send_alert

# 설정값
SAMPLE_RATE  = 16000
SOS_KEYWORDS = ["살려줘", "아파요", "아파", "도와줘", "도움"]

# 모델 로드
model      = vosk.Model("vosk-model-small-ko-0.22")
recognizer = vosk.KaldiRecognizer(model, SAMPLE_RATE)

def detect(audio_data):
    if recognizer.AcceptWaveform(audio_data):
        result = json.loads(recognizer.Result())
        text   = result.get("text", "")

        if text:
            print(f"인식된 말: {text}")
            for keyword in SOS_KEYWORDS:
                if keyword in text:
                    print(f"🚨 SOS 감지! 키워드: {keyword}")
                    send_alert(f"음성 SOS — '{keyword}'", "101호")
                    return True

    return False