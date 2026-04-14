import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# --- 1. 系統設定與介面顯色優化 ---
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

# 初始化資料庫
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

# --- 4. 數據預處理 (月份過濾) ---
current_month_str = tw_now.strftime("%Y-%m")
df_calc = df.copy()
df_calc['日期格式'] = pd.to_datetime(df_calc['日期'])
df_calc['月份'] = df_calc['日期格式'].dt.strftime("%Y-%m")

month_df = df_calc[df_calc['月份'] == current_month_str]
month_income = month_df[month_df['收支'] == "收入"]['金額'].sum()
month_expense = month_df[month_df['收支'] == "支出"]['金額'].sum()
month_balance = month_income - month_expense

# --- 5. 介面呈現 (側邊欄加強下載按鈕) ---
with st.sidebar:
    st.title("⚙️ 管理選單")
    if st.button("🔓 安全登出系統", type="primary"):
        st.session_state.auth = False
        st.rerun()
    
    # --- 新增的下載備份按鈕 ---
    st.divider()
    st.subheader("📥 資料備份 (防消失)")
    if os.path.exists(DB_LEDGER) and not df.empty:
        with open(DB_LEDGER, "rb") as file:
            st.download_button(
                label="💾 下載所有帳目備份 (CSV)",
                data=file,
                file_name=f"ledger_backup_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )
        st.caption("建議定期下載存手機，萬一雲端資料重置可供恢復。")
    else:
        st.caption("目前尚無資料可供備份")
    
    st.divider()
    st.metric("本月結餘", f"${int(month_balance):,}", delta=f"{int(month_balance):+,}")
    st.info(f"📅 目前時間：{tw_now.strftime('%H:%M')}")

tab1, tab2, tab3 = st.tabs(["➕ 新增帳目", "📊 財務分析", "📜 歷史編輯"])

# --- Tab 1: 新增帳目 ---
with tab1:
    st.subheader("📝 快速記帳")
    existing_categories = sorted(df['類別'].unique().tolist()) if not df.empty else ["客戶交際", "油錢/交通"]
    with st.form("ledger_form", clear_on_submit=True):
        f1, f2 = st.columns(2)
        date_in = f1.date_input("日期", tw_now.date())
        type_choice = f2.selectbox("選擇既有類別", ["直接手動輸入"] + existing_categories)
        manual_type = st.text_input("手動輸入新類別")
        final_type = manual_type if type_choice == "直接手動輸入" else type_choice
        
        f3, f4 = st.columns(2)
        side_in = f3.radio("收支方向", ["支出", "收入"], horizontal=True)
        amt_in = f4.number_input("金額", min_value=0, step=1)
        note_in = st.text_input("項目內容描述")
        
        if st.form_submit_button("確認存檔"):
            if amt_in > 0 and final_type:
                new_row = pd.DataFrame([{"日期": date_in, "類別": final_type.strip(), "項目內容": note_in, "收支": side_in, "金額": amt_in}])
                save_data(pd.concat([df, new_row], ignore_index=True))
                st.success("✅ 已記錄！")
                st.rerun()

# --- Tab 2: 財務分析 ---
with tab2:
    st.markdown("### 📅 1. 每月收支概況")
    st.caption(f"統計月份：{current_month_str}")
    c1, c2 = st.columns(2)
    c1.metric("本月總收入", f"${int(month_income):,}")
    c2.metric("本月總支出", f"${int(month_expense):,}")
    summary_data = pd.DataFrame({"項目": ["收入", "支出"], "金額": [month_income, month_expense]})
    st.bar_chart(summary_data.set_index("項目"))
    st.divider()
    st.markdown("### 🏆 2. 各類別累計總額")
    col_exp, col_inc = st.columns(2)
    with col_exp:
        st.write("#### 🔴 累計支出排行")
        all_exp = df[df['收支'] == "支出"]
        if not all_exp.empty:
            cat_exp_total = all_exp.groupby("類別")["金額"].sum().sort_values(ascending=False).reset_index()
            st.bar_chart(cat_exp_total.set_index("類別"))
    with col_inc:
        st.write("#### 🟢 累計收入排行")
        all_inc = df[df['收支'] == "收入"]
        if not all_inc.empty:
            cat_inc_total = all_inc.groupby("類別")["金額"].sum().sort_values(ascending=False).reset_index()
            st.bar_chart(cat_inc_total.set_index("類別"))

# --- Tab 3: 歷史編輯 ---
with tab3:
    st.subheader("📜 歷史紀錄維護")
    search_query = st.text_input("🔍 搜尋關鍵字", "").strip()
    filtered_df = df.copy()
    if search_query:
        filtered_df = df[df['類別'].str.contains(search_query, case=False, na=False) | 
                         df['項目內容'].str.contains(search_query, case=False, na=False)]

    for i, row in filtered_df.iloc[::-1].head(50).iterrows():
        label = f"{row['日期']} | {'🔴' if row['收支']=='支出' else '🟢'} {row['類別']} | ${int(row['金額']):,}"
        with st.expander(label):
            with st.form(f"edit_{i}"):
                d = st.date_input("日期", row['日期'], key=f"d{i}")
                c = st.text_input("類別", row['類別'], key=f"c{i}")
                s = st.selectbox("收支", ["支出", "收入"], index=0 if row['收支']=="支出" else 1, key=f"s{i}")
                a = st.number_input("金額", value=int(row['金額']), key=f"a{i}")
                n = st.text_input("內容", row['項目內容'], key=f"n{i}")
                b1, b2 = st.columns(2)
                if b1.form_submit_button("💾 儲存"):
                    df.loc[i] = [d, c, n, s, a]
                    save_data(df)
                    st.rerun()
                if b2.form_submit_button("🗑️ 刪除"):
                    save_data(df.drop(i))
                    st.rerun()