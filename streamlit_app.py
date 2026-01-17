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

# --- 有給・時間外不都合日の入力セクション ---
st.header("📅 休暇・不都合日の入力")
st.write("各スタッフの「有給」や「当直・延長不可日」を入力してください。例: 5, 12, 20")

if 'df_constraints' not in st.session_state or len(st.session_state.df_constraints) != len(staff_list):
    st.session_state.df_constraints = pd.DataFrame([
        {"名前": s, "有給日(日付)": "", "時間外不都合日(日付)": ""} for s in staff_list
    ])
edited_constraints = st.data_editor(st.session_state.df_constraints, hide_index=True)

# 入力された日付をリスト化する関数
def parse_dates(date_str):
    try:
        return [int(d.strip()) for d in date_str.split(',') if d.strip().isdigit()]
    except:
        return []

# --- 業務スキル設定 ---
st.header("🛠 業務スキル設定")
if 'df_skills' not in st.session_state or len(st.session_state.df_skills) != len(staff_list):
    st.session_state.df_skills = pd.DataFrame([{"名前": s, "1st": True, "2nd": True, "当直": True, "延長": True, "CT": True, "MRI": True} for s in staff_list])
edited_skills = st.data_editor(st.session_state.df_skills, hide_index=True)

if st.button("✨ シフトを自動生成"):
    num_days = calendar.monthrange(year, month)[1]
    dates = [datetime(year, month, d) for d in range(1, num_days + 1)]
    holidays = [11, 23] # 2026年2月
    
    duty_counts = {s: 0 for s in staff_list}
    schedule = {s: [""] * num_days for s in staff_list}
    last_duty_idx = {s: -2 for s in staff_list}
    daily_off_reserved = [0] * num_days

    # 制約データの読み込み
    staff_constraints = {}
    for _, row in edited_constraints.iterrows():
        staff_constraints[row["名前"]] = {
            "paid_off": parse_dates(row["有給日(日付)"]),
            "no_overtime": parse_dates(row["時間外不都合日(日付)"])
        }

    # 1. 優先的に「有給」をスケジュールに埋める
    for s in staff_list:
        for d in staff_constraints[s]["paid_off"]:
            if 1 <= d <= num_days:
                schedule[s][d-1] = "有給"
                daily_off_reserved[d-1] += 1

    # 2. メインの当番割り当て
    for d_idx in range(num_days):
        day_num = d_idx + 1
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
                        daily_off_reserved[d_idx] += 1
                        if is_holiday:
                            workdays = [i for i, dt in enumerate(dates) if dt.weekday() < 5 and dt.day not in holidays]
                            random.shuffle(workdays)
                            for f_idx in workdays:
                                if schedule[s][f_idx] == "" and f_idx > d_idx and daily_off_reserved[f_idx] < 3:
                                    schedule[s][f_idx] = f"◎({date.day}明)"
                                    daily_off_reserved[f_idx] += 1
                                    break
                    continue
                
                # 既に埋まっている、または有給の日はスキップ
                if schedule[s][d_idx] != "": continue
                
                # 時間外不都合日のチェック（当直、延長、日勤など時間外業務が対象）
                if day_num in staff_constraints[s]["no_overtime"] and duty in ["当直", "延長", "日勤"]:
                    continue

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
                
                # 土日祝当番の代休予約
                if is_holiday and duty in ["当直", "日勤"]:
                    workdays = [i for i, dt in enumerate(dates) if dt.weekday() < 5 and dt.day not in holidays]
                    random.shuffle(workdays)
                    for f_idx in workdays:
                        if schedule[chosen][f_idx] == "" and f_idx != d_idx and daily_off_reserved[f_idx] < 3:
                            schedule[chosen][f_idx] = f"◎({date.day})"
                            daily_off_reserved[f_idx] += 1
                            break

    # 3. 仕上げ
    off_counts = {s: 0 for s in staff_list}
    daily_off_total = [0] * num_days
    for s in staff_list:
        for d_idx in range(num_days):
            if schedule[s][d_idx] == "":
                schedule[s][d_idx] = "×" if (dates[d_idx].weekday() >= 5 or dates[d_idx].day in holidays) else "-"
            
            val = str(schedule[s][d_idx])
            if any(x in val for x in ["◎", "×", "○", "有給"]):
                daily_off_total[d_idx] += 1
                if any(x in val for x in ["◎", "×", "有給"]):
                    off_counts[s] += 1

    res_df = pd.DataFrame(schedule, index=[d.strftime("%d(%a)") for d in dates]).T
    res_df.loc["休日合計 (◎+×+○+有)"] = daily_off_total
    st.subheader("📋 シフト表")
    st.dataframe(res_df)
    
    st.subheader("📊 集計")
    st.table(pd.DataFrame({"当番": pd.Series(duty_counts), "休み": pd.Series(off_counts)}).T)
