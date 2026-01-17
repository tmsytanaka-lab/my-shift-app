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
    # 初期値。ここを52名分に書き換えてください。
    default_staff = "\n".join([f"スタッフ{i}" for i in range(1, 53)])
    staff_input = st.text_area("名前を改行区切りで入力", height=200, value=default_staff)

staff_list = [s.strip() for s in staff_input.split('\n') if s.strip()]

# --- 業務スキル設定 ---
st.header("🛠 業務スキル設定")
if 'df_skills' not in st.session_state or len(st.session_state.df_skills) != len(staff_list):
    default_skills = [{"名前": s, "1st": True, "2nd": True, "当直": True, "延長": True, "CT": True, "MRI": True} for s in staff_list]
    st.session_state.df_skills = pd.DataFrame(default_skills)

edited_skills = st.data_editor(st.session_state.df_skills, hide_index=True)

# --- 生成ロジック ---
if st.button("✨ シフトを自動生成"):
    num_days = calendar.monthrange(year, month)[1]
    dates = [datetime(year, month, d) for d in range(1, num_days + 1)]
    
    duty_counts = {s: 0 for s in staff_list}
    schedule = {s: [""] * num_days for s in staff_list}
    last_duty_idx = {s: -2 for s in staff_list}

    for d_idx in range(num_days):
        date = dates[d_idx]
        is_holiday = date.weekday() >= 5
        daily_duties = ["1st", "2nd", "当直", "日勤"] if is_holiday else ["1st", "2nd", "当直", "延長", "CT", "MRI"]

        for duty in daily_duties:
            candidates = []
            for s in staff_list:
                # 当直明け判定
                if d_idx > 0 and schedule[s][d_idx-1] == "当直":
                    schedule[s][d_idx] = "明"
                    continue
                
                if schedule[s][d_idx] != "": continue
                
                skill_col = "当直" if duty == "日勤" else duty
                if edited_skills.loc[edited_skills["名前"] == s, skill_col].values[0]:
                    if last_duty_idx[s] < d_idx - 1:
                        candidates.append(s)
            
            candidates.sort(key=lambda x: duty_counts[x])
            
            if candidates:
                chosen = candidates[0]
                schedule[chosen][d_idx] = duty
                duty_counts[chosen] += 1
                last_duty_idx[chosen] = d_idx
                
                # 【代休予約】土日祝の当直・日勤
                if is_holiday and duty in ["当直", "日勤"]:
                    for f_idx in range(d_idx + 1, num_days):
                        # 平日かつ空欄の日を探して予約
                        if dates[f_idx].weekday() < 5 and schedule[chosen][f_idx] == "":
                            schedule[chosen][f_idx] = "◎"
                            break

    # 空欄を「×」または「-」で埋める
    for s in staff_list:
        for d_idx in range(num_days):
            if schedule[s][d_idx] == "":
                schedule[s][d_idx] = "×" if dates[d_idx].weekday() >= 5 else "-"

    res_df = pd.DataFrame(schedule, index=[d.strftime("%d(%a)") for d in dates]).T
    st.subheader("📋 生成されたシフト表")
    # エラー回避のため色付けなしのシンプルな表示に変更
    st.dataframe(res_df)
    
    st.subheader("📊 当番回数の集計")
    st.bar_chart(pd.Series(duty_counts))
