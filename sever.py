
from flask import Flask, send_file, request, abort
import os

app = Flask(__name__)

# Đường dẫn đến file ZIP
ZIP_PATH = os.path.join(os.path.dirname(__file__), 'files', 'KHSX_LOG.exe')
ZIP_PATH1 = os.path.join(os.path.dirname(__file__), 'files', 'app.zip')

@app.route('/app', methods=['GET'])
def download_exe():
    if not os.path.exists(ZIP_PATH):
        abort(404, description="File không tồn tại.")

    # Gợi ý tên file tải về, có thể lấy từ query: /download?name=myfile.zip
    filename = request.args.get('name', os.path.basename(ZIP_PATH))

    # Thiết lập headers để trình duyệt tải về file
    # as_attachment=True sẽ set Content-Disposition: attachment; filename=...
    # download_name (Flask>=2.0) đảm bảo tên file hiển thị đúng
    return send_file(
        ZIP_PATH,
        as_attachment=True,
        download_name=filename,
        mimetype='application/app',        # Content-Type đúng cho zip
        conditional=True                   # Hỗ trợ If-None-Match/If-Modified-Since (caching) + Range
    )

@app.route('/zip', methods=['GET'])
def download_zip():
    if not os.path.exists(ZIP_PATH1):
        abort(404, description="File không tồn tại.")

    # Gợi ý tên file tải về, có thể lấy từ query: /download?name=myfile.zip
    filename = request.args.get('name', os.path.basename(ZIP_PATH1))

    # Thiết lập headers để trình duyệt tải về file
    # as_attachment=True sẽ set Content-Disposition: attachment; filename=...
    # download_name (Flask>=2.0) đảm bảo tên file hiển thị đúng
    return send_file(
        ZIP_PATH1,
        as_attachment=True,
        download_name=filename,
        mimetype='application/zip',        # Content-Type đúng cho zip
        conditional=True                   # Hỗ trợ If-None-Match/If-Modified-Since (caching) + Range
    )

if __name__ == '__main__':
    # Chạy development server
    app.run(host='0.0.0.0', port=5000, debug=True)
