"""Optional USB-serial bridge for the current Arduino packet:
   humidity,temperature,mq2,mq135#
Run this on a laptop connected to the Arduino Nano by USB. It forwards fields
1..4 to ThingSpeak. Do not run this if the ESP8266 already uploads the same data.
"""
import os, time
import requests
import serial

PORT = os.getenv("ARDUINO_PORT", "COM4")  # Linux example: /dev/ttyUSB0
BAUD = int(os.getenv("ARDUINO_BAUD", "9600"))
WRITE_KEY = os.environ["THINGSPEAK_WRITE_KEY"]
POST_URL = "https://api.thingspeak.com/update"
MIN_UPLOAD_INTERVAL = 20  # seconds; leave a margin between cloud updates

ser = serial.Serial(PORT, BAUD, timeout=2)
time.sleep(2)
last_sent = 0.0
print(f"Listening on {PORT} at {BAUD} baud. Press Ctrl+C to stop.")

while True:
    line = ser.readline().decode("utf-8", errors="ignore").strip()
    if not line or "#" not in line:
        continue
    payload = line.split("#", 1)[0]
    parts = [p.strip() for p in payload.split(",")]
    if len(parts) != 4:
        print("Skipped malformed packet:", line)
        continue
    try:
        humidity, temperature, mq2, mq135 = [float(p) for p in parts]
    except ValueError:
        print("Skipped non-numeric packet:", line)
        continue
    wait = MIN_UPLOAD_INTERVAL - (time.time() - last_sent)
    if wait > 0:
        time.sleep(wait)
    try:
        response = requests.post(POST_URL, data={
            "api_key": WRITE_KEY,
            "field1": humidity,
            "field2": temperature,
            "field3": mq2,
            "field4": mq135,
        }, timeout=10)
        response.raise_for_status()
        print("Uploaded entry:", response.text, "|", parts)
        last_sent = time.time()
    except requests.RequestException as exc:
        print("Upload failed:", exc)
