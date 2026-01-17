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
    staff_input = st.text_area("名前を改行区切りで入力", height=200, value="\n".join([f"スタッフ{i}" for i in range(1, 53)]))

staff_list = [s.strip() for s in staff_input.split('\n') if s.strip()]

# --- 業務スキル設定 ---
if 'df_skills' not in st.session_state or len(st.session_state.df_skills) != len(staff_list):
    st.session_state.df_skills = pd.DataFrame([{"名前": s, "1st": True, "2nd": True, "当直": True, "延長": True, "CT": True, "MRI": True} for s in staff_list])
edited_skills = st.data_editor(st.session_state.df_skills, hide_index=True)

if st.button("✨ シフトを自動生成"):
    num_days = calendar.monthrange(year, month)[1]
    dates = [datetime(year, month, d) for d in range(1, num_days + 1)]
    holidays = [11, 23] # 2026年2月
    
    duty_counts = {s: 0 for s in staff_list}
    # 平日の「休み（- または ◎）」をカウントするための辞書
    weekday_off_counts = {s: 0 for s in staff_list}
    schedule = {s: [""] * num_days for s in staff_list}
    last_duty_idx = {s: -2 for s in staff_list}

    # 1. メインの当番割り当て
    for d_idx in range(num_days):
        date = dates[d_idx]
        is_holiday = date.weekday() >= 5 or (date.day in holidays)
        daily_duties = ["1st", "2nd", "当直", "日勤"] if is_holiday else ["1st", "2nd", "当直", "延長", "CT", "MRI"]

        for duty in daily_duties:
            candidates = []
            for s in staff_list:
                # 当直明け判定
                if d_idx > 0 and schedule[s][d_idx-1] == "当直":
                    if schedule[s][d_idx] == "":
                        schedule[s][d_idx] = "○"
                        if is_holiday:
                            # 祝日明けの代休補填
                            workdays = [i for i, d in enumerate(dates) if d.weekday() < 5 and d.day not in holidays]
                            random.shuffle(workdays)
                            for f_idx in workdays:
                                if schedule[s][f_idx] == "" and f_idx > d_idx:
                                    schedule[s][f_idx] = f"◎({date.day}明)"
                                    break
                    continue
                
                if schedule[s][d_idx] != "": continue
                
                skill_col = "当直" if duty == "日勤" else duty
                if edited_skills.loc[edited_skills["名前"] == s, skill_col].values[0]:
                    if last_duty_idx[s] < d_idx - 1:
                        candidates.append(s)
            
            # 平等化の鍵：当番回数が少なく、かつ「平日の休み」が少ない人を優先的に当番から外す（＝休みを増やす）
            # ここではシンプルに当番回数の少なさを優先
            random.shuffle(candidates)
            candidates.sort(key=lambda x: duty_counts[x])
            
            if candidates:
                chosen = candidates[0]
                schedule[chosen][d_idx] = duty
                duty_counts[chosen] += 1
                last_duty_idx[chosen] = d_idx
                
                if is_holiday and duty in ["当直", "日勤"]:
                    # 土日祝当番の代休予約
                    workdays = [i for i, d in enumerate(dates) if d.weekday() < 5 and d.day not in holidays]
                    random.shuffle(workdays)
                    for f_idx in workdays:
                        if schedule[chosen][f_idx] == "" and f_idx != d_idx:
                            schedule[chosen][f_idx] = f"◎({date.day})"
                            break

    # 2. 仕上げ（空欄を × または - で埋める）と平日の休みカウント
    off_counts = {s: 0 for s in staff_list}
    daily_off_counts = [0] * num_days

    for s in staff_list:
        for d_idx in range(num_days):
            date = dates[d_idx]
            is_holiday = date.weekday() >= 5 or (date.day in holidays)
            
            if schedule[s][d_idx] == "":
                schedule[s][d_idx] = "×" if is_holiday else "-"
            
            # 休み合計（◎、×、- すべて）のカウント
            if "◎" in schedule[s][d_idx] or schedule[s][d_idx] == "×" or schedule[s][d_idx] == "-":
                off_counts[s] += 1
                daily_off_counts[d_idx] += 1
                # 平日の休み（代休含む）をカウント
                if not is_holiday:
                    weekday_off_counts[s] += 1

    res_df = pd.DataFrame(schedule, index=[d.strftime("%d(%a)") for d in dates]).T
    res_df.loc["休日合計 (◎+×+-)"] = daily_off_counts

    st.subheader("📋 シフト表")
    st.dataframe(res_df)
    
    st.subheader("📊 集計 (平日の休み数・当番数)")
    summary_df = pd.DataFrame({
        "当番回数": pd.Series(duty_counts),
        "平日の休み数(- or ◎)": pd.Series(weekday_off_counts),
        "総休み数(◎+×+-)": pd.Series(off_counts)
    })
    st.table(summary_df.T)
