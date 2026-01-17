import streamlit as st
import pandas as pd
import calendar
from datetime import datetime

st.set_page_config(layout="wide", page_title="シフト作成システム")
st.title("🏥 シフト自動生成・管理システム")

# --- 設定セクション ---
with st.sidebar:
    st.header("📅 基本設定")
    year = st.number_input("年", value=2026)
    month = st.number_input("月", min_value=1, max_value=12, value=2)
    
    st.header("👥 スタッフ一括登録")
    staff_input = st.text_area("名前を改行区切りで入力", height=200, value="スタッフ1\nスタッフ2\n...") # ここに52名分貼れます

if 'staff_list' not in st.session_state:
    st.session_state.staff_list = [s.strip() for s in staff_input.split('\n') if s.strip()]

# --- 業務スキル設定 ---
st.header("🛠 業務スキル設定")
default_skills = [{"名前": s, "1st": True, "2nd": True, "当直": True, "延長": True, "CT": True, "MRI": True} for s in st.session_state.staff_list]
edited_skills = st.data_editor(pd.DataFrame(default_skills), hide_index=True)

# --- 生成ロジック ---
if st.button("✨ シフトを自動生成"):
    num_days = calendar.monthrange(year, month)[1]
    dates = [datetime(year, month, d) for d in range(1, num_days + 1)]
    duty_counts = {s: 0 for s in st.session_state.staff_list}
    schedule = {s: [""] * num_days for s in st.session_state.staff_list}
    last_duty = {s: -2 for s in st.session_state.staff_list}

    for d_idx in range(num_days):
        date = dates[d_idx]
        is_holiday = date.weekday() >= 5
        duties = ["1st", "2nd", "当直", "日勤"] if is_holiday else ["1st", "2nd", "当直", "延長", "CT", "MRI"]

        for duty in duties:
            candidates = []
            for s in st.session_state.staff_list:
                if d_idx > 0 and schedule[s][d_idx-1] == "当直":
                    schedule[s][d_idx] = "明"
                    continue
                if schedule[s][d_idx] != "": continue
                
                skill_col = "当直" if duty == "日勤" else duty
                if edited_skills.loc[edited_skills["名前"] == s, skill_col].values[0] and last_duty[s] < d_idx - 1:
                    candidates.append(s)
            
            candidates.sort(key=lambda x: duty_counts[x])
            if candidates:
                chosen = candidates[0]
                schedule[chosen][d_idx] = duty
                duty_counts[chosen] += 1
                last_duty[chosen] = d_idx
                
                # 代休(◎)付与ロジック
                if is_holiday and duty in ["当直", "日勤"]:
                    for f_idx in range(d_idx + 1, num_days):
                        if dates[f_idx].weekday() < 5 and schedule[chosen][f_idx] == "":
                            schedule[chosen][f_idx] = "◎"
                            break

    # --- 仕上げ：空欄を「×」または「-」に埋める ---
    for s in st.session_state.staff_list:
        for d_idx in range(num_days):
            if schedule[s][d_idx] == "":
                if dates[d_idx].weekday() >= 5:
                    schedule[s][d_idx] = "×" # 休日は×
                else:
                    schedule[s][d_idx] = "-" # 平日は通常勤務

    res_df = pd.DataFrame(schedule, index=[d.strftime("%d(%a)") for d in dates]).T
    st.dataframe(res_df)
    st.bar_chart(pd.Series(duty_counts))