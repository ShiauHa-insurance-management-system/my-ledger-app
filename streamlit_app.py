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
    temp_df['日期'] = pd.to_datetime(temp_df['日期']).dt.date # 統一日期格式
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
    st.metric("本月結餘", f"${balance:,}", delta=f"{balance:+,}")
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
        manual_type = st.text_input("手動輸入新類別 (若上方選手動則填此)")
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

# --- Tab 2: 財務分析 (個別類別加總) ---
with tab2:
    st.subheader(f"📅 {current_month} 個別類別加總分析")
    c1, c2 = st.columns(2)
    c1.metric("本月總收入", f"${income:,}")
    c2.metric("本月總支出", f"${expense:,}")
    
    st.divider()
    
    # 個別類別支出排行榜
    exp_only = month_df[month_df['收支'] == "支出"]
    if not exp_only.empty:
        st.write("### 🔴 支出類別詳細統計")
        # 按類別加總並排序
        cat_sum = exp_only.groupby("類別")["金額"].sum().sort_values(ascending=False).reset_index()
        cat_sum.columns = ["支出類別", "加總金額"]
        
        # 顯示清單
        for _, r in cat_sum.iterrows():
            st.write(f"🔹 **{r['支出類別']}**：`${r['加總金額']:,}`")
        
        # 顯示圖表
        st.bar_chart(cat_sum.set_index("支出類別"))
    
    # 個別類別收入排行榜
    inc_only = month_df[month_df['收支'] == "收入"]
    if not inc_only.empty:
        st.write("### 🟢 收入類別詳細統計")
        cat_inc_sum = inc_only.groupby("類別")["金額"].sum().sort_values(ascending=False).reset_index()
        cat_inc_sum.columns = ["收入類別", "加總金額"]
        
        for _, r in cat_inc_sum.iterrows():
            st.write(f"🔸 **{r['收入類別']}**：`${r['加總金額']:,}`")
        st.bar_chart(cat_inc_sum.set_index("收入類別"))

# --- Tab 3: 歷史編輯 (修改與刪除) ---
with tab3:
    st.subheader("📜 歷史紀錄維護 (可直接修改)")
    # 顯示最近的 50 筆
    for i, row in df.iloc[::-1].iterrows():
        expander_label = f"{row['日期']} | {'🔴' if row['收支']=='支出' else '🟢'} {row['類別']} | ${row['金額']:,}"
        with st.expander(expander_label):
            with st.form(f"edit_form_{i}"):
                e1, e2 = st.columns(2)
                new_date = e1.date_input("修改日期", row['日期'], key=f"d_{i}")
                new_cat = e2.text_input("修改類別", row['類別'], key=f"c_{i}")
                
                e3, e4 = st.columns(2)
                new_side = e3.selectbox("修改方向", ["支出", "收入"], index=0 if row['收支']=="支出" else 1, key=f"s_{i}")
                new_amt = e4.number_input("修改金額", value=int(row['金額']), key=f"a_{i}")
                
                new_note = st.text_input("修改內容", row['項目內容'], key=f"n_{i}")
                
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.form_submit_button("💾 儲存修改"):
                    df.at[i, '日期'] = new_date
                    df.at[i, '類別'] = new_cat
                    df.at[i, '收支'] = new_side
                    df.at[i, '金額'] = new_amt
                    df.at[i, '項目內容'] = new_note
                    save_data(df)
                    st.success("修改成功！")
                    st.rerun()
                
                if col_btn2.form_submit_button("🗑️ 刪除此筆"):
                    df_new = df.drop(i)
                    save_data(df_new)
                    st.warning("已刪除該筆資料。")
                    st.rerun()