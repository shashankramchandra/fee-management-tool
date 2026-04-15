"""
RPS Fee Management — Server Watcher
Runs silently (no window). Starts app.py and auto-restarts if it ever dies.
"""
import subprocess, sys, os, time, socket

APP_DIR = os.path.dirname(os.path.abspath(__file__))
APP_PY  = os.path.join(APP_DIR, "app.py")
PYTHON  = sys.executable

# If we're running as pythonw, switch to python for subprocess (has no console either way)
if PYTHON.lower().endswith('pythonw.exe'):
    PYTHON = PYTHON[:-1].rstrip('w') + '.exe'
    if not os.path.exists(PYTHON):
        PYTHON = sys.executable

def is_port_open(port=5000):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except:
        return False

def start_server():
    kwargs = {"cwd": APP_DIR}
    # Hide any window on Windows
    if sys.platform == "win32":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0  # SW_HIDE
        kwargs["startupinfo"] = si
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.Popen([PYTHON, APP_PY], **kwargs)

proc = None
while True:
    if proc is None or proc.poll() is not None:
        proc = start_server()
        time.sleep(4)
    else:
        time.sleep(5)
        if not is_port_open(5000):
            try: proc.kill()
            except: pass
            proc = None
