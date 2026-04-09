import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# --- 1. 系統設定與 CSS 強制顯色優化 ---
st.set_page_config(page_title="產險行動記帳本", layout="wide")

# 加入 CSS 強制指令，解決深色模式導致字體變白的問題
st.markdown("""
    <style>
    /* 強制所有背景為白色，字體為黑色 */
    .stApp {
        background-color: #ffffff !important;
        color: #1a1a1a !important;
    }
    
    /* 針對指標數據 (Metric) 的強制顯色 */
    [data-testid="stMetricValue"] > div { 
        color: #1a1a1a !important; 
        font-weight: 800 !important; 
    }
    [data-testid="stMetricLabel"] > div { 
        color: #555555 !important; 
    }
    
    /* 容器框樣式優化 */
    div[data-testid="metric-container"] {
        background-color: #ffffff !important;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid #eeeeee;
    }

    /* 按鈕樣式強化 */
    .stButton>button { 
        width: 100%; 
        border-radius: 10px; 
        height: 3.5em; 
        font-weight: bold; 
    }
    
    /* 輸入框強制顯色 */
    input {
        color: #1a1a1a !important;
    }
    </style>
    """, unsafe_allow_html=True)

DB_LEDGER = "my_ledger.csv"

# 初始化資料庫
if not os.path.exists(DB_LEDGER):
    df_empty = pd.DataFrame(columns=["日期", "類別", "項目內容", "收支", "金額"])
    df_empty.to_csv(DB_LEDGER, index=False)

def get_tw_time():
    return datetime.utcnow() + timedelta(hours=8)

# --- 2. 登入與安全登出機制 ---
if "auth" not in st.session_state:
    st.session_state.auth = False

# 安全登出邏輯
def logout():
    st.session_state.auth = False
    st.rerun()

if not st.session_state.auth:
    st.title("📑 產險業務行動記帳本")
    pwd = st.text_input("輸入管理密碼", type="password")
    if st.button("確認進入"):
        if pwd == "085799": 
            st.session_state.auth = True
            st.rerun()
    st.stop()

# --- 3. 核心邏輯與數據處理 ---
def load_data():
    return pd.read_csv(DB_LEDGER)

def save_data(df_to_save):
    df_to_save.to_csv(DB_LEDGER, index=False)

tw_now = get_tw_time()
df = load_data()

# 提取既有類別供快速選擇
existing_categories = sorted(df['類別'].unique().tolist()) if not df.empty else ["客戶交際", "油錢/交通", "餐飲伙食"]

# 財務統計計算
df['日期'] = pd.to_datetime(df['日期'])
current_month = tw_now.strftime("%Y-%m")
month_df = df[df['日期'].dt.strftime("%Y-%m") == current_month]
income = month_df[month_df['收支'] == "收入"]['金額'].sum()
expense = month_df[month_df['收支'] == "支出"]['金額'].sum()
balance = income - expense

# --- 4. 介面呈現 (側邊欄登出按鈕) ---
with st.sidebar:
    st.title("⚙️ 控制面板")
    
    # 一鍵登出功能
    if st.button("🔓 安全登出系統", type="primary"):
        logout()
        
    st.divider()
    st.metric("本月結餘", f"${balance:,}", delta=f"{balance:+,}")
    st.info(f"📅 目前時間：{tw_now.strftime('%H:%M')}")

tab1, tab2, tab3 = st.tabs(["➕ 新增帳目", "📊 財務分析", "📜 歷史編輯"])

# --- Tab 1: 新增帳目 ---
with tab1:
    st.subheader("📝 快速記帳")
    with st.form("ledger_form", clear_on_submit=True):
        f1, f2 = st.columns(2)
        date_in = f1.date_input("日期", tw_now)
        type_choice = f2.selectbox("選擇類別", ["直接手動輸入"] + existing_categories)
        manual_type = st.text_input("手動輸入新類別 (若上方選『手動』則填此)")
        
        final_type = manual_type if type_choice == "直接手動輸入" else type_choice
        
        f3, f4 = st.columns(2)
        side_in = f3.radio("收支方向", ["支出", "收入"], horizontal=True)
        amt_in = f4.number_input("金額", min_value=0, step=1)
        
        note_in = st.text_input("項目內容描述")
        
        if st.form_submit_button("確認存檔"):
            if amt_in > 0 and final_type:
                new_row = pd.DataFrame([{
                    "日期": date_in.strftime("%Y-%m-%d"),
                    "類別": final_type.strip(),
                    "項目內容": note_in,
                    "收支": side_in,
                    "金額": amt_in
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                save_data(updated_df)
                st.success(f"✅ 已記錄：{final_type} ${amt_in}")
                st.rerun()

# --- Tab 2 & 3 保持原功能 ---
with tab2:
    st.subheader(f"📅 {current_month} 支出統計")
    if not month_df[month_df['收支'] == "支出"].empty:
        exp_pie = month_df[month_df['收支'] == "支出"].groupby("類別")['金額'].sum()
        st.bar_chart(exp_pie)
    else:
        st.info("尚無支出數據")

with tab3:
    st.subheader("📜 歷史紀錄 (最新 30 筆)")
    display_df = df.iloc[::-1].head(30)
    for i, row in display_df.iterrows():
        color = "🔴" if row['收支'] == "支出" else "🟢"
        with st.expander(f"{row['日期']} | {color} {row['類別']} | ${row['金額']:,}"):
            st.write(f"內容：{row['項目內容']}")
            if st.button(f"🗑️ 刪除", key=f"del_{i}"):
                df_to_del = load_data().drop(i)
                save_data(df_to_del)
                st.rerun()