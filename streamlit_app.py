import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# --- 1. 系統設定與 CSS 強制顯色 ---
st.set_page_config(page_title="產險行動記帳本", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #ffffff !important; color: #1a1a1a !important; }
    [data-testid="stMetricValue"] > div { color: #1a1a1a !important; font-weight: 800 !important; }
    div[data-testid="metric-container"] {
        background-color: #ffffff !important;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid #eeeeee;
    }
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; font-weight: bold; }
    input { color: #1a1a1a !important; }
    </style>
    """, unsafe_allow_html=True)

DB_LEDGER = "my_ledger.csv"

if not os.path.exists(DB_LEDGER):
    df_empty = pd.DataFrame(columns=["日期", "類別", "項目內容", "收支", "金額"])
    df_empty.to_csv(DB_LEDGER, index=False)

def get_tw_time():
    return datetime.utcnow() + timedelta(hours=8)

# --- 2. 登入與安全登出 ---
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("📑 產險業務行動記帳本")
    pwd = st.text_input("輸入管理密碼", type="password")
    if st.button("確認進入"):
        if pwd == "085799": 
            st.session_state.auth = True
            st.rerun()
    st.stop()

# --- 3. 核心邏輯 ---
def load_data():
    temp_df = pd.read_csv(DB_LEDGER)
    temp_df['日期'] = pd.to_datetime(temp_df['日期']).dt.date
    return temp_df

def save_data(df_to_save):
    df_to_save.to_csv(DB_LEDGER, index=False)

tw_now = get_tw_time()
df = load_data()

# 財務統計計算
current_month = tw_now.strftime("%Y-%m")
df_for_calc = df.copy()
df_for_calc['月'] = pd.to_datetime(df_for_calc['日期']).dt.strftime("%Y-%m")
month_df = df_for_calc[df_for_calc['月'] == current_month]

income = month_df[month_df['收支'] == "收入"]['金額'].sum()
expense = month_df[month_df['收支'] == "支出"]['金額'].sum()
balance = income - expense

# --- 4. 介面呈現 ---
with st.sidebar:
    st.title("⚙️ 控制面板")
    if st.button("🔓 安全登出系統", type="primary"):
        st.session_state.auth = False
        st.rerun()
    st.divider()
    st.metric("本月結餘", f"${balance:,