"""
tao_du_lieu_ungdc.py – CHẠY MỘT LẦN để chuẩn bị dữ liệu LHQ cho web app.

Việc nó làm:
  1. Tải UN General Debate Corpus (UNGDC) từ Harvard Dataverse (hoặc dùng file bạn đã tải sẵn).
  2. Chấm điểm TỪNG bài phát biểu (VADER + từ điển ngoại giao + đếm từ khóa).
  3. Lưu 2 file nhỏ gọn để web app đọc tức thì:
       ungdc_diem.csv.gz  – điểm số của mọi nước–năm (~1 MB)
       ungdc_cau.csv.gz   – các câu đáng chú ý nhất của mỗi bài (để "đọc kỹ")

Vì sao không để web app tự làm việc này? Chấm điểm hơn 10.000 bài mất 10–20 phút.
Làm sẵn một lần thì ai mở công cụ cũng thấy kết quả ngay lập tức.

Cách chạy (trên Google Colab):
    !pip install -q vaderSentiment
    !python tao_du_lieu_ungdc.py                 # tự tải dữ liệu
    !python tao_du_lieu_ungdc.py --file UNGDC.tgz   # hoặc dùng file đã tải tay
"""
import argparse
import re
import tarfile
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

from phan_tich import (TU_KHOA_MAC_DINH, BoChamDiem, cau_noi_bat, dem_tu_khoa,
                       lam_sach, regex_tu_khoa)

DOI_UNGDC = "doi:10.7910/DVN/0TJX8Y"
API_DATAVERSE = "https://dataverse.harvard.edu/api"
THU_MUC_GIAI_NEN = Path("du_lieu_ungdc")
MAU_TEN_FILE = re.compile(r"^([A-Z]{2,4})_(\d{1,3})_(\d{4})\.txt$")


def giai_nen(duong_dan, thu_muc_dich=THU_MUC_GIAI_NEN):
    duong_dan = str(duong_dan)
    Path(thu_muc_dich).mkdir(parents=True, exist_ok=True)
    if duong_dan.lower().endswith((".tgz", ".tar.gz", ".tar")):
        with tarfile.open(duong_dan) as tar:
            try:
                tar.extractall(thu_muc_dich, filter="data")
            except TypeError:
                tar.extractall(thu_muc_dich)
    elif duong_dan.lower().endswith(".zip"):
        with zipfile.ZipFile(duong_dan) as z:
            z.extractall(thu_muc_dich)
    else:
        raise ValueError(f"Không nhận ra định dạng file: {duong_dan}")


def tai_tu_dataverse():
    print("🔎 Đang hỏi Harvard Dataverse danh sách file...")
    r = requests.get(f"{API_DATAVERSE}/datasets/:persistentId/",
                     params={"persistentId": DOI_UNGDC}, timeout=60)
    r.raise_for_status()
    phien_ban = r.json()["data"]["latestVersion"]
    cac_file = [f["dataFile"] for f in phien_ban["files"]]
    file_nen = [f for f in cac_file if f["filename"].lower().endswith((".tgz", ".tar.gz", ".zip"))]
    if not file_nen:
        raise RuntimeError("Không tìm thấy file nén (.tgz/.zip) trong bộ dữ liệu.")
    chon = max(file_nen, key=lambda f: f.get("filesize", 0))
    dich = Path(chon["filename"])
    print(f"⬇️  Đang tải {dich.name} ({chon.get('filesize', 0) / 1e6:.0f} MB)...")
    with requests.get(f"{API_DATAVERSE}/access/datafile/{chon['id']}", stream=True, timeout=600) as resp:
        resp.raise_for_status()
        with open(dich, "wb") as out:
            for khoi in resp.iter_content(chunk_size=1 << 20):
                out.write(khoi)
    return dich


def main():
    p = argparse.ArgumentParser(description="Chuẩn bị dữ liệu UNGDC cho web app.")
    p.add_argument("--file", help="File UNGDC (.tgz/.zip) đã tải sẵn; bỏ trống để tự tải.")
    p.add_argument("--thu-muc-ra", default=".", help="Nơi lưu 2 file kết quả (mặc định: thư mục hiện tại).")
    args = p.parse_args()

    if not (THU_MUC_GIAI_NEN.exists() and any(THU_MUC_GIAI_NEN.rglob("*.txt"))):
        file_nen = Path(args.file) if args.file else tai_tu_dataverse()
        print("📦 Đang giải nén...")
        giai_nen(file_nen)

    cac_file = sorted(p for p in THU_MUC_GIAI_NEN.rglob("*.txt") if MAU_TEN_FILE.match(p.name))
    if not cac_file:
        raise SystemExit("❌ Không tìm thấy file bài phát biểu nào (dạng ABC_77_2022.txt).")
    print(f"📚 Tìm thấy {len(cac_file):,} bài phát biểu. Bắt đầu chấm điểm (10–20 phút)...")

    bo_cham = BoChamDiem()
    cac_rx = regex_tu_khoa(TU_KHOA_MAC_DINH)
    diem, cau_hay = [], []
    bat_dau = time.time()
    for i, f in enumerate(cac_file, 1):
        ma, khoa, nam = MAU_TEN_FILE.match(f.name).groups()
        van_ban = f.read_text(encoding="utf-8", errors="replace")
        tong_ket, cau = bo_cham.cham(van_ban)
        dong = {"country": ma, "session": int(khoa), "year": int(nam), **tong_ket}
        dong.update(dem_tu_khoa(lam_sach(van_ban), cac_rx))
        diem.append(dong)
        cau_hay.append(cau_noi_bat(cau).assign(country=ma, year=int(nam)))
        if i % 500 == 0 or i == len(cac_file):
            da_qua = time.time() - bat_dau
            print(f"   {i:,}/{len(cac_file):,} bài – còn khoảng {da_qua / i * (len(cac_file) - i) / 60:.0f} phút")

    ra = Path(args.thu_muc_ra)
    ra.mkdir(parents=True, exist_ok=True)
    bang_diem = pd.DataFrame(diem).sort_values(["country", "year"])
    bang_diem["vader_tong"] = bang_diem["vader_tong"].round(4)
    bang_diem.to_csv(ra / "ungdc_diem.csv.gz", index=False, compression="gzip")
    bang_cau = pd.concat(cau_hay, ignore_index=True)[["country", "year", "loai", "diem", "sentence"]]
    bang_cau["diem"] = bang_cau["diem"].round(3)
    bang_cau.to_csv(ra / "ungdc_cau.csv.gz", index=False, compression="gzip")

    for ten in ["ungdc_diem.csv.gz", "ungdc_cau.csv.gz"]:
        print(f"💾 {ra / ten}  ({(ra / ten).stat().st_size / 1e6:.1f} MB)")
    print(f"✅ Xong! {bang_diem.country.nunique()} quốc gia, "
          f"{bang_diem.year.min()}–{bang_diem.year.max()}. Hãy tải 2 file trên lên GitHub.")


if __name__ == "__main__":
    main()
