"""
血壓健康儀表板
執行方式：
    pip install streamlit pandas plotly requests
    streamlit run bp_dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime, date
from collections import Counter

# ──────────────────────────────────────────
#  頁面設定
# ──────────────────────────────────────────
st.set_page_config(
    page_title="血壓健康儀表板",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────
#  自訂 CSS
# ──────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;600;700&family=Space+Mono:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans TC', sans-serif; }
.stApp { background: linear-gradient(135deg, #0f1923 0%, #1a2a3a 50%, #0d1f30 100%); color: #e8f4f8; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0d2137 0%, #112940 100%); border-right: 1px solid rgba(64,196,255,0.15); }
[data-testid="stSidebar"] * { color: #c8e6f5 !important; }
.metric-card { background: rgba(255,255,255,0.04); border: 1px solid rgba(64,196,255,0.18); border-radius: 16px; padding: 20px 24px; text-align: center; backdrop-filter: blur(8px); transition: transform 0.2s ease; }
.metric-card:hover { transform: translateY(-3px); box-shadow: 0 8px 32px rgba(64,196,255,0.12); }
.metric-label { font-size: 0.78rem; letter-spacing: 0.12em; text-transform: uppercase; color: #7ec8e3; margin-bottom: 6px; }
.metric-value { font-family: 'Space Mono', monospace; font-size: 2.2rem; font-weight: 700; color: #fff; line-height: 1; }
.metric-unit  { font-size: 0.85rem; color: #7ec8e3; margin-top: 4px; }
.badge { display: inline-block; padding: 4px 14px; border-radius: 20px; font-size: 0.82rem; font-weight: 600; letter-spacing: 0.05em; margin-top: 6px; }
.badge-normal   { background: rgba(52,211,153,0.2);  color: #34d399; border: 1px solid #34d399; }
.badge-elevated { background: rgba(251,191,36,0.2);  color: #fbbf24; border: 1px solid #fbbf24; }
.badge-high1    { background: rgba(251,146,60,0.2);  color: #fb923c; border: 1px solid #fb923c; }
.badge-high2    { background: rgba(239,68,68,0.2);   color: #ef4444; border: 1px solid #ef4444; }
.badge-crisis   { background: rgba(220,38,38,0.4);   color: #fca5a5; border: 1px solid #fca5a5; }
.badge-low      { background: rgba(99,179,237,0.2);  color: #63b3ed; border: 1px solid #63b3ed; }
.weather-card { background: rgba(255,255,255,0.04); border: 1px solid rgba(64,196,255,0.15); border-radius: 16px; padding: 18px 22px; backdrop-filter: blur(8px); }
.weather-title { font-size: 0.75rem; letter-spacing: 0.12em; text-transform: uppercase; color: #7ec8e3; margin-bottom: 12px; }
.weather-temp  { font-family: 'Space Mono', monospace; font-size: 2.8rem; font-weight: 700; color: #fff; line-height: 1; }
.weather-info  { font-size: 0.88rem; color: #a8d8ea; margin-top: 8px; }
.section-title { font-size: 0.75rem; letter-spacing: 0.14em; text-transform: uppercase; color: #40c4ff; border-bottom: 1px solid rgba(64,196,255,0.2); padding-bottom: 8px; margin-bottom: 16px; }
.info-banner { background: rgba(64,196,255,0.06); border-left: 3px solid #40c4ff; border-radius: 0 8px 8px 0; padding: 10px 16px; font-size: 0.88rem; color: #a8d8ea; margin-bottom: 12px; }
[data-testid="stDataFrame"] { background: rgba(255,255,255,0.03) !important; border-radius: 12px; border: 1px solid rgba(64,196,255,0.15); }
[data-testid="stDataFrame"] * { color: #c8e6f5 !important; background: transparent !important; }
[data-testid="stDataFrame"] th { background: rgba(64,196,255,0.08) !important; color: #40c4ff !important; }
[data-testid="stMetric"] { background: rgba(255,255,255,0.03); border: 1px solid rgba(64,196,255,0.12); border-radius: 12px; padding: 12px 16px; }
[data-testid="stMetricValue"] { color: #ffffff !important; }
[data-testid="stMetricLabel"] { color: #7ec8e3 !important; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────
#  Session State 初始化
# ──────────────────────────────────────────
HEADER = ["日期時間", "收縮壓", "舒張壓", "心跳", "狀態", "溫度(°C)", "濕度(%)", "生活標籤", "備註"]
if "history" not in st.session_state:
    st.session_state.history = []

# ──────────────────────────────────────────
#  血壓分類
# ──────────────────────────────────────────
def classify_bp(systolic, diastolic):
    if systolic < 90 or diastolic < 60:
        return "低血壓", "badge-low"
    elif systolic < 120 and diastolic < 80:
        return "正常", "badge-normal"
    elif systolic < 130 and diastolic < 80:
        return "血壓偏高", "badge-elevated"
    elif systolic < 140 or diastolic < 90:
        return "高血壓第一期", "badge-high1"
    elif systolic < 180 and diastolic < 120:
        return "高血壓第二期", "badge-high2"
    else:
        return "高血壓危象", "badge-crisis"

# ──────────────────────────────────────────
#  個人基準線
# ──────────────────────────────────────────
def compute_personal_baseline(df):
    if df.empty:
        return None
    df = df.copy()
    df["_dt"] = pd.to_datetime(df["日期時間"], format="%m/%d %H:%M", errors="coerce")
    df["_dt"] = df["_dt"].apply(lambda x: x.replace(year=datetime.now().year) if pd.notnull(x) else x)
    two_weeks_ago = datetime.now() - pd.Timedelta(days=14)
    df_base = df[df["_dt"] >= two_weeks_ago].copy()
    if len(df_base) < 3:
        return None
    for col in ["收縮壓", "舒張壓"]:
        df_base[col] = pd.to_numeric(df_base[col], errors="coerce")
    return {
        "sys_mean": df_base["收縮壓"].mean(), "sys_std": df_base["收縮壓"].std(),
        "dia_mean": df_base["舒張壓"].mean(), "dia_std": df_base["舒張壓"].std(),
        "count": len(df_base),
    }

def personal_baseline_alert(systolic, diastolic, baseline):
    if baseline is None:
        return False, []
    alerts, is_abnormal = [], False
    sys_upper = baseline["sys_mean"] + 1.5 * max(baseline["sys_std"], 3)
    dia_upper = baseline["dia_mean"] + 1.5 * max(baseline["dia_std"], 3)
    if systolic > sys_upper:
        alerts.append(f"📊 收縮壓比個人兩週基準（{baseline['sys_mean']:.0f} mmHg）高出 **{systolic - baseline['sys_mean']:.0f} mmHg**，出現個人異常波動。")
        is_abnormal = True
    if diastolic > dia_upper:
        alerts.append(f"📊 舒張壓比個人兩週基準（{baseline['dia_mean']:.0f} mmHg）高出 **{diastolic - baseline['dia_mean']:.0f} mmHg**，出現個人異常波動。")
        is_abnormal = True
    return is_abnormal, alerts

# ──────────────────────────────────────────
#  血壓建議
# ──────────────────────────────────────────
def bp_advice(systolic, diastolic, temp, humidity):
    advice = []
    if systolic >= 180 or diastolic >= 120:
        advice.append("🚨 血壓已達危象標準，請立即就醫或撥打 119，不要自行服藥或等待觀察。")
    elif systolic >= 140 or diastolic >= 90:
        advice.append("⚠️ 血壓達高血壓第二期，建議本週內安排就醫，若有頭痛、胸悶、視力模糊請立即就診。")
        advice.append("💊 若已服用降壓藥，請勿自行停藥或調整劑量。")
    elif systolic >= 130 or diastolic >= 80:
        advice.append("📋 血壓偏高，建議減少鹽分攝取（每日 < 6g），並規律量測追蹤。")
        advice.append("🚶 每天進行 30 分鐘中等強度運動（如快走）有助於降低血壓。")
    if isinstance(temp, (int, float)):
        if temp <= 18 and (systolic >= 130 or diastolic >= 80):
            advice.append("🧥 氣溫偏低，建議開啟暖氣將室內維持在 20–25°C。")
            advice.append("🛁 避免突然進出冷熱環境，溫差過大對心血管負擔大。")
            advice.append("🧣 外出時注意保暖，尤其頸部、手腕、腳踝。")
        elif temp >= 30 and (systolic >= 130 or diastolic >= 80):
            advice.append("🌡️ 高溫容易使心跳加速，請避免在正午外出，多補充水分。")
    if isinstance(humidity, (int, float)) and humidity >= 80 and (systolic >= 130 or diastolic >= 80):
        advice.append("💧 高濕度悶熱環境增加心臟負擔，建議待在通風或有冷氣的室內。")
    return advice

# ──────────────────────────────────────────
#  AI 歸因分析
# ──────────────────────────────────────────
def ai_attribution_analysis(df):
    insights = []
    if df.empty or "生活標籤" not in df.columns or len(df) < 5:
        return insights
    df = df.copy()
    for col in ["收縮壓", "舒張壓", "溫度(°C)"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["異常"] = (df["收縮壓"] >= 130) | (df["舒張壓"] >= 80)
    TAGS = ["😴 睡眠不足","💊 忘記服藥","🍱 聚餐吃大餐","🏃 剛運動完","😰 壓力較大","🍺 飲酒","☕ 喝咖啡/茶","🚬 抽菸","😷 身體不適"]
    tag_results = []
    for tag in TAGS:
        has_tag = df["生活標籤"].str.contains(tag, na=False)
        count = has_tag.sum()
        if count < 2:
            continue
        abnormal_rate = df[has_tag]["異常"].mean()
        normal_rate   = df[~has_tag]["異常"].mean() if (~has_tag).sum() > 0 else 0
        if abnormal_rate >= 0.6 and abnormal_rate > normal_rate + 0.2:
            tag_results.append((tag, abnormal_rate, count))
    for tag, rate, count in sorted(tag_results, key=lambda x: -x[1]):
        insights.append(f"🏷️ **{tag}** 出現時，您的血壓超標機率為 **{rate*100:.0f}%**（共 {count} 次）")
    has_temp = df["溫度(°C)"].notna()
    if has_temp.sum() >= 3:
        cold = df["溫度(°C)"] <= 18
        for tag in ["😴 睡眠不足","💊 忘記服藥","😰 壓力較大"]:
            has_tag = df["生活標籤"].str.contains(tag, na=False)
            combo = cold & has_tag
            if combo.sum() >= 2:
                rate = df[combo]["異常"].mean()
                if rate >= 0.7:
                    insights.append(f"🌡️+🏷️ **氣溫低於 18°C** 且 **{tag}** 同時出現時，超標機率高達 **{rate*100:.0f}%**（共 {combo.sum()} 次）")
    abnormal_df = df[df["異常"] & df["生活標籤"].notna() & (df["生活標籤"] != "")]
    if len(abnormal_df) >= 2:
        all_tags = []
        for tags in abnormal_df["生活標籤"]:
            all_tags.extend([t.strip() for t in str(tags).split("、") if t.strip()])
        if all_tags:
            top_tag, top_count = Counter(all_tags).most_common(1)[0]
            if top_count >= 2:
                insights.append(f"📌 血壓超標時最常出現的標籤是 **{top_tag}**（共 {top_count} 次），建議特別留意。")
    return insights

# ──────────────────────────────────────────
#  天氣 API
# ──────────────────────────────────────────
@st.cache_data(ttl=600)
def fetch_weather(lat, lon):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,weather_code"
        "&timezone=Asia%2FTaipei"
    )
    try:
        resp = requests.get(url, timeout=6)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None

def weather_code_to_desc(code):
    wmo = {0:"☀️ 晴天",1:"🌤 大致晴朗",2:"⛅ 局部多雲",3:"☁️ 陰天",45:"🌫 霧",51:"🌦 毛毛雨",61:"🌧 小雨",63:"🌧 中雨",65:"🌧 大雨",80:"🌦 陣雨",95:"⛈ 雷陣雨"}
    return wmo.get(code, f"代碼 {code}")

# ──────────────────────────────────────────
#  城市選項
# ──────────────────────────────────────────
CITY_OPTIONS = {
    "台北市": (25.03, 121.56), "新北市": (25.01, 121.47),
    "台中市": (24.14, 120.68), "高雄市": (22.63, 120.30), "台南市": (22.99, 120.20),
}

# ──────────────────────────────────────────
#  側邊欄
# ──────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🩺 血壓紀錄輸入")
    st.markdown("---")
    record_date = st.date_input("📅 量測日期", value=date.today())
    from datetime import timezone, timedelta
    tw_tz = timezone(timedelta(hours=8))
    current_time = datetime.now(tw_tz).time().replace(second=0, microsecond=0)
    if "record_time" not in st.session_state:
        st.session_state.record_time = current_time
    record_time = st.time_input("⏰ 量測時間", value=current_time, step=60, key="record_time")

    st.markdown("### 血壓數值")
    st.info("💡 建議坐下休息 5 分鐘後，量 3 次取平均，結果更準確。")
    systolic  = st.slider("收縮壓（高壓）mmHg", min_value=60,  max_value=250, value=115, step=1)
    diastolic = st.slider("舒張壓（低壓）mmHg", min_value=40,  max_value=150, value=75,  step=1)
    pulse     = st.slider("心跳 bpm",            min_value=30,  max_value=200, value=70,  step=1)

    st.markdown("### 備註")
    note = st.text_input("備註（可選）", placeholder="餐後、運動後…")

    st.markdown("### 🏷️ 生活狀態標籤")
    st.caption("選擇今天量測前的狀況（可多選）")
    LIFESTYLE_OPTIONS = ["😴 睡眠不足","💊 忘記服藥","🍱 聚餐吃大餐","🏃 剛運動完","😰 壓力較大","🍺 飲酒","☕ 喝咖啡/茶","🚬 抽菸","😷 身體不適"]
    selected_tags = st.multiselect("生活標籤", LIFESTYLE_OPTIONS, label_visibility="collapsed")
    tags_str = "、".join(selected_tags) if selected_tags else ""

    st.markdown("---")
    st.markdown("### 🌍 天氣位置設定")
    selected_city = st.selectbox("選擇城市", list(CITY_OPTIONS.keys()))

    st.markdown("---")
    add_btn   = st.button("➕ 新增紀錄", use_container_width=True, type="primary")
    clear_btn = st.button("🗑 清除所有紀錄", use_container_width=True)

lat, lon = CITY_OPTIONS[selected_city]

if add_btn:
    label_text, _ = classify_bp(systolic, diastolic)
    dt_str = datetime.combine(record_date, record_time).strftime("%m/%d %H:%M")
    cur_weather = fetch_weather(lat, lon)
    cur_temp, cur_humidity = "--", "--"
    if cur_weather:
        cur_temp     = cur_weather["current"].get("temperature_2m", "--")
        cur_humidity = cur_weather["current"].get("relative_humidity_2m", "--")
    st.session_state.history.append({
        "日期時間": dt_str, "收縮壓": systolic, "舒張壓": diastolic,
        "心跳": pulse, "狀態": label_text, "溫度(°C)": cur_temp,
        "濕度(%)": cur_humidity, "生活標籤": tags_str, "備註": note,
    })
    st.success("✅ 紀錄已新增！")

if clear_btn:
    st.session_state.history = []
    st.warning("紀錄已清除。")

# ──────────────────────────────────────────
#  主畫面
# ──────────────────────────────────────────
from datetime import timezone, timedelta
TW_TZ = timezone(timedelta(hours=8))

st.markdown("<h1 style='color:#40c4ff;font-family:Noto Sans TC;font-weight:700;margin-bottom:4px;'>血壓健康儀表板</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='color:#7ec8e3;font-size:0.88rem;margin-bottom:24px;'>最後更新：{datetime.now(TW_TZ).strftime('%Y-%m-%d %H:%M')}</p>", unsafe_allow_html=True)

label, badge_cls = classify_bp(systolic, diastolic)

# 取得天氣（供建議使用）
cur_weather_now = fetch_weather(lat, lon)
now_temp     = cur_weather_now["current"].get("temperature_2m", "--") if cur_weather_now else "--"
now_humidity = cur_weather_now["current"].get("relative_humidity_2m", "--") if cur_weather_now else "--"

# 個人基準線
df_all = pd.DataFrame(st.session_state.history) if st.session_state.history else pd.DataFrame(columns=HEADER)
if not df_all.empty:
    for col in ["收縮壓", "舒張壓", "心跳"]:
        df_all[col] = pd.to_numeric(df_all[col], errors="coerce")
baseline = compute_personal_baseline(df_all)

# ── 警告 ─────────────────────────────────
if systolic >= 180 or diastolic >= 120:
    st.error("🚨 **高血壓危象！** 收縮壓或舒張壓已達危險值，請立即就醫或撥打 119。")
elif systolic >= 140 or diastolic >= 90:
    st.warning("⚠️ **血壓偏高，建議就醫。** 已達高血壓第二期標準（≥140/90 mmHg），請盡快諮詢醫師。")

if baseline:
    is_abnormal, base_alerts = personal_baseline_alert(systolic, diastolic, baseline)
    if is_abnormal and not (systolic >= 140 or diastolic >= 90):
        st.warning("🤖 **個人動態警戒：** 雖未超過醫學標準，但相對於您的個人基準出現異常波動。")
        for a in base_alerts:
            st.markdown(f"> {a}")

advice_list = bp_advice(systolic, diastolic, now_temp, now_humidity)
if advice_list:
    with st.expander("💡 健康建議（點擊展開）", expanded=True):
        for a in advice_list:
            st.markdown(f"- {a}")

# 個人基準資訊列
if baseline:
    baseline_info = f"🤖 個人兩週基準：收縮壓 **{baseline['sys_mean']:.0f}** mmHg｜舒張壓 **{baseline['dia_mean']:.0f}** mmHg（依 {baseline['count']} 筆計算）"
else:
    baseline_info = "🤖 個人基準學習中，累積 3 筆以上兩週內紀錄後將自動啟用動態警戒。"

# ── 指標卡片 ──────────────────────────────
col1, col2, col3, col4 = st.columns(4)
for col, (lbl, val, unit) in zip([col1,col2,col3,col4],[("收縮壓",systolic,"mmHg"),("舒張壓",diastolic,"mmHg"),("心跳",pulse,"bpm"),("狀態",label,"")]):
    with col:
        if lbl == "狀態":
            st.markdown(f'<div class="metric-card"><div class="metric-label">{lbl}</div><div style="margin-top:12px;"><span class="badge {badge_cls}">{val}</span></div><div class="metric-unit" style="margin-top:10px;">依 AHA 準則</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="metric-card"><div class="metric-label">{lbl}</div><div class="metric-value">{val}</div><div class="metric-unit">{unit}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f'<div class="info-banner">{baseline_info}</div>', unsafe_allow_html=True)

# ── 天氣 + 折線圖 ──────────────────────────
weather_col, chart_col = st.columns([1, 2.5])

with weather_col:
    st.markdown('<p class="section-title">🌤 即時天氣</p>', unsafe_allow_html=True)
    if cur_weather_now:
        cur = cur_weather_now["current"]
        temp     = cur.get("temperature_2m","--")
        humidity = cur.get("relative_humidity_2m","--")
        pressure = cur.get("surface_pressure","--")
        wind     = cur.get("wind_speed_10m","--")
        wcode    = cur.get("weather_code",0)
        st.markdown(f"""<div class="weather-card">
            <div class="weather-title">📍 {selected_city}</div>
            <div class="weather-temp">{temp}°C</div>
            <div class="weather-info">{weather_code_to_desc(wcode)}</div>
            <hr style="border-color:rgba(64,196,255,0.12);margin:12px 0;">
            <div class="weather-info">💧 濕度：{humidity}%</div>
            <div class="weather-info">🔵 氣壓：{pressure} hPa</div>
            <div class="weather-info">💨 風速：{wind} km/h</div>
        </div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if isinstance(pressure,(int,float)) and pressure < 1000:
            st.markdown('<div class="info-banner">⚠️ 氣壓偏低，低氣壓環境可能使血壓升高，請多留意。</div>', unsafe_allow_html=True)
        elif isinstance(humidity,(int,float)) and humidity > 80:
            st.markdown('<div class="info-banner">💧 濕度偏高，悶熱天氣可能影響心血管，注意補水。</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="info-banner">✅ 今日天氣狀況良好，適合量測血壓。</div>', unsafe_allow_html=True)
    else:
        st.warning("⚠️ 無法取得天氣資料。")

with chart_col:
    st.markdown('<p class="section-title">📈 血壓趨勢折線圖</p>', unsafe_allow_html=True)
    if df_all.empty:
        demo = pd.DataFrame([
            {"日期時間":"05/01 08:00","收縮壓":118,"舒張壓":76,"心跳":70},
            {"日期時間":"05/02 08:00","收縮壓":121,"舒張壓":79,"心跳":68},
            {"日期時間":"05/03 08:00","收縮壓":116,"舒張壓":74,"心跳":65},
            {"日期時間":"05/04 08:00","收縮壓":122,"舒張壓":80,"心跳":72},
            {"日期時間":"05/05 08:00","收縮壓":systolic,"舒張壓":diastolic,"心跳":pulse},
        ])
        df_chart = demo
        st.caption("（目前顯示示範資料，新增紀錄後將顯示您的實際數據）")
    else:
        df_chart = df_all

    fig = go.Figure()
    fig.add_hrect(y0=90, y1=120, fillcolor="rgba(52,211,153,0.06)", line_width=0, annotation_text="正常收縮壓範圍", annotation_position="top left", annotation_font=dict(size=10,color="#34d399"))
    fig.add_hrect(y0=60, y1=80, fillcolor="rgba(99,179,237,0.06)", line_width=0, annotation_text="正常舒張壓範圍", annotation_position="bottom left", annotation_font=dict(size=10,color="#63b3ed"))
    fig.add_trace(go.Scatter(x=df_chart["日期時間"], y=pd.to_numeric(df_chart["收縮壓"],errors="coerce"), mode="lines+markers", name="收縮壓", line=dict(color="#ef4444",width=2.5), marker=dict(size=7,color="#ef4444",line=dict(color="white",width=1.5)), hovertemplate="<b>收縮壓</b>: %{y} mmHg<extra></extra>"))
    fig.add_trace(go.Scatter(x=df_chart["日期時間"], y=pd.to_numeric(df_chart["舒張壓"],errors="coerce"), mode="lines+markers", name="舒張壓", line=dict(color="#40c4ff",width=2.5), marker=dict(size=7,color="#40c4ff",line=dict(color="white",width=1.5)), hovertemplate="<b>舒張壓</b>: %{y} mmHg<extra></extra>"))
    fig.add_trace(go.Scatter(x=df_chart["日期時間"], y=pd.to_numeric(df_chart["心跳"],errors="coerce"), mode="lines+markers", name="心跳", line=dict(color="#fbbf24",width=1.8,dash="dot"), marker=dict(size=6,symbol="diamond",color="#fbbf24"), yaxis="y2", hovertemplate="<b>心跳</b>: %{y} bpm<extra></extra>"))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Noto Sans TC",color="#c8e6f5"),
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1,bgcolor="rgba(0,0,0,0)",bordercolor="rgba(64,196,255,0.2)",borderwidth=1),
        xaxis=dict(showgrid=True,gridcolor="rgba(64,196,255,0.08)"),
        yaxis=dict(title="血壓 (mmHg)",showgrid=True,gridcolor="rgba(64,196,255,0.08)",range=[50,180]),
        yaxis2=dict(title=dict(text="心跳 (bpm)",font=dict(color="#fbbf24")),overlaying="y",side="right",showgrid=False,range=[40,160],tickfont=dict(color="#fbbf24")),
        hovermode="x unified", margin=dict(l=10,r=10,t=10,b=10), height=340,
    )
    st.plotly_chart(fig, use_container_width=True)

# ── 近三次平均 ────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<p class="section-title">🔢 近三次量測平均</p>', unsafe_allow_html=True)

if not df_all.empty:
    df_recent = df_all.copy()
    df_recent["_dt"] = pd.to_datetime(df_recent["日期時間"], format="%m/%d %H:%M", errors="coerce")
    df_recent["_dt"] = df_recent["_dt"].apply(lambda x: x.replace(year=datetime.now().year) if pd.notnull(x) else x)
    df_recent = df_recent.sort_values("_dt").reset_index(drop=True)

    valid_rows = []
    last_idx = len(df_recent) - 1
    for i in range(last_idx, max(last_idx-5,-1), -1):
        if not valid_rows:
            valid_rows.append(i)
        else:
            dt_diff = abs((df_recent.loc[valid_rows[-1],"_dt"] - df_recent.loc[i,"_dt"]).total_seconds())
            if dt_diff <= 3600:
                valid_rows.append(i)
        if len(valid_rows) == 3:
            break
    df_avg = df_recent.loc[valid_rows[::-1]]

    if len(df_avg) == 1:
        st.info("目前 1 小時內只有 1 筆紀錄，建議再量 1–2 次後查看平均。")
        st.dataframe(df_avg[["日期時間","收縮壓","舒張壓","心跳","狀態"]], use_container_width=True, hide_index=True)
    else:
        avg_sys = df_avg["收縮壓"].mean()
        avg_dia = df_avg["舒張壓"].mean()
        avg_pul = df_avg["心跳"].mean()
        avg_label, avg_badge = classify_bp(int(avg_sys), int(avg_dia))
        st.markdown(f"根據最近 **{len(df_avg)} 筆**（1 小時內）量測計算：")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("平均收縮壓", f"{avg_sys:.0f} mmHg")
        r2.metric("平均舒張壓", f"{avg_dia:.0f} mmHg")
        r3.metric("平均心跳",   f"{avg_pul:.0f} bpm")
        with r4:
            st.markdown(f'<div class="metric-card" style="padding:12px 16px;"><div class="metric-label">平均狀態</div><div style="margin-top:8px;"><span class="badge {avg_badge}">{avg_label}</span></div></div>', unsafe_allow_html=True)
        with st.expander("查看納入計算的紀錄"):
            st.dataframe(df_avg[["日期時間","收縮壓","舒張壓","心跳","狀態"]], use_container_width=True, hide_index=True)
else:
    st.info("尚無紀錄，無法計算近三次平均。")

# ── 歷史紀錄 ──────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<p class="section-title">📋 歷史紀錄</p>', unsafe_allow_html=True)

if not df_all.empty:
    df_history = df_all.copy()
    df_history["_dt"] = pd.to_datetime(df_history["日期時間"], format="%m/%d %H:%M", errors="coerce")
    df_history["_dt"] = df_history["_dt"].apply(lambda x: x.replace(year=datetime.now().year) if pd.notnull(x) else x)
    today = datetime.now(TW_TZ)
    df_today = df_history[df_history["_dt"].dt.date == today.date()]
    week_start = today.date() - pd.Timedelta(days=today.weekday())
    df_week  = df_history[df_history["_dt"].dt.date >= week_start]
    df_morning = df_history[(df_history["_dt"].dt.hour >= 5)  & (df_history["_dt"].dt.hour < 12)]
    df_evening = df_history[(df_history["_dt"].dt.hour >= 18) & (df_history["_dt"].dt.hour < 24)]

    st.markdown("#### 📊 血壓統計摘要")
    tab1, tab2, tab3, tab4 = st.tabs(["📅 今日", "🗓 本週", "🌅 早晚對比", "🤖 AI 歸因分析"])

    with tab1:
        if df_today.empty:
            st.info("今日尚無量測紀錄。")
        else:
            c1,c2,c3 = st.columns(3)
            c1.metric("今日平均收縮壓", f"{df_today['收縮壓'].mean():.0f} mmHg")
            c2.metric("今日平均舒張壓", f"{df_today['舒張壓'].mean():.0f} mmHg")
            c3.metric("今日平均心跳",   f"{df_today['心跳'].mean():.0f} bpm")
            st.caption(f"共 {len(df_today)} 筆紀錄")

    with tab2:
        if df_week.empty:
            st.info("本週尚無量測紀錄。")
        else:
            c1,c2,c3 = st.columns(3)
            c1.metric("本週平均收縮壓", f"{df_week['收縮壓'].mean():.0f} mmHg", delta=f"{df_week['收縮壓'].iloc[-1]-df_week['收縮壓'].mean():.0f}", delta_color="inverse")
            c2.metric("本週平均舒張壓", f"{df_week['舒張壓'].mean():.0f} mmHg", delta=f"{df_week['舒張壓'].iloc[-1]-df_week['舒張壓'].mean():.0f}", delta_color="inverse")
            c3.metric("本週平均心跳",   f"{df_week['心跳'].mean():.0f} bpm",    delta=f"{df_week['心跳'].iloc[-1]-df_week['心跳'].mean():.0f}", delta_color="inverse")
            st.caption(f"共 {len(df_week)} 筆（本週從 {week_start.strftime('%m/%d')} 起算）")

    with tab3:
        c1,c2 = st.columns(2)
        with c1:
            st.markdown("**🌅 早上（05:00–11:59）**")
            if df_morning.empty:
                st.info("尚無早上量測紀錄")
            else:
                st.metric("平均收縮壓", f"{df_morning['收縮壓'].mean():.0f} mmHg")
                st.metric("平均舒張壓", f"{df_morning['舒張壓'].mean():.0f} mmHg")
                st.caption(f"共 {len(df_morning)} 筆")
        with c2:
            st.markdown("**🌙 晚上（18:00–23:59）**")
            if df_evening.empty:
                st.info("尚無晚上量測紀錄")
            else:
                st.metric("平均收縮壓", f"{df_evening['收縮壓'].mean():.0f} mmHg")
                st.metric("平均舒張壓", f"{df_evening['舒張壓'].mean():.0f} mmHg")
                st.caption(f"共 {len(df_evening)} 筆")
        if not df_morning.empty and not df_evening.empty:
            diff_sys = abs(df_morning['收縮壓'].mean() - df_evening['收縮壓'].mean())
            if diff_sys >= 15:
                st.warning(f"⚠️ 早晚收縮壓差異達 {diff_sys:.0f} mmHg，波動較大，建議諮詢醫師。")
            else:
                st.success(f"✅ 早晚收縮壓差異為 {diff_sys:.0f} mmHg，血壓控制穩定。")

    with tab4:
        insights = ai_attribution_analysis(df_history)
        if not insights:
            st.info("資料累積 5 筆以上且有生活標籤紀錄後，AI 將自動分析您的血壓風險因子。")
        else:
            for ins in insights:
                st.markdown(f"- {ins}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### 📋 完整紀錄")
    c1,c2,c3 = st.columns(3)
    c1.metric("整體平均收縮壓", f"{df_history['收縮壓'].mean():.0f} mmHg", delta=f"{df_history['收縮壓'].iloc[-1]-df_history['收縮壓'].mean():.0f}", delta_color="inverse")
    c2.metric("整體平均舒張壓", f"{df_history['舒張壓'].mean():.0f} mmHg", delta=f"{df_history['舒張壓'].iloc[-1]-df_history['舒張壓'].mean():.0f}", delta_color="inverse")
    c3.metric("整體平均心跳",   f"{df_history['心跳'].mean():.0f} bpm",    delta=f"{df_history['心跳'].iloc[-1]-df_history['心跳'].mean():.0f}", delta_color="inverse")

    st.dataframe(df_history[["日期時間","收縮壓","舒張壓","心跳","狀態","溫度(°C)","濕度(%)","生活標籤","備註"]], use_container_width=True, hide_index=True)
    csv = df_history.drop(columns=["_dt"]).to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 下載 CSV", csv, "血壓紀錄.csv", "text/csv")
else:
    st.info("尚無紀錄。請在左側側邊欄輸入血壓數值並按「新增紀錄」。")

with st.expander("📖 血壓分類對照表（AHA 準則）"):
    st.markdown("""
| 分類 | 收縮壓 | | 舒張壓 |
|------|--------|---|--------|
| 低血壓 | < 90 | 或 | < 60 |
| 正常 | < 120 | 且 | < 80 |
| 血壓偏高 | 120–129 | 且 | < 80 |
| 高血壓第一期 | 130–139 | 或 | 80–89 |
| 高血壓第二期 | ≥ 140 | 或 | ≥ 90 |
| 高血壓危象 | > 180 | 或 | > 120 |

> 本儀表板僅供健康追蹤參考，不可替代專業醫療診斷。如有疑慮，請諮詢醫師。
""")
