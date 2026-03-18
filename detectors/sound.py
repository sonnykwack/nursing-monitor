import numpy as np
import librosa
import threading
from alert import send_alert

# 설정값
SAMPLE_RATE      = 16000
SCREAM_DB        = 70
IMPACT_THRESHOLD = 0.6

# 상태 변수
sound_alert_sent = False
sound_lock       = threading.Lock()

def get_db(audio_data):
    samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
    if np.max(np.abs(samples)) == 0:
        return 0
    rms = np.sqrt(np.mean(samples ** 2))
    return 20 * np.log10(rms + 1e-10)

def detect(audio_data):
    global sound_alert_sent

    samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
    samples = samples / 32768.0
    db      = get_db(audio_data)

    # 비명 감지
    if db > SCREAM_DB:
        freqs    = np.fft.rfftfreq(len(samples), d=1.0 / SAMPLE_RATE)
        fft_vals = np.abs(np.fft.rfft(samples))
        high_freq_energy = np.sum(fft_vals[(freqs > 1000) & (freqs < 4000)])
        total_energy     = np.sum(fft_vals) + 1e-10

        if high_freq_energy / total_energy > 0.4:
            with sound_lock:
                if not sound_alert_sent:
                    print(f"🚨 비명 감지! dB: {db:.1f}")
                    send_alert("비명 감지 — 즉시 확인 바랍니다", "101호")
                    sound_alert_sent = True
            return

    # 낙상 충격음 감지
    if len(samples) > 0:
        onset_strength = librosa.onset.onset_strength(
            y=samples, sr=SAMPLE_RATE
        )
        if np.max(onset_strength) > IMPACT_THRESHOLD and db > 50:
            with sound_lock:
                if not sound_alert_sent:
                    print(f"🚨 낙상 충격음 감지! dB: {db:.1f}")
                    send_alert("낙상 충격음 감지 — 즉시 확인 바랍니다", "101호")
                    sound_alert_sent = True
            return

    # 조용해지면 초기화
    if db < 30:
        with sound_lock:
            sound_alert_sent = False