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
            if 1
