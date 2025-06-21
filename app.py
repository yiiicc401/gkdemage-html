from flask import Flask, render_template, request, redirect, url_for
import os
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from werkzeug.utils import secure_filename

# Flask 基本設定
app = Flask(__name__)
UPLOAD_FOLDER = 'static/photos'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ✅ 建立 Google Sheets API 連線（從環境變數）
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# 從 Render 環境變數讀取 credentials.json 的內容
creds_json_str = os.environ.get("GOOGLE_CREDENTIALS")

# 轉換成 dict 後建立憑證物件
creds_dict = json.loads(creds_json_str)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

client = gspread.authorize(creds)
sheet = client.open("GKdemage").sheet1  # 預設工作表1

# 🔼 上傳表單頁
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        studio = request.form.get('studio')
        product = request.form.get('product')
        condition = request.form.get('condition')
        filenames = []

        for field in ['photo1', 'photo2', 'photo3']:
            file = request.files.get(field)
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                filenames.append(filename)
            else:
                filenames.append('')  # 保持欄位空白

        # 寫入 Google Sheets
        sheet.append_row([studio, product, condition] + filenames)
        return redirect(url_for('view'))

    return render_template('upload.html')

# 👁 顯示資料頁
@app.route('/view', methods=['GET', 'POST'])
def view():
    data = sheet.get_all_records()

    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        if keyword:
            data = [row for row in data if any(keyword in str(value) for value in row.values())]

    return render_template('view.html', data=data)

if __name__ == '__main__':
    app.run(debug=True)
