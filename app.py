"""
app.py – Giao diện web của công cụ (viết bằng Streamlit).

Chạy thử trên máy:   streamlit run app.py
Đưa lên mạng:        xem README.md (Streamlit Community Cloud, miễn phí)

Cấu trúc file này:
  0. Cấu hình & chữ hiển thị (song ngữ Việt–Anh)
  1. Hàm tiện ích (tên nước, màu, vẽ biểu đồ, đọc file)
  2. Thanh bên (ngôn ngữ, giới thiệu, tùy chỉnh từ điển)
  3. Tab 1 – Phân tích một văn bản
  4. Tab 2 – So sánh nhiều văn bản theo thời gian (file CSV của người dùng)
  5. Tab 3 – Khám phá dữ liệu Đại hội đồng LHQ (dữ liệu chấm sẵn)
"""
import hashlib
import io
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import phan_tich as pt

# ═════════════════════════════════════════════════════════════════════════════
# 0. CẤU HÌNH
# ═════════════════════════════════════════════════════════════════════════════
TAC_GIA = "Tên của bạn"          # ✏️ sửa thành tên bạn
LIEN_KET_GITHUB = ""             # ✏️ vd. "https://github.com/ten-ban/cong-cu-ngoai-giao"

THU_MUC_APP = Path(__file__).parent
BANG_MAU = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
MAU_TB = "#8a8984"

st.set_page_config(page_title="Diplomatic Language Analyzer", page_icon="🌐", layout="wide")

CHU = {  # khóa: (Tiếng Việt, English)
    "tieu_de": ("🌐 Phân tích Ngôn ngữ Ngoại giao", "🌐 Diplomatic Language Analyzer"),
    "mo_ta": ("Đo mức độ **thù địch**, **hợp tác** và sự **dịch chuyển luận điệu** trong phát ngôn ngoại giao – "
              "bài phát biểu, thông cáo chung, bài báo.",
              "Measure **hostility**, **cooperation** and **rhetorical shifts** in diplomatic texts – "
              "speeches, joint statements, news articles."),
    "tab1": ("🔍 Phân tích một văn bản", "🔍 Analyze a text"),
    "tab2": ("📈 So sánh theo thời gian", "📈 Compare over time"),
    "tab3": ("🌐 Dữ liệu Đại hội đồng LHQ", "🌐 UN General Debate data"),
    # thanh bên
    "ve_cong_cu": ("ℹ️ Công cụ hoạt động thế nào?", "ℹ️ How does it work?"),
    "ve_cong_cu_nd": (
        "**1. Từ điển ngoại giao** – đếm các từ báo hiệu *thù địch* (aggression, hegemony, sanctions…) "
        "và *hợp tác* (dialogue, mutual, win-win…) trên mỗi 1.000 từ.\n\n"
        "**2. Cán cân giọng điệu** = (hợp tác − thù địch) / (hợp tác + thù địch), từ −1 (đối đầu) đến +1 (hòa dịu).\n\n"
        "**3. VADER** – điểm cảm xúc từng câu (−1 đến +1), lấy trung bình.\n\n"
        "**Giới hạn:** phương pháp đếm từ không hiểu ngữ cảnh (phủ định, mỉa mai). "
        "Văn bản phải bằng **tiếng Anh**. Hãy luôn đọc các câu được làm nổi bật để kiểm chứng.",
        "**1. Diplomatic dictionary** – counts *hostile* words (aggression, hegemony, sanctions…) "
        "and *cooperative* words (dialogue, mutual, win-win…) per 1,000 words.\n\n"
        "**2. Tone balance** = (cooperative − hostile) / (cooperative + hostile), from −1 (confrontational) to +1 (conciliatory).\n\n"
        "**3. VADER** – sentence-level sentiment (−1 to +1), averaged.\n\n"
        "**Limitations:** word counting ignores context (negation, irony). Texts must be in **English**. "
        "Always read the highlighted sentences to validate."),
    "tuy_chinh": ("⚙️ Tùy chỉnh từ điển", "⚙️ Customize dictionaries"),
    "tuy_chinh_nd": ("Phân cách bằng dấu phẩy. Dấu * = mọi đuôi từ. Áp dụng cho tab 1 và 2 "
                     "(dữ liệu LHQ dùng từ điển gốc).",
                     "Comma-separated. * = any word ending. Applies to tabs 1 and 2 "
                     "(UN data uses the original dictionaries)."),
    "tu_thu_dich": ("Từ thù địch", "Hostile words"),
    "tu_hop_tac": ("Từ hợp tác", "Cooperative words"),
    "khoi_phuc": ("Khôi phục mặc định", "Reset to default"),
    "tac_gia": ("Xây dựng bởi", "Built by"),
    # tab 1
    "tab1_hd": ("Dán một văn bản **tiếng Anh** (bài phát biểu, thông cáo, bài báo…) hoặc tải file lên.",
                "Paste an **English** text (speech, statement, article…) or upload a file."),
    "tai_tep": ("Tải file (.txt hoặc .pdf)", "Upload a file (.txt or .pdf)"),
    "dung_mau": ("Dùng văn bản mẫu", "Use sample text"),
    "o_van_ban": ("Văn bản", "Text"),
    "cho_van_ban": ("👆 Hãy dán văn bản hoặc bấm “Dùng văn bản mẫu” để xem thử.",
                    "👆 Paste a text or click “Use sample text” to try it."),
    "dang_dung_tep": ("Đang phân tích file", "Analyzing file"),
    "qua_ngan": ("Văn bản quá ngắn – cần ít nhất một câu hoàn chỉnh (≥ 4 từ).",
                 "Text too short – at least one full sentence (≥ 4 words) is needed."),
    "loi_tep": ("Không đọc được file này", "Could not read this file"),
    "phan_vi": ("Mức thù địch của văn bản này **cao hơn {p:.0%}** các bài phát biểu tại Đại hội đồng LHQ giai đoạn {a}–{b}.",
                "This text is **more hostile than {p:.0%}** of UN General Debate speeches in {a}–{b}."),
    "so_voi_lhq": ("so với TB LHQ", "vs UN avg"),
    "van_ban_to_mau": ("Văn bản được làm nổi bật", "Highlighted text"),
    "chu_thich_mau": ("<span style='{a}'>thù địch</span> &nbsp; <span style='{b}'>hợp tác</span>",
                      "<span style='{a}'>hostile</span> &nbsp; <span style='{b}'>cooperative</span>"),
    "tu_td_nhieu": ("🔴 Từ thù địch xuất hiện nhiều nhất", "🔴 Most frequent hostile words"),
    "tu_ht_nhieu": ("🟢 Từ hợp tác xuất hiện nhiều nhất", "🟢 Most frequent cooperative words"),
    "khong_co": ("(không có)", "(none)"),
    "bang_cau": ("Điểm từng câu", "Sentence scores"),
    "sap_xep": ("Sắp xếp theo", "Sort by"),
    "sx_td": ("Thù địch nhất", "Most hostile"),
    "sx_tc": ("Tiêu cực nhất (VADER)", "Most negative (VADER)"),
    "sx_ht": ("Hợp tác nhất", "Most cooperative"),
    "sx_goc": ("Thứ tự trong văn bản", "Original order"),
    "tai_ve_csv": ("⬇️ Tải bảng kết quả (CSV)", "⬇️ Download results (CSV)"),
    # tab 2
    "tab2_hd": ("Tải lên file CSV có tối thiểu 3 cột **country** (mã nước, vd. VNM), **year** (năm) và **text** "
                "(toàn văn tiếng Anh). Một nước–năm có thể có nhiều văn bản; công cụ sẽ tự cộng dồn.",
                "Upload a CSV with at least 3 columns: **country** (code, e.g. VNM), **year** and **text** "
                "(full English text). Several texts per country-year are fine; they are added up."),
    "tai_mau_csv": ("⬇️ Tải file CSV mẫu", "⬇️ Download sample CSV"),
    "tai_csv": ("Tải file CSV của bạn", "Upload your CSV"),
    "tu_khoa_rieng": ("Từ khóa muốn theo dõi (phân cách bằng dấu phẩy)", "Keywords to track (comma-separated)"),
    "thieu_cot": ("File thiếu cột: {c}. Cần tối thiểu: country, year, text.",
                  "Missing columns: {c}. Required: country, year, text."),
    "dang_cham": ("Đang chấm điểm {i}/{n} văn bản...", "Scoring {i}/{n} texts..."),
    "da_cham": ("Đã phân tích {n} văn bản của {k} quốc gia.", "Analyzed {n} texts from {k} countries."),
    "toi_da_8": ("Biểu đồ hiển thị tối đa 8 nước.", "Charts show at most 8 countries."),
    # tab 3
    "chua_co_du_lieu": ("Chưa có dữ liệu LHQ. Người quản trị cần chạy `tao_du_lieu_ungdc.py` một lần và đặt hai file "
                        "`ungdc_diem.csv.gz`, `ungdc_cau.csv.gz` cạnh `app.py` (xem README).",
                        "UN data not found. The maintainer must run `tao_du_lieu_ungdc.py` once and place "
                        "`ungdc_diem.csv.gz` and `ungdc_cau.csv.gz` next to `app.py` (see README)."),
    "tab3_hd": ("Bài phát biểu của các nước tại Phiên thảo luận chung Đại hội đồng LHQ, đã được chấm điểm sẵn.",
                "Country statements at the UN General Assembly General Debate, pre-scored."),
    "chon_nuoc": ("Quốc gia (tối đa 8)", "Countries (max 8)"),
    "khoang_nam": ("Khoảng năm", "Years"),
    "chi_so": ("Chỉ số", "Metric"),
    "hien_tb": ("Hiện trung bình các nước", "Show average of all countries"),
    "hien_su_kien": ("Hiện mốc sự kiện", "Show key events"),
    "tb_cac_nuoc": ("Trung bình các nước", "All-country average"),
    "buoc_ngoat": ("⚡ Những bước ngoặt lớn nhất", "⚡ Biggest shifts"),
    "buoc_ngoat_hd": ("Thay đổi mạnh nhất so với năm liền trước. Hãy đọc kỹ các năm này ở mục bên dưới.",
                      "Largest changes from the previous year. Read these years closely below."),
    "doc_ky": ("📖 Đọc kỹ một bài phát biểu", "📖 Close reading"),
    "nuoc": ("Quốc gia", "Country"),
    "nam": ("Năm", "Year"),
    "nam_truoc": ("Từ năm", "From"),
    "thay_doi": ("Thay đổi", "Change"),
    "loai_thu_dich": ("🔴 Câu dùng nhiều từ thù địch nhất", "🔴 Sentences with most hostile words"),
    "loai_tieu_cuc": ("🟠 Câu tiêu cực nhất (VADER)", "🟠 Most negative sentences (VADER)"),
    "loai_hop_tac": ("🟢 Câu hợp tác nhất", "🟢 Most cooperative sentences"),
    "xep_hang": ("🏆 Xếp hạng các nước trong một năm", "🏆 Country ranking for a year"),
    "tai_du_lieu_loc": ("⬇️ Tải dữ liệu đang xem (CSV)", "⬇️ Download this data (CSV)"),
    "trich_dan": ("Nguồn dữ liệu: Jankin, Baturo & Dasandi (2024), *Words to unite nations: The complete United Nations "
                  "General Debate Corpus, 1946–present*, Journal of Peace Research. Văn bản là bản tiếng Anh chính thức của LHQ.",
                  "Data: Jankin, Baturo & Dasandi (2024), *Words to unite nations: The complete United Nations General "
                  "Debate Corpus, 1946–present*, Journal of Peace Research. Texts are official UN English versions."),
    "tu_khoa": ("Từ khóa", "Keyword"),
}

CHI_SO = {  # cột: ((nhãn VI, nhãn EN), (giải thích VI, giải thích EN), định dạng)
    "can_can": (("Cán cân giọng điệu", "Tone balance"),
                ("−1 = hoàn toàn đối đầu, +1 = hoàn toàn hòa dịu", "−1 = fully confrontational, +1 = fully conciliatory"),
                "{:+.2f}"),
    "chi_so_thu_dich": (("Thù địch / 1.000 từ", "Hostile / 1,000 words"),
                        ("Số từ thù địch trên mỗi 1.000 từ", "Hostile dictionary words per 1,000 words"), "{:.1f}"),
    "chi_so_hop_tac": (("Hợp tác / 1.000 từ", "Cooperative / 1,000 words"),
                       ("Số từ hợp tác trên mỗi 1.000 từ", "Cooperative dictionary words per 1,000 words"), "{:.1f}"),
    "vader_tb": (("Cảm xúc TB (VADER)", "Avg sentiment (VADER)"),
                 ("Điểm VADER trung bình mỗi câu, −1 đến +1", "Mean VADER compound per sentence, −1 to +1"), "{:+.2f}"),
    "ty_le_tieu_cuc": (("Tỷ lệ câu tiêu cực", "Share of negative sentences"),
                       ("Tỷ lệ câu có điểm VADER ≤ −0,05", "Share of sentences with VADER ≤ −0.05"), "{:.0%}"),
}
CHI_SO_XAU_KHI_TANG = {"chi_so_thu_dich", "ty_le_tieu_cuc"}   # tăng = tiêu cực → mũi tên màu đảo

SU_KIEN = {1956: ("Suez/Hungary", "Suez/Hungary"), 1962: ("Khủng hoảng Cuba", "Cuban Missile Crisis"),
           1979: ("Afghanistan", "Afghanistan"), 1991: ("Liên Xô tan rã", "USSR dissolves"),
           2001: ("11/9", "9/11"), 2003: ("Chiến tranh Iraq", "Iraq War"),
           2008: ("Khủng hoảng tài chính", "Financial crisis"), 2014: ("Crimea", "Crimea"),
           2020: ("COVID-19", "COVID-19"), 2022: ("Nga–Ukraine", "Russia–Ukraine"), 2023: ("Gaza", "Gaza")}

TEN_VI = {"RUS": "Nga", "USA": "Hoa Kỳ", "CHN": "Trung Quốc", "VNM": "Việt Nam", "GBR": "Anh", "FRA": "Pháp",
          "DEU": "Đức", "JPN": "Nhật Bản", "IND": "Ấn Độ", "UKR": "Ukraine", "PRK": "Triều Tiên",
          "KOR": "Hàn Quốc", "IRN": "Iran", "ISR": "Israel", "PSE": "Palestine", "TUR": "Thổ Nhĩ Kỳ",
          "BRA": "Brazil", "ZAF": "Nam Phi", "PHL": "Philippines", "AUS": "Úc", "CAN": "Canada",
          "IDN": "Indonesia", "THA": "Thái Lan", "LAO": "Lào", "KHM": "Campuchia", "MYS": "Malaysia",
          "SGP": "Singapore", "MMR": "Myanmar", "CUB": "Cuba", "SAU": "Ả Rập Xê Út", "EGY": "Ai Cập",
          "PAK": "Pakistan", "SYR": "Syria", "IRQ": "Iraq", "AFG": "Afghanistan", "VEN": "Venezuela",
          "MEX": "Mexico", "ARG": "Argentina", "NGA": "Nigeria", "ITA": "Ý", "ESP": "Tây Ban Nha",
          "POL": "Ba Lan", "BLR": "Belarus", "GEO": "Gruzia", "SRB": "Serbia", "KAZ": "Kazakhstan"}
TEN_DAC_BIET = {"EU": ("Liên minh châu Âu", "European Union"), "YUG": ("Nam Tư", "Yugoslavia"),
                "CSK": ("Tiệp Khắc", "Czechoslovakia"), "DDR": ("Đông Đức", "East Germany")}

VAN_BAN_MAU = (
    "Mr. President, on behalf of the Republic of Valdoria, I congratulate you on your election. "
    "Our nation remains committed to multilateralism, dialogue and mutual respect among all States. "
    "We welcome the agreement reached on regional connectivity and stand ready to deepen cooperation with our partners.\n\n"
    "Yet we cannot remain silent. The unilateral sanctions imposed on our people are illegal and violate "
    "the Charter of the United Nations. Some powers still cling to a Cold War mentality and a bloc mentality, "
    "using disinformation to justify interference in the internal affairs of sovereign nations. "
    "We condemn these double standards. Hegemony has no place in the twenty-first century.\n\n"
    "Let us instead build bridges, restore trust and work together for a peaceful, inclusive and prosperous future. "
    "Valdoria extends the hand of friendship to every nation willing to engage on the basis of equality and goodwill."
)  # Valdoria là quốc gia HƯ CẤU – văn bản mẫu chỉ để minh họa

MAU_CSV = (
    "country,year,source,title,text\n"
    'VNM,2023,Ministry of Foreign Affairs,Joint Statement (example),"Paste the FULL ENGLISH TEXT here, inside double quotes."\n'
    'VNM,2024,Viet Nam News Agency (English),Article title (example),"Several texts in the same year are fine."\n'
    'CHN,2024,Xinhua (English edition),Article title (example),"Use ISO 3-letter codes (VNM, CHN, RUS, USA...)."\n'
)

# ═════════════════════════════════════════════════════════════════════════════
# 1. HÀM TIỆN ÍCH
# ═════════════════════════════════════════════════════════════════════════════
st.session_state.setdefault("ngon_ngu", "Tiếng Việt")
VI = st.session_state["ngon_ngu"] == "Tiếng Việt"


def t(khoa, **kw):
    chu = CHU[khoa][0 if VI else 1]
    return chu.format(**kw) if kw else chu


def nhan(cot):
    if cot.startswith("tk::"):
        return f"{t('tu_khoa')}: {cot[4:].replace('*', '…')} / {'1.000' if VI else '1,000'}"
    return CHI_SO[cot][0][0 if VI else 1]


def giai_thich(cot):
    return CHI_SO[cot][1][0 if VI else 1] if cot in CHI_SO else None


def dinh_dang(cot, gia_tri):
    if pd.isna(gia_tri):
        return "–"
    return (CHI_SO[cot][2] if cot in CHI_SO else "{:.2f}").format(gia_tri)


try:
    import pycountry
except ImportError:
    pycountry = None


@st.cache_data
def _ten_tieng_anh(ma):
    if pycountry is not None:
        try:
            nuoc = pycountry.countries.get(alpha_3=ma)
            if nuoc is not None:
                return getattr(nuoc, "common_name", None) or nuoc.name
        except (KeyError, LookupError):
            pass
    return ma


def ten_nuoc(ma):
    if ma in TEN_DAC_BIET:
        return TEN_DAC_BIET[ma][0 if VI else 1]
    if VI and ma in TEN_VI:
        return TEN_VI[ma]
    return _ten_tieng_anh(ma)


def mau_on_dinh(khoa_bo_nho, ds_ma):
    """Mỗi nước giữ nguyên màu của mình khi người dùng thêm/bớt nước khác."""
    bo_nho = st.session_state.setdefault(khoa_bo_nho, {})
    for ma in [m for m in bo_nho if m not in ds_ma]:
        del bo_nho[ma]
    for ma in ds_ma:
        if ma not in bo_nho:
            da_dung = set(bo_nho.values())
            bo_nho[ma] = next(i for i in range(len(BANG_MAU)) if i not in da_dung)
    return {ma: BANG_MAU[bo_nho[ma]] for ma in ds_ma}


def _day_nhan(y_cuoi, khoang):
    """Đẩy nhãn cuối đường ra xa nhau để không đè lên nhau."""
    vi_tri, truoc = {}, None
    for ma in sorted(y_cuoi, key=y_cuoi.get):
        y = y_cuoi[ma] if truoc is None else max(y_cuoi[ma], truoc + khoang)
        vi_tri[ma], truoc = y, y
    return vi_tri


def ve_duong(bang, cot, mau, trung_binh=None, hien_su_kien=True, key=None):
    """Biểu đồ đường tương tác: mỗi nước một màu cố định, đường TB nét đứt, mốc sự kiện."""
    bang = bang.dropna(subset=[cot])
    if bang.empty:
        st.info("–")
        return
    fig = go.Figure()
    y_cuoi, x_cuoi = {}, {}
    for ma, m in mau.items():
        d = bang[bang.country == ma].sort_values("year")
        if d.empty:
            continue
        fig.add_trace(go.Scatter(
            x=d.year, y=d[cot], name=ten_nuoc(ma), mode="lines+markers",
            line=dict(color=m, width=2), marker=dict(size=7, color=m, line=dict(width=1, color="white")),
            hovertemplate=f"<b>{ten_nuoc(ma)}</b> · %{{x}}<br>{nhan(cot)}: %{{y:.3f}}<extra></extra>"))
        x_cuoi[ma], y_cuoi[ma] = d.year.iloc[-1], d[cot].iloc[-1]
    if trung_binh is not None and cot in trung_binh:
        fig.add_trace(go.Scatter(
            x=trung_binh.year, y=trung_binh[cot], name=t("tb_cac_nuoc"), mode="lines",
            line=dict(color=MAU_TB, width=1.6, dash="dash"),
            hovertemplate=f"<b>{t('tb_cac_nuoc')}</b> · %{{x}}<br>%{{y:.3f}}<extra></extra>"))

    nam_min, nam_max = int(bang.year.min()), int(bang.year.max())
    if len(y_cuoi) <= 4:   # nhãn trực tiếp ở cuối đường
        bien_do = (bang[cot].max() - bang[cot].min()) or 1
        for ma, y in _day_nhan(y_cuoi, bien_do * 0.07).items():
            fig.add_annotation(x=x_cuoi[ma], y=y, text=ten_nuoc(ma), xanchor="left", xshift=10,
                               showarrow=False, font=dict(size=12))
    if hien_su_kien:
        moc = sorted(n for n in SU_KIEN if nam_min <= n <= nam_max)
        for i, n in enumerate(moc):
            fig.add_vline(x=n, line_width=1, line_dash="dot", line_color="rgba(138,137,132,0.7)")
            fig.add_annotation(x=n, y=1, yref="paper", yanchor="bottom", yshift=4 + 17 * (i % 3),
                               text=SU_KIEN[n][0 if VI else 1], showarrow=False,
                               font=dict(size=11, color=MAU_TB))
    phan_du = max(2, (nam_max - nam_min) * 0.13)
    fig.update_xaxes(range=[nam_min - 0.6, nam_max + phan_du], showgrid=False)
    fig.update_layout(height=500, yaxis_title=nhan(cot), hovermode="closest",
                      margin=dict(l=10, r=10, t=90 if hien_su_kien else 30, b=10),
                      legend=dict(orientation="h", yanchor="top", y=-0.1, x=0))
    st.plotly_chart(fig, width="stretch", key=key)


def doc_tep_van_ban(tep):
    if tep.name.lower().endswith(".pdf"):
        from pypdf import PdfReader
        return "\n".join((trang.extract_text() or "") for trang in PdfReader(tep).pages)
    du_lieu = tep.getvalue()
    if du_lieu[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return du_lieu.decode("utf-16")
    try:
        return du_lieu.decode("utf-8-sig")
    except UnicodeDecodeError:
        return du_lieu.decode("cp1252", errors="replace")


@st.cache_resource
def lay_vader():
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    return SentimentIntensityAnalyzer()


def bo_cham(tu_td, tu_ht):
    return pt.BoChamDiem(list(tu_td), list(tu_ht), vader=lay_vader())


@st.cache_data(max_entries=30, show_spinner=False)
def cham_mot_van_ban(van_ban, tu_td, tu_ht):
    return bo_cham(tu_td, tu_ht).cham(van_ban)


@st.cache_data(show_spinner=False)
def tai_du_lieu_lhq():
    for thu_muc in (THU_MUC_APP, THU_MUC_APP / "data"):
        f_diem, f_cau = thu_muc / "ungdc_diem.csv.gz", thu_muc / "ungdc_cau.csv.gz"
        if f_diem.exists():
            diem = pt.tinh_chi_so(pd.read_csv(f_diem))
            cau = pd.read_csv(f_cau) if f_cau.exists() else None
            return diem, cau
    return None, None


# ═════════════════════════════════════════════════════════════════════════════
# 2. THANH BÊN
# ═════════════════════════════════════════════════════════════════════════════
MAC_DINH_TD, MAC_DINH_HT = ", ".join(pt.TU_DIEN_THU_DICH), ", ".join(pt.TU_DIEN_HOP_TAC)
st.session_state.setdefault("tu_td", MAC_DINH_TD)
st.session_state.setdefault("tu_ht", MAC_DINH_HT)


def khoi_phuc_tu_dien():
    st.session_state["tu_td"], st.session_state["tu_ht"] = MAC_DINH_TD, MAC_DINH_HT


with st.sidebar:
    st.radio("Ngôn ngữ / Language", ["Tiếng Việt", "English"], horizontal=True, key="ngon_ngu")
    with st.expander(t("ve_cong_cu"), expanded=False):
        st.markdown(t("ve_cong_cu_nd"))
    with st.expander(t("tuy_chinh"), expanded=False):
        st.caption(t("tuy_chinh_nd"))
        st.text_area(t("tu_thu_dich"), key="tu_td", height=180)
        st.text_area(t("tu_hop_tac"), key="tu_ht", height=180)
        st.button(t("khoi_phuc"), on_click=khoi_phuc_tu_dien)
    st.divider()
    tac_gia = f"{t('tac_gia')} **{TAC_GIA}**"
    if LIEN_KET_GITHUB:
        tac_gia += f" · [GitHub]({LIEN_KET_GITHUB})"
    st.caption(tac_gia)

TU_TD = tuple(pt.doc_danh_sach(st.session_state["tu_td"]))
TU_HT = tuple(pt.doc_danh_sach(st.session_state["tu_ht"]))
TU_DIEN_GOC = TU_TD == tuple(pt.TU_DIEN_THU_DICH) and TU_HT == tuple(pt.TU_DIEN_HOP_TAC)

DIEM_LHQ, CAU_LHQ = tai_du_lieu_lhq()

st.title(t("tieu_de"))
st.markdown(t("mo_ta"))
tab1, tab2, tab3 = st.tabs([t("tab1"), t("tab2"), t("tab3")])

# ═════════════════════════════════════════════════════════════════════════════
# 3. TAB 1 – PHÂN TÍCH MỘT VĂN BẢN
# ═════════════════════════════════════════════════════════════════════════════
st.session_state.setdefault("o_van_ban", "")


def dung_van_ban_mau():
    st.session_state["o_van_ban"] = VAN_BAN_MAU


def hien_ket_qua_van_ban(van_ban):
    tong, cau = cham_mot_van_ban(van_ban, TU_TD, TU_HT)
    if tong["so_cau"] == 0:
        st.warning(t("qua_ngan"))
        return
    chi = pt.tinh_chi_so(pd.DataFrame([tong])).iloc[0]

    # Mốc so sánh: các bài phát biểu LHQ 10 năm gần nhất (chỉ khi dùng từ điển gốc)
    moc = None
    if DIEM_LHQ is not None and TU_DIEN_GOC:
        nam_cuoi = int(DIEM_LHQ.year.max())
        moc = DIEM_LHQ[DIEM_LHQ.year > nam_cuoi - 10]

    cot_hien = ["can_can", "chi_so_thu_dich", "chi_so_hop_tac", "vader_tb", "ty_le_tieu_cuc"]
    for khung, cot in zip(st.columns(len(cot_hien)), cot_hien):
        delta = None
        if moc is not None and pd.notna(chi[cot]):
            chenh = chi[cot] - moc[cot].mean()
            mau_so = {"ty_le_tieu_cuc": "{:+.0%}", "chi_so_thu_dich": "{:+.1f}", "chi_so_hop_tac": "{:+.1f}"}
            delta = mau_so.get(cot, "{:+.2f}").format(chenh) + " " + t("so_voi_lhq")
        khung.metric(nhan(cot), dinh_dang(cot, chi[cot]), delta=delta, help=giai_thich(cot),
                     delta_color="inverse" if cot in CHI_SO_XAU_KHI_TANG else "normal")
    if moc is not None and pd.notna(chi["chi_so_thu_dich"]):
        st.markdown(t("phan_vi", p=(moc["chi_so_thu_dich"] < chi["chi_so_thu_dich"]).mean(),
                      a=int(moc.year.min()), b=int(moc.year.max())))

    bo = bo_cham(TU_TD, TU_HT)
    trai, phai = st.columns([3, 2])
    with trai:
        st.subheader(t("van_ban_to_mau"))
        st.markdown(t("chu_thich_mau", a=pt.KIEU_THU_DICH, b=pt.KIEU_HOP_TAC), unsafe_allow_html=True)
        with st.container(height=420, border=True):
            st.markdown(pt.to_mau_html(van_ban, bo.re_thu_dich, bo.re_hop_tac), unsafe_allow_html=True)
    with phai:
        for tieu_de, rx in ((t("tu_td_nhieu"), bo.re_thu_dich), (t("tu_ht_nhieu"), bo.re_hop_tac)):
            st.markdown(f"**{tieu_de}**")
            cac_tu = pt.tu_noi_bat(van_ban, rx)
            st.markdown(" · ".join(f"{tu} ×{so}" for tu, so in cac_tu) if cac_tu else t("khong_co"))

    st.subheader(t("bang_cau"))
    # Giá trị lưu là mã cố định ("td", "tc"...), nhãn hiển thị đổi theo ngôn ngữ
    cach = st.radio(t("sap_xep"), ["td", "tc", "ht", "goc"], format_func=lambda k: t("sx_" + k),
                    horizontal=True, key="sap_xep_cau")
    if cach == "td":
        cau = cau.sort_values(["n_thu_dich", "vader"], ascending=[False, True])
    elif cach == "tc":
        cau = cau.sort_values("vader")
    elif cach == "ht":
        cau = cau.sort_values(["n_hop_tac", "vader"], ascending=[False, False])
    st.dataframe(cau, hide_index=True, column_config={
        "sentence": st.column_config.TextColumn("Câu" if VI else "Sentence", width="large"),
        "vader": st.column_config.NumberColumn("VADER", format="%.2f"),
        "n_thu_dich": st.column_config.NumberColumn(t("tu_thu_dich")),
        "n_hop_tac": st.column_config.NumberColumn(t("tu_hop_tac")),
    })
    st.download_button(t("tai_ve_csv"), cau.to_csv(index=False).encode("utf-8-sig"),
                       file_name="diem_tung_cau.csv", mime="text/csv")


with tab1:
    st.markdown(t("tab1_hd"))
    cot_a, cot_b = st.columns([4, 1])
    with cot_a:
        tep = st.file_uploader(t("tai_tep"), type=["txt", "pdf"], key="tep_van_ban")
    with cot_b:
        st.write("")
        st.button(t("dung_mau"), on_click=dung_van_ban_mau, width="stretch")
    st.text_area(t("o_van_ban"), key="o_van_ban", height=200)

    van_ban = st.session_state["o_van_ban"]
    if tep is not None:
        try:
            van_ban = doc_tep_van_ban(tep)
            st.caption(f"{t('dang_dung_tep')}: **{tep.name}**")
        except Exception as loi:
            st.error(f"{t('loi_tep')}: {loi}")
            van_ban = ""
    if van_ban.strip():
        hien_ket_qua_van_ban(van_ban)
    else:
        st.info(t("cho_van_ban"))

# ═════════════════════════════════════════════════════════════════════════════
# 4. TAB 2 – SO SÁNH NHIỀU VĂN BẢN THEO THỜI GIAN
# ═════════════════════════════════════════════════════════════════════════════
def cham_bang_csv(bang, ds_tu_khoa):
    """Chấm từng văn bản (có thanh tiến độ), rồi cộng dồn theo nước–năm."""
    bo = bo_cham(TU_TD, TU_HT)
    cac_rx = pt.regex_tu_khoa(ds_tu_khoa)
    thanh = st.progress(0.0)
    dong = []
    for i, r in enumerate(bang.itertuples(index=False), 1):
        tong, _ = bo.cham(r.text)
        dong.append({"country": r.country, "year": r.year, **tong,
                     **pt.dem_tu_khoa(pt.lam_sach(r.text), cac_rx)})
        if i % 5 == 0 or i == len(bang):
            thanh.progress(i / len(bang), text=t("dang_cham", i=i, n=len(bang)))
    thanh.empty()
    return pt.gop_theo_nam(pd.DataFrame(dong))


with tab2:
    st.markdown(t("tab2_hd"))
    st.download_button(t("tai_mau_csv"), MAU_CSV.encode("utf-8-sig"), file_name="mau_du_lieu.csv", mime="text/csv")
    tep_csv = st.file_uploader(t("tai_csv"), type=["csv"], key="tep_csv")
    tu_khoa_rieng = pt.doc_danh_sach(st.text_input(t("tu_khoa_rieng"), value="sovereign*, sanction*, NATO",
                                                   key="tu_khoa_rieng"))
    if tep_csv is not None:
        noi_dung = tep_csv.getvalue()
        bang = pd.read_csv(io.BytesIO(noi_dung))
        bang.columns = [str(c).strip().lower() for c in bang.columns]
        thieu = {"country", "year", "text"} - set(bang.columns)
        if thieu:
            st.error(t("thieu_cot", c=", ".join(sorted(thieu))))
        else:
            bang["country"] = bang["country"].astype(str).str.strip().str.upper()
            bang["year"] = pd.to_numeric(bang["year"], errors="coerce")
            bang = bang.dropna(subset=["year", "text"])
            bang["year"] = bang["year"].astype(int)
            bang["text"] = bang["text"].astype(str)

            khoa = (hashlib.md5(noi_dung).hexdigest(), TU_TD, TU_HT, tuple(tu_khoa_rieng))
            if st.session_state.get("kq_csv_khoa") != khoa:
                st.session_state["kq_csv"] = cham_bang_csv(bang, tu_khoa_rieng)
                st.session_state["kq_csv_khoa"] = khoa
            kq = st.session_state["kq_csv"]
            st.success(t("da_cham", n=len(bang), k=kq.country.nunique()))

            ds_nuoc = list(kq.groupby("country")["so_van_ban"].sum().sort_values(ascending=False).index)
            if len(ds_nuoc) > 8:
                st.caption(t("toi_da_8"))
            chon = st.multiselect(t("chon_nuoc"), ds_nuoc, default=ds_nuoc[:4], max_selections=8,
                                  format_func=lambda m: f"{ten_nuoc(m)} ({m})", key="nuoc_tab2")
            cac_cot = list(CHI_SO) + [c for c in kq.columns if c.startswith("tk::")]
            cot = st.selectbox(t("chi_so"), cac_cot, format_func=nhan, key="chi_so_tab2")
            ve_duong(kq[kq.country.isin(chon)], cot, mau_on_dinh("mau_tab2", chon),
                     hien_su_kien=False, key="bieu_do_tab2")
            st.dataframe(kq[kq.country.isin(chon)], hide_index=True)
            st.download_button(t("tai_ve_csv"), kq.to_csv(index=False).encode("utf-8-sig"),
                               file_name="ket_qua_theo_nam.csv", mime="text/csv", key="tai_tab2")

# ═════════════════════════════════════════════════════════════════════════════
# 5. TAB 3 – DỮ LIỆU ĐẠI HỘI ĐỒNG LHQ
# ═════════════════════════════════════════════════════════════════════════════
with tab3:
    if DIEM_LHQ is None:
        st.info(t("chua_co_du_lieu"))
    else:
        st.markdown(t("tab3_hd"))
        tat_ca_nuoc = sorted(DIEM_LHQ.country.unique(), key=ten_nuoc)
        mac_dinh = [m for m in ["RUS", "USA", "CHN", "VNM"] if m in tat_ca_nuoc]
        nam_min, nam_max = int(DIEM_LHQ.year.min()), int(DIEM_LHQ.year.max())

        c1, c2, c3 = st.columns([3, 2, 2])
        chon = c1.multiselect(t("chon_nuoc"), tat_ca_nuoc, default=mac_dinh, max_selections=8,
                              format_func=lambda m: f"{ten_nuoc(m)} ({m})", key="nuoc_tab3")
        tu, den = c2.slider(t("khoang_nam"), nam_min, nam_max, (max(nam_min, 1990), nam_max), key="nam_tab3")
        cac_cot = list(CHI_SO) + [c for c in DIEM_LHQ.columns if c.startswith("tk::")]
        cot = c3.selectbox(t("chi_so"), cac_cot, format_func=nhan, key="chi_so_tab3")
        c4, c5 = st.columns(2)
        hien_tb = c4.checkbox(t("hien_tb"), value=True, key="tb_tab3")
        hien_sk = c5.checkbox(t("hien_su_kien"), value=True, key="sk_tab3")

        trong_khoang = DIEM_LHQ[DIEM_LHQ.year.between(tu, den)]
        da_chon = trong_khoang[trong_khoang.country.isin(chon)]
        trung_binh = trong_khoang.groupby("year", as_index=False)[cac_cot].mean() if hien_tb else None
        if chon:
            ve_duong(da_chon, cot, mau_on_dinh("mau_tab3", chon), trung_binh, hien_sk, key="bieu_do_tab3")

            st.subheader(t("buoc_ngoat"))
            st.caption(t("buoc_ngoat_hd"))
            bn = pt.tim_buoc_ngoat(da_chon, cot)
            bn.insert(0, "ten", bn.country.map(ten_nuoc))
            st.dataframe(bn.drop(columns="country").rename(columns={
                "ten": t("nuoc"), "nam_truoc": t("nam_truoc"), "year": t("nam"),
                cot: nhan(cot), "thay_doi": t("thay_doi")}).round(3), hide_index=True)

            st.subheader(t("doc_ky"))
            d1, d2 = st.columns(2)
            nuoc_doc = d1.selectbox(t("nuoc"), chon, format_func=ten_nuoc, key="nuoc_doc")
            cac_nam = sorted(da_chon.loc[da_chon.country == nuoc_doc, "year"].unique(), reverse=True)
            if cac_nam:
                nam_doc = d2.selectbox(t("nam"), cac_nam, key="nam_doc")
                dong = da_chon[(da_chon.country == nuoc_doc) & (da_chon.year == nam_doc)].iloc[0]
                st.markdown(" · ".join(f"{nhan(c)}: **{dinh_dang(c, dong[c])}**" for c in CHI_SO))
                if CAU_LHQ is not None:
                    cau_nam = CAU_LHQ[(CAU_LHQ.country == nuoc_doc) & (CAU_LHQ.year == nam_doc)]
                    for loai in ["thu_dich", "tieu_cuc", "hop_tac"]:
                        nhom = cau_nam[cau_nam.loai == loai]
                        st.markdown(f"**{t('loai_' + loai)}**")
                        if nhom.empty:
                            st.caption(t("khong_co"))
                        for _, r in nhom.iterrows():
                            st.markdown(f"> {r.sentence}")

        st.subheader(t("xep_hang"))
        x1, x2 = st.columns([1, 3])
        nam_xh = x1.selectbox(t("nam"), sorted(trong_khoang.year.unique(), reverse=True), key="nam_xh")
        xh = (DIEM_LHQ[DIEM_LHQ.year == nam_xh][["country", cot]].dropna()
              .sort_values(cot, ascending=False).reset_index(drop=True))
        xh.insert(0, "#", xh.index + 1)
        xh.insert(1, t("nuoc"), xh.country.map(ten_nuoc))
        x2.dataframe(xh.rename(columns={cot: nhan(cot)}), hide_index=True, height=320)

        st.download_button(t("tai_du_lieu_loc"), da_chon.to_csv(index=False).encode("utf-8-sig"),
                           file_name="du_lieu_lhq.csv", mime="text/csv", key="tai_tab3")
        st.caption(t("trich_dan"))
