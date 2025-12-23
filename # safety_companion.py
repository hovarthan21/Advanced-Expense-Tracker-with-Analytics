# safety_companion.py
import json
import socket
import time
import queue
import threading
from vosk import Model, KaldiRecognizer
import sounddevice as sd
import numpy as np
import sys
import os

# ---------- CONFIG ----------
MODEL_PATH = "model"  # path to vosk model directory
SAMPLE_RATE = 16000
CHANNELS = 1
KEYWORDS = {"help", "emergency", "stop", "save me", "rape", "abuse", "leave me alone", "get out"}  # add local-language words here
MULTICAST_GROUP = "239.255.0.1"  # local multicast address (private)
MULTICAST_PORT = 5007
ALERT_TTL = 1  # 1 = local network only
ALERT_COOLDOWN = 30  # seconds before re-alerting (avoid spamming)
NODE_ID = socket.gethostname()  # uniquely identify device; replace with UUID in prod
# ----------------------------

if not os.path.isdir(MODEL_PATH):
    print(f"Model directory not found at {MODEL_PATH}. Please download a VOSK model and set MODEL_PATH.")
    sys.exit(1)

model = Model(MODEL_PATH)
rec = KaldiRecognizer(model, SAMPLE_RATE)
rec.SetWords(True)

audio_q = queue.Queue()

def audio_callback(indata, frames, time_info, status):
    if status:
        # non-fatal audio warnings
        print("Sounddevice status:", status, file=sys.stderr)
    # convert to bytes for VOSK
    audio_q.put(bytes(indata))

def start_listening():
    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize = 8000, dtype='int16',
                           channels=CHANNELS, callback=audio_callback):
        print("Listening (press Ctrl+C to stop)...")
        last_alert = 0
        while True:
            try:
                data = audio_q.get()
            except KeyboardInterrupt:
                break
            if rec.AcceptWaveform(data):
                res = rec.Result()
                # res is JSON string
                j = json.loads(res)
                text = j.get("text", "").strip().lower()
                if text:
                    print(f"Recognized: {text}")
                    if detect_keywords(text) and (time.time() - last_alert) > ALERT_COOLDOWN:
                        last_alert = time.time()
                        alert_payload = build_alert(text)
                        print("Triggering local alert:", alert_payload)
                        send_udp_multicast(json.dumps(alert_payload).encode('utf-8'))
                        play_local_alarm()
                        write_local_alert_file(alert_payload)
            else:
                # partial result is available if you want
                # partial = json.loads(rec.PartialResult())
                pass

def detect_keywords(text):
    # Simple approach: check if any keyword token in recognized phrase
    # For production, use Fuzzy match or multilingual keywords.
    for kw in KEYWORDS:
        if kw in text:
            return True
    return False

def build_alert(text):
    # Build alert data. Add GPS/metadata if available.
    payload = {
        "type": "distress_alert",
        "node_id": NODE_ID,
        "timestamp": int(time.time()),
        "detected_phrase": text,
        "language": "undetermined"
    }
    return payload

def send_udp_multicast(message_bytes):
    """Send a UDP multicast alert to local network."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    # set TTL to local network only
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ALERT_TTL)
    try:
        sock.sendto(message_bytes, (MULTICAST_GROUP, MULTICAST_PORT))
        print(f"Sent multicast to {MULTICAST_GROUP}:{MULTICAST_PORT}")
    except Exception as e:
        print("Failed to send multicast:", e)
    finally:
        sock.close()

def play_local_alarm():
    # Simple beep on terminal (cross-platform simple)
    try:
        print("\a")  # system bell — not guaranteed to be audible everywhere
    except Exception:
        pass

def write_local_alert_file(payload):
    try:
        fn = f"distress_alert_{int(time.time())}.json"
        with open(fn, "w") as f:
            json.dump(payload, f)
        print("Wrote local alert file:", fn)
    except Exception as e:
        print("Failed to write alert file:", e)

if _name_ == "_main_":
    print("AI Women Safety Companion — Prototype")
    print("Keywords:", KEYWORDS)
    try:
        start_listening()
    except KeyboardInterrupt:
        print("Stopping...")
        sys.exit(0)