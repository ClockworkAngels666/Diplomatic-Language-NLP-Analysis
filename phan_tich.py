"""
phan_tich.py – "Bộ não" của công cụ.

Mọi phép tính nằm ở đây, tách riêng khỏi giao diện (app.py), để:
  • app.py và tao_du_lieu_ungdc.py dùng chung MỘT cách tính → kết quả nhất quán;
  • sau này đổi giao diện (web, Excel, API...) không phải viết lại phần phân tích.
"""
import html
import re
from collections import Counter

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# 1. TỪ ĐIỂN NGOẠI GIAO  (dấu * = bắt mọi đuôi từ: sanction* → sanction, sanctions...)
# ─────────────────────────────────────────────────────────────────────────────
TU_DIEN_THU_DICH = [
    "aggress*", "hostil*", "threat*", "provocat*", "confrontation*", "belligeren*", "warmonger*",
    "invasion*", "invade*", "occupation", "occupying", "occupier*", "annex*", "interfer*",
    "sanction*", "blockade*", "embargo*", "coerc*", "blackmail*", "intimidat*",
    "hegemon*", "imperialis*", "neo-colonial*", "neocolonial*", "colonialis*", "expansionis*",
    "destabili*", "subversi*", "regime change", "colour revolution*", "color revolution*",
    "double standard*", "hypocri*", "propaganda", "disinformation", "falsif*",
    "condemn*", "denounce*", "violat*", "illegal*", "illegitimate", "unlawful",
    "atrocit*", "genocid*", "massacre*", "terroris*", "extremis*", "nazi*", "neo-nazi*", "fascis*",
    "enemy", "enemies", "attack*", "war", "wars", "bombing*", "cold war", "zero-sum",
    "bloc mentality", "unilateralis*", "arrogan*", "domination", "dictat*",
]

TU_DIEN_HOP_TAC = [
    "cooperat*", "co-operat*", "collaborat*", "partner*", "dialogue*", "negotiat*", "consultation*",
    "multilateral*", "mutual*", "reciproc*", "friendship", "friendly", "solidarity", "together",
    "trust", "confidence-building", "reconcil*", "consensus", "compromise*", "understanding",
    "peaceful*", "peacebuilding", "win-win", "common interest*", "shared future", "common future",
    "common destiny", "jointly", "integrat*", "connectivity", "assist*", "goodwill",
    "good-neighbo*", "good neighbo*", "harmon*", "inclusive*", "welcome*", "agreement*",
    "build bridges", "bridge-building",
]

# Từ khóa được đếm sẵn cho toàn bộ dữ liệu LHQ (sửa danh sách này rồi chạy lại tao_du_lieu_ungdc.py)
TU_KHOA_MAC_DINH = [
    "NATO", "sovereign*", "multipolar*", "sanction*", "hegemon*", "terroris*", "climate",
    "nuclear", "human rights", "democra*", "colonial*", "Ukrain*", "Taiwan", "Palestin*",
    "South China Sea", "pandemic", "cyber*", "artificial intelligence",
]

NGUONG_TIEU_CUC = -0.05   # câu có điểm VADER ≤ –0,05 được coi là tiêu cực (quy ước phổ biến)


def bien_thanh_regex(danh_sach):
    """Biến danh sách từ (có thể có dấu *) thành một biểu thức tìm kiếm (regex) duy nhất."""
    mau = []
    for tu in danh_sach:
        tu = tu.strip().lower()
        if not tu.rstrip("*"):
            continue
        goc = re.escape(tu.rstrip("*")).replace(r"\ ", r"\s+")
        mau.append(goc + (r"[\w-]*" if tu.endswith("*") else ""))
    if not mau:
        return re.compile(r"(?!x)x")                  # regex không bao giờ khớp
    mau.sort(key=len, reverse=True)                   # cụm dài ưu tiên ("cold war" trước "war")
    return re.compile(r"\b(?:" + "|".join(mau) + r")\b", flags=re.IGNORECASE)


def doc_danh_sach(chuoi):
    """'a, b\\nc' → ['a', 'b', 'c'] (dùng cho ô nhập từ điển trên giao diện)."""
    return [t.strip() for t in re.split(r"[,\n;]+", chuoi or "") if t.strip()]


# ─────────────────────────────────────────────────────────────────────────────
# 2. LÀM SẠCH & TÁCH CÂU
# ─────────────────────────────────────────────────────────────────────────────
_VIET_TAT = re.compile(r"\b(Mr|Mrs|Ms|Dr|St|No|Nos|Art|Arts|Vol|para|paras|U\.S|U\.N|U\.K|E\.U|H\.E)\.")
_TACH_CAU = re.compile(r"(?<=[.!?])\s+(?=[\"“'(\[]?[A-Z])")


def lam_sach(van_ban):
    van_ban = str(van_ban).replace("﻿", " ")
    van_ban = re.sub(r"(?m)^\s*\d{1,3}\.\s+", "", van_ban)    # số thứ tự đoạn ở đầu dòng
    return re.sub(r"\s+", " ", van_ban).strip()


def tach_cau(van_ban_sach):
    tam = _VIET_TAT.sub(lambda m: m.group(0).replace(".", "§"), van_ban_sach)
    cac_cau = [c.replace("§", ".").strip() for c in _TACH_CAU.split(tam)]
    return [c for c in cac_cau if len(c.split()) >= 4]


# ─────────────────────────────────────────────────────────────────────────────
# 3. CHẤM ĐIỂM
# ─────────────────────────────────────────────────────────────────────────────
COT_DEM = ["so_tu", "so_cau", "n_thu_dich", "n_hop_tac", "vader_tong", "n_cau_tieu_cuc"]


class BoChamDiem:
    """Chấm điểm một văn bản bằng 2 lớp: VADER (theo câu) và từ điển ngoại giao."""

    def __init__(self, tu_thu_dich=None, tu_hop_tac=None, vader=None):
        if vader is None:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            vader = SentimentIntensityAnalyzer()
        self.vader = vader
        self.re_thu_dich = bien_thanh_regex(tu_thu_dich if tu_thu_dich is not None else TU_DIEN_THU_DICH)
        self.re_hop_tac = bien_thanh_regex(tu_hop_tac if tu_hop_tac is not None else TU_DIEN_HOP_TAC)

    def cham(self, van_ban):
        """Trả về (tong_ket: dict các số đếm, cau: DataFrame điểm từng câu)."""
        sach = lam_sach(van_ban)
        cac_cau = tach_cau(sach)
        cau = pd.DataFrame({
            "sentence": cac_cau,
            "vader": [self.vader.polarity_scores(c)["compound"] for c in cac_cau],
            "n_thu_dich": [len(self.re_thu_dich.findall(c)) for c in cac_cau],
            "n_hop_tac": [len(self.re_hop_tac.findall(c)) for c in cac_cau],
        })
        tong_ket = {
            "so_tu": len(sach.split()),
            "so_cau": len(cau),
            "n_thu_dich": len(self.re_thu_dich.findall(sach)),
            "n_hop_tac": len(self.re_hop_tac.findall(sach)),
            "vader_tong": float(cau["vader"].sum()) if len(cau) else 0.0,
            "n_cau_tieu_cuc": int((cau["vader"] <= NGUONG_TIEU_CUC).sum()) if len(cau) else 0,
        }
        return tong_ket, cau


def tinh_chi_so(bang):
    """Từ các cột số đếm (COT_DEM) → các chỉ số chuẩn hóa (trên 1.000 từ, tỷ lệ...)."""
    b = bang.copy()
    so_tu = b["so_tu"].replace(0, np.nan)
    so_cau = b["so_cau"].replace(0, np.nan)
    b["chi_so_thu_dich"] = b["n_thu_dich"] / so_tu * 1000
    b["chi_so_hop_tac"] = b["n_hop_tac"] / so_tu * 1000
    b["can_can"] = (b["n_hop_tac"] - b["n_thu_dich"]) / (b["n_hop_tac"] + b["n_thu_dich"]).replace(0, np.nan)
    b["vader_tb"] = b["vader_tong"] / so_cau
    b["ty_le_tieu_cuc"] = b["n_cau_tieu_cuc"] / so_cau
    for cot in [c for c in b.columns if c.startswith("kw::")]:
        b["tk::" + cot[4:]] = b[cot] / so_tu * 1000          # từ khóa trên 1.000 từ
    return b


def gop_theo_nam(bang):
    """Cộng dồn nhiều văn bản về mức quốc gia–năm, rồi tính chỉ số."""
    cot_cong = COT_DEM + [c for c in bang.columns if c.startswith("kw::")]
    g = bang.groupby(["country", "year"], as_index=False)[cot_cong].sum()
    g["so_van_ban"] = bang.groupby(["country", "year"]).size().values
    return tinh_chi_so(g)


def regex_tu_khoa(ds_tu_khoa):
    return {"kw::" + tk: bien_thanh_regex([tk]) for tk in ds_tu_khoa}


def dem_tu_khoa(van_ban_sach, cac_regex):
    return {cot: len(rx.findall(van_ban_sach)) for cot, rx in cac_regex.items()}


def cau_noi_bat(cau, n=3, do_dai_toi_da=600):
    """Chọn những câu đáng đọc nhất: thù địch nhất, tiêu cực nhất (VADER), hợp tác nhất."""
    if cau.empty:
        return pd.DataFrame(columns=["loai", "diem", "sentence"])
    c = cau.drop_duplicates("sentence")
    phan = [
        c[c.n_thu_dich > 0].sort_values(["n_thu_dich", "vader"], ascending=[False, True]).head(n)
         .assign(loai="thu_dich", diem=lambda d: d.n_thu_dich),
        c[c.vader <= NGUONG_TIEU_CUC].nsmallest(n, "vader").assign(loai="tieu_cuc", diem=lambda d: d.vader),
        c[c.n_hop_tac > 0].sort_values(["n_hop_tac", "vader"], ascending=[False, False]).head(n)
         .assign(loai="hop_tac", diem=lambda d: d.n_hop_tac),
    ]
    kq = pd.concat(phan, ignore_index=True)[["loai", "diem", "sentence"]]
    kq["sentence"] = kq["sentence"].str.slice(0, do_dai_toi_da)
    return kq


def tim_buoc_ngoat(bang_nam, cot, n=8):
    """Những lần thay đổi mạnh nhất so với năm có dữ liệu liền trước, theo từng nước."""
    b = bang_nam.sort_values(["country", "year"]).copy()
    b["nam_truoc"] = b.groupby("country")["year"].shift()
    b["thay_doi"] = b.groupby("country")[cot].diff()
    b = b.dropna(subset=["thay_doi"])
    b = b.reindex(b["thay_doi"].abs().sort_values(ascending=False).index).head(n)
    b["nam_truoc"] = b["nam_truoc"].astype(int)
    return b[["country", "nam_truoc", "year", cot, "thay_doi"]]


# ─────────────────────────────────────────────────────────────────────────────
# 4. HIỂN THỊ: tô màu từ khóa & thống kê từ nổi bật
# ─────────────────────────────────────────────────────────────────────────────
KIEU_THU_DICH = "background:rgba(227,73,72,.25);border-radius:3px;padding:0 2px"
KIEU_HOP_TAC = "background:rgba(27,175,122,.25);border-radius:3px;padding:0 2px"


def to_mau_html(van_ban, re_thu_dich, re_hop_tac):
    """Trả về HTML an toàn: từ thù địch nền đỏ, từ hợp tác nền xanh."""
    khop = [(m.start(), m.end(), KIEU_THU_DICH) for m in re_thu_dich.finditer(van_ban)]
    khop += [(m.start(), m.end(), KIEU_HOP_TAC) for m in re_hop_tac.finditer(van_ban)]
    khop.sort()
    ra, vi_tri = [], 0
    for dau, cuoi, kieu in khop:
        if dau < vi_tri:          # bỏ đoạn chồng lấn
            continue
        ra.append(html.escape(van_ban[vi_tri:dau]))
        ra.append(f'<span style="{kieu}">{html.escape(van_ban[dau:cuoi])}</span>')
        vi_tri = cuoi
    ra.append(html.escape(van_ban[vi_tri:]))
    return "".join(ra).replace("\n", "<br>")


def tu_noi_bat(van_ban, regex, n=10):
    dem = Counter(re.sub(r"\s+", " ", m.lower()) for m in regex.findall(van_ban))
    return dem.most_common(n)
