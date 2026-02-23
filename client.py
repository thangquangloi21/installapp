
import os
import sys
import time
import zipfile
import shutil
import hashlib
from pathlib import Path

import requests
import subprocess
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


try:
    from tqdm import tqdm
    HAS_TQDM = True
except Exception:
    HAS_TQDM = False


def make_session(timeout=(10, 30), total_retries=3, backoff=0.5):
    """Tạo session Requests có retry và timeout."""
    session = requests.Session()
    retry = Retry(
        total=total_retries,
        backoff_factor=backoff,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.timeout = timeout
    return session


def download_zip(url: str, dest_path: Path, expected_sha256: str | None = None, resume: bool = True) -> Path:
    """
    Tải file ZIP từ URL về dest_path.
    - Hỗ trợ resume (Range) nếu server cho phép.
    - Kiểm tra SHA256 (nếu cung cấp).
    """
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    session = make_session()

    headers = {}
    temp_path = dest_path.with_suffix(dest_path.suffix + ".part")

    # Kiểm tra resume
    downloaded = 0
    if resume and temp_path.exists():
        downloaded = temp_path.stat().st_size
        headers["Range"] = f"bytes={downloaded}-"

    # Preflight HEAD để lấy kích thước (nếu có)
    total_size = None
    try:
        head = session.head(url, timeout=session.timeout, allow_redirects=True)
        if head.ok and "Content-Length" in head.headers:
            total_size = int(head.headers["Content-Length"])
    except Exception:
        pass  # không bắt buộc

    # GET streaming
    with session.get(url, stream=True, headers=headers, timeout=session.timeout) as r:
        r.raise_for_status()

        # Kiểm tra Content-Type cơ bản (không bắt buộc)
        ctype = r.headers.get("Content-Type", "").lower()
        # zip có thể trả về application/zip hoặc application/octet-stream
        # if 'zip' not in ctype and 'octet-stream' not in ctype:
        #     print(f"Cảnh báo: Content-Type không phải zip: {ctype}")

        # Xác định tổng dung lượng để hiển thị progress
        if total_size is None:
            # Nếu dùng Range, tổng còn lại có thể trong Content-Length của response
            if "Content-Length" in r.headers:
                total_size = int(r.headers["Content-Length"]) + downloaded

        chunk_size = 1024 * 256  # 256KB
        mode = "ab" if downloaded > 0 and resume else "wb"

        if HAS_TQDM and total_size:
            pbar = tqdm(
                total=total_size,
                unit="B", unit_scale=True, unit_divisor=1024,
                initial=downloaded,
                desc=f"Tải {dest_path.name}"
            )
        else:
            pbar = None

        with open(temp_path, mode) as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                f.write(chunk)
                if pbar:
                    pbar.update(len(chunk))

        if pbar:
            pbar.close()

    # Đổi tên .part -> file đích (ghi đè nếu file đích đã tồn tại trên Windows)
    try:
        os.replace(temp_path, dest_path)
    except Exception:
        # Fallback: nếu os.replace thất bại, thử rename bình thường
        temp_path.rename(dest_path)

    # Kiểm tra SHA256 nếu có
    if expected_sha256:
        sha = sha256_file(dest_path)
        if sha.lower() != expected_sha256.lower():
            raise ValueError(f"SHA256 không khớp! Expected={expected_sha256} Actual={sha}")

    return dest_path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()



def extract_zip(zip_path: Path, dest_dir: Path, overwrite: bool = False) -> Path:
    """
    Giải nén `zip_path` vào `dest_dir` an toàn (ngăn path traversal).
    Nếu `overwrite` True thì xóa `dest_dir` trước khi giải nén.
    Trả về `dest_dir` khi hoàn tất.
    """
    dest_dir = Path(dest_dir)
    if overwrite and dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Kiểm tra các member để tránh path traversal
            for member in zf.namelist():
                member_path = Path(member)
                target_path = (dest_dir / member_path).resolve()
                if not str(target_path).startswith(str(dest_dir.resolve())):
                    raise Exception(f"Illegal file path in zip: {member}")
            # Thực hiện giải nén
            zf.extractall(path=dest_dir)
    except zipfile.BadZipFile as e:
        raise ValueError(f"File ZIP không hợp lệ: {e}") from e

    return dest_dir


def get_desktop_path() -> Path:
    """Trả về đường dẫn Desktop của user (Windows-friendly)."""
    try:
        import ctypes, ctypes.wintypes
        buf = ctypes.create_unicode_buffer(260)
        # CSIDL_DESKTOPDIRECTORY = 0x0010
        ctypes.windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, buf)
        return Path(buf.value)
    except Exception:
        return Path.home() / "Desktop"


def create_desktop_shortcut(target: Path, name: str | None = None, args: str = "", working_dir: Path | None = None, icon: Path | None = None) -> Path:
    """
    Tạo shortcut .lnk trên Desktop trỏ tới `target`.
    Sử dụng PowerShell + WScript.Shell để tránh phụ thuộc bên ngoài.
    Trả về đường dẫn tới file .lnk vừa tạo.
    """
    desktop = get_desktop_path()
    desktop.mkdir(parents=True, exist_ok=True)
    name = name or target.stem
    lnk = desktop / f"{name}.lnk"

    t = str(target.resolve())
    cwd = str((working_dir or target.parent).resolve())
    iconloc = str(icon.resolve()) if icon else t

    def _ps_quote(s: str) -> str:
        return s.replace("'", "''")

    lnk_q = _ps_quote(str(lnk))
    t_q = _ps_quote(t)
    cwd_q = _ps_quote(cwd)
    icon_q = _ps_quote(iconloc)
    args_q = _ps_quote(args)

    ps_cmd = (
        f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk_q}');"
        f"$s.TargetPath='{t_q}';"
        f"$s.Arguments='{args_q}';"
        f"$s.WorkingDirectory='{cwd_q}';"
        f"$s.IconLocation='{icon_q}';"
        "$s.Save();"
    )

    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True, capture_output=True)
    return lnk


def main():
    # ==== THAY ĐỔI CHO PHÙ HỢP VỚI LINK CỦA BẠN ====
    url = "http://10.239.2.174:5000/zip"   # ví dụ: link Flask bạn đã tạo
    save_to = Path("downloads/sample.zip")    # nơi lưu tạm
    extract_to = Path("C:/APP")            # thư mục giải nén
    expected_sha256 = None                    # nếu có endpoint checksum thì điền vào
    overwrite_extract = False                 # đổi thành True nếu muốn ghi đè

    print(f"Bắt đầu tải: {url}")
    zip_file = download_zip(url, save_to, expected_sha256=expected_sha256, resume=True)
    print(f"Đã tải xong: {zip_file} (SHA256={sha256_file(zip_file)})")

    print(f"Giải nén vào: {extract_to}")
    try:
        extracted = extract_zip(zip_file, extract_to, overwrite=overwrite_extract)
        print(f"Hoàn tất giải nén: {extracted}")

        # Tìm `testapp.exe` trong nội dung giải nén và tạo shortcut trên Desktop
        testapp = None
        for p in extracted.rglob('M_PLUS.exe'):
            testapp = p
            break
        if testapp:
            try:
                shortcut = create_desktop_shortcut(testapp, name='M_PLUS_TEST')
                print(f"Shortcut đã tạo trên Desktop: {shortcut}")
            except Exception as e:
                print(f"Lỗi khi tạo shortcut: {e}")
        else:
            print("Không tìm thấy 'testapp.exe' trong nội dung giải nén.")

    except Exception as e:
        print(f"Lỗi khi giải nén: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
