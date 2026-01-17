import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
import random

st.set_page_config(layout="wide", page_title="シフト作成システム")
st.title("🏥 シフト自動生成・管理システム")

# --- 設定セクション ---
with st.sidebar:
    st.header("📅 基本設定")
    year = st.number_input("年", value=2026)
    month = st.number_input("月", min_value=1, max_value=12, value=2)
    
    st.header("👥 スタッフ一括登録")
    default_staff = "\n".join([f"スタッフ{i}" for i in range(1, 53)])
    staff_input = st.text_area("名前を改行区切りで入力", height=200, value=default_staff)

staff_list = [s.strip() for s in staff_input.split('\n') if s.strip()]

# --- 業務スキル設定 ---
if 'df_skills' not in st.session_state or len(st.session_state.df_skills) != len(staff_list):
    default_skills = [{"名前": s, "1st": True, "2nd": True, "当直": True, "延長": True, "CT": True, "MRI": True} for s in staff_list]
    st.session_state.df_skills = pd.DataFrame(default_skills)

edited_skills = st.data_editor(st.session_state.df_skills, hide_index=True)

# --- 生成ロジック ---
if st.button("✨ シフトを自動生成"):
    num_days = calendar.monthrange(year, month)[1]
    dates = [datetime(year, month, d) for d in range(1, num_days + 1)]
    holidays = [11, 23] # 2026年2月の祝日
    
    duty_counts = {s: 0 for s in staff_list}
    schedule = {s: [""] * num_days for s in staff_list}
    last_duty_idx = {s: -2 for s in staff_list}

    for d_idx in range(num_days):
        date = dates[d_idx]
        is_holiday = date.weekday() >= 5 or (date.day in holidays)
        daily_duties = ["1st", "2nd", "当直", "日勤"] if is_holiday else ["1st", "2nd", "当直", "延長", "CT", "MRI"]

        for duty in daily_duties:
            candidates = []
            for s in staff_list:
                if d_idx > 0 and schedule[s][d_idx-1] == "当直":
                    schedule[s][d_idx] = "○"
                    continue
                if schedule[s][d_idx] != "": continue
                
                skill_col = "当直" if duty == "日勤" else duty
                if edited_skills.loc[edited_skills["名前"] == s, skill_col].values[0]:
                    if last_duty_idx[s] < d_idx - 1:
                        candidates.append(s)
            
            random.shuffle(candidates)
            candidates.sort(key=lambda x: duty_counts[x])
            
            if candidates:
                chosen = candidates[0]
                schedule[chosen][d_idx] = duty
                duty_counts[chosen] += 1
                last_duty_idx[chosen] = d_idx
                
                if is_holiday and duty in ["当直", "日勤"]:
                    for f_idx in range(num_days):
                        f_date = dates[f_idx]
                        if f_date.weekday() < 5 and f_date.day not in holidays:
                            if schedule[chosen][f_idx] == "" and f_idx != d_idx:
                                schedule[chosen][f_idx] = f"◎({date.day})"
                                break

    # 休み（×・-）の埋め合わせとカウント
    off_counts = {s: 0 for s in staff_list}
    for s in staff_list:
        for d_idx in range(num_days):
            val = schedule[s][d_idx]
            if val == "":
                date = dates[d_idx]
                is_holiday = date.weekday() >= 5 or (date.day in holidays)
                schedule[s][d_idx] = "×" if is_holiday else "-"
            
            # ◎（代休）または ×（休日）をカウント
            if "◎" in schedule[s][d_idx] or schedule[s][d_idx] == "×":
                off_counts[s] += 1

    res_df = pd.DataFrame(schedule, index=[d.strftime("%d(%a)") for d in dates]).T
    st.subheader("📋 シフト表")
    st.dataframe(res_df)

    # --- カウント結果の表示 ---
    st.subheader("📊 休み数・当番数の集計")
    col1, col2 = st.columns(2)
    with col1:
        st.write("各スタッフの休み合計（◎ + ×）")
        st.bar_chart(pd.Series(off_counts))
    with col2:
        st.write("当番回数（平等性の確認）")
        st.bar_chart(pd.Series(duty_counts))
    
    # 詳細テーブル
    summary_df = pd.DataFrame({
        "当番回数": pd.Series(duty_counts),
        "休み合計(◎+×)": pd.Series(off_counts)
    })
    st.table(summary_df)
