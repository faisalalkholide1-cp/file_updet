import os
import json
import time
import socket
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import zipfile
import tempfile

# ================= Settings =================
CONFIG_FILE = "config.json"
SCOPES = ['https://www.googleapis.com/auth/drive']
UPLOADED_LOG = "uploaded_files.txt"

# ================= Load Config =================
def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

config = load_config()

# ================= Google Auth =================
def authenticate():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)

# ================= Helpers =================
def load_uploaded_files():
    if not os.path.exists(UPLOADED_LOG):
        return set()
    with open(UPLOADED_LOG, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f.readlines())

def save_uploaded_file(filename):
    with open(UPLOADED_LOG, "a", encoding="utf-8") as f:
        f.write(filename + "\n")

def log(msg):
    output.insert(tk.END, msg + "\n")
    output.see(tk.END)

def compress_file(file_path):
    temp_dir = tempfile.gettempdir()
    file_name = os.path.basename(file_path)
    zip_path = os.path.join(temp_dir, file_name + ".zip")

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(file_path, arcname=file_name)

    return zip_path

# ================= Upload Function =================
def upload_files():
    local_path = config["local_folder"]
    drive_id = config["drive_folder_id"]

    if not os.path.exists(local_path):
        log(f"❌ المجلد المحلي غير موجود: {local_path}")
        return

    service = authenticate()
    uploaded = load_uploaded_files()

    for file in os.listdir(local_path):
        full_path = os.path.join(local_path, file)

        if os.path.isfile(full_path) and file not in uploaded:
            zip_file_path = compress_file(full_path)

            media = MediaFileUpload(zip_file_path, resumable=True)
            file_metadata = {
                'name': file + ".zip",
                'parents': [drive_id]
            }

            service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            save_uploaded_file(file)
            log(f"✅ تم رفع: {file}")

        else:
            log(f"⏭️ تم تخطي: {file}")

# ================= Auto Upload Loop =================
def internet_available():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except OSError:
        return False

def auto_upload_loop():
    while True:
        if internet_available():
            upload_files()
        time.sleep(60)  # تحقق كل دقيقة

if config.get("auto_upload"):
    threading.Thread(target=auto_upload_loop, daemon=True).start()

# ================= GUI =================
root = tk.Tk()
root.title("Google Drive Uploader")
root.geometry("600x450")

tk.Label(root, text="📁 مجلد الجهاز: " + config["local_folder"], fg="blue").pack(pady=2)
tk.Label(root, text="☁️ Google Drive Folder ID: " + config["drive_folder_id"], fg="green").pack(pady=2)

tk.Button(root, text="🚀 رفع الملفات الآن", command=upload_files).pack(pady=10)

output = scrolledtext.ScrolledText(root, width=70, height=15)
output.pack(pady=10)

root.mainloop()
