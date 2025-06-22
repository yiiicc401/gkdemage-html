from flask import Flask, render_template, request, redirect, url_for
import os, json
import gspread
from werkzeug.utils import secure_filename
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- Flask 設定 ---
app = Flask(__name__)
UPLOAD_FOLDER = 'static/photos'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Google Sheets + Drive 認證設定 ---
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds_json_str = os.environ.get("GOOGLE_CREDENTIALS")
assert creds_json_str, "❌ 請確認已設定 GOOGLE_CREDENTIALS 環境變數！"

creds_dict = json.loads(creds_json_str)
creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)

# Google Sheets 連線
gc = gspread.authorize(creds)
sheet = gc.open("GKdemage").sheet1

# Google Drive 連線
drive_service = build('drive', 'v3', credentials=creds)
drive_folder_id = "1sjYzTtnRVi7CjBzBcr00wUe_ysULwASS"  # ← 替換為你的資料夾 ID

# --- 上傳圖片到 Google Drive 並回傳公開網址 ---
def upload_to_drive(local_path, filename):
    file_metadata = {'name': filename, 'parents': [drive_folder_id]}
    media = MediaFileUpload(local_path, resumable=True)
    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    # 設定為任何人可讀
    drive_service.permissions().create(
        fileId=file['id'],
        body={'type': 'anyone', 'role': 'reader'}
    ).execute()

    return f"https://drive.google.com/uc?id={file['id']}"

# --- 上傳頁面 ---
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        studio = request.form.get('studio')
        product = request.form.get('product')
        condition = request.form.get('condition')
        image_urls = []

        for field in ['photo1', 'photo2', 'photo3']:
            file = request.files.get(field)
            if file and file.filename:
                filename = secure_filename(file.filename)
                local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(local_path)
                url = upload_to_drive(local_path, filename)
                image_urls.append(url)
            else:
                image_urls.append('')

        # 寫入 Google Sheets
        sheet.append_row([studio, product, condition] + image_urls)
        return redirect(url_for('view'))

    return render_template('upload.html')

# --- 顯示所有上傳紀錄 ---
@app.route('/view', methods=['GET', 'POST'])
def view():
    data = sheet.get_all_records()
    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        if keyword:
            data = [row for row in data if any(keyword in str(v) for v in row.values())]
    return render_template('view.html', data=data)

# --- 讓 Render 正確監聽埠口 ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
