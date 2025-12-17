#!/usr/bin/env python3
import os
import time
import subprocess
import signal
import sys
import errno

DEVICE = os.environ.get("P910ND_DEVICE", "/dev/usb/lp0")
PORT = os.environ.get("P910ND_PORT", "0")      # 0 => TCP 9100
BIDI = os.environ.get("P910ND_BIDI", "0")
CHECK_INTERVAL = float(os.environ.get("CHECK_INTERVAL", "5"))
RESTART_DELAY = float(os.environ.get("RESTART_DELAY", "2"))

proc = None
stopping = False


def build_cmd():
    # p910nd [-f device] [-i bindaddr] [-bvd] [0|1|2]
    cmd = ["p910nd", "-f", DEVICE]   # poprawne użycie -f device

    if BIDI == "1":
        cmd.append("-b")             # bidirectional, jeśli włączone

    cmd.append("-d")                 # foreground (logi na stdout)
    cmd.append(PORT)                 # numer portu: 0, 1 lub 2

    return cmd


def device_available(path: str) -> bool:
    """Sprawdź, czy urządzenie istnieje i daje się otworzyć."""
    if not os.path.exists(path):
        return False
    try:
        fd = os.open(path, os.O_WRONLY | os.O_NONBLOCK)
        os.close(fd)
        return True
    except OSError as e:
        # Typowe: EIO, ENODEV, EBUSY – traktujemy jako chwilowy brak
        print(f"[watcher] Device {path} not usable yet: {e}", flush=True)
        return False


def start_p910nd():
    global proc
    cmd = build_cmd()
    print(f"[watcher] Starting p910nd: {' '.join(cmd)}", flush=True)
    proc = subprocess.Popen(cmd)


def stop_p910nd():
    global proc
    if proc and proc.poll() is None:
        print("[watcher] Stopping p910nd", flush=True)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("[watcher] Killing p910nd (no response to SIGTERM)", flush=True)
            proc.kill()
    proc = None


def handle_signal(signum, frame):
    global stopping
    print(f"[watcher] Got signal {signum}, shutting down", flush=True)
    stopping = True
    stop_p910nd()
    sys.exit(0)


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

print(f"[watcher] Config:")
print(f"  DEVICE         = {DEVICE}")
print(f"  PORT           = {PORT} (TCP {9100 + int(PORT)})")
print(f"  BIDI           = {BIDI}")
print(f"  CHECK_INTERVAL = {CHECK_INTERVAL}s")
print(f"  RESTART_DELAY  = {RESTART_DELAY}s", flush=True)

while True:
    if stopping:
        break

    # jeśli urządzenie nie istnieje albo nie daje się otworzyć – zatrzymaj p910nd
    if not device_available(DEVICE):
        if proc and proc.poll() is None:
            print(f"[watcher] Device {DEVICE} disappeared or not usable, stopping p910nd", flush=True)
            stop_p910nd()
        print(f"[watcher] Waiting for device {DEVICE} ...", flush=True)
        time.sleep(CHECK_INTERVAL)
        continue

    # jeśli p910nd nie działa, uruchom ponownie
    if proc is None or proc.poll() is not None:
        if proc and proc.poll() is not None:
            print(f"[watcher] p910nd exited with code {proc.returncode}, restarting after {RESTART_DELAY}s...", flush=True)
            time.sleep(RESTART_DELAY)
        start_p910nd()

    time.sleep(CHECK_INTERVAL)
