import streamlit as st
import pandas as pd
import calendar
from datetime import datetime

st.set_page_config(layout="wide", page_title="シフト作成システム")

st.title("🏥 シフト自動生成・管理システム")

# --- サイドバー：設定 ---
with st.sidebar:
    st.header("📅 基本設定")
    year = st.number_input("年", value=2026)
    month = st.number_input("月", min_value=1, max_value=12, value=2)
    
    st.header("👥 スタッフ一括登録")
    staff_input = st.text_area("名前を改行区切りで入力（52名分コピペ可）", height=200)
    if staff_input:
        st.session_state.staff_list = [s.strip() for s in staff_input.split('\n') if s.strip()]
    else:
        st.session_state.staff_list = [f"スタッフ{i}" for i in range(1, 53)]

st.header("🛠 業務スキル・制約の設定")
st.write("各スタッフが担当可能な業務にチェックを入れてください。")

# スキル管理用データフレーム
default_skills = []
for s in st.session_state.staff_list:
    is_A = (s == "A")
    is_B = (s == "B")
    default_skills.append({
        "名前": s,
        "1st": not is_A and not is_B,
        "2nd": not is_A, # BさんはこれだけOK
        "当直": not is_A and not is_B,
        "延長": not is_A and not is_B,
        "CT": not is_A and not is_B,
        "MRI": not is_A and not is_B
    })

edited_skills = st.data_editor(pd.DataFrame(default_skills), key="skill_editor", hide_index=True)

st.header("🚫 希望休・不都合日の入力")
unavailability_input = st.text_area("例：スタッフ名:1,5,12 （コロンの後に日付をカンマ区切り。複数人は改行）")

# --- 生成ロジック ---
if st.button("✨ シフトを自動生成（回数平等化）"):
    num_days = calendar.monthrange(year, month)[1]
    dates = [datetime(year, month, d) for d in range(1, num_days + 1)]
    
    # 不都合日のパース
    unavail_dict = {}
    for line in unavailability_input.split('\n'):
        if ':' in line:
            name, days = line.split(':')
            unavail_dict[name.strip()] = [int(d.strip()) for d in days.split(',')]

    # カウンターと結果保持
    duty_counts = {s: 0 for s in st.session_state.staff_list}
    schedule = {s: ["-"] * num_days for s in st.session_state.staff_list}
    last_duty_date = {s: -2 for s in st.session_state.staff_list}

    for d_idx in range(num_days):
        current_date = dates[d_idx]
        day_num = d_idx + 1
        is_holiday = current_date.weekday() >= 5 # 簡易土日判定

        # 当日の業務リスト
        if is_holiday:
            daily_duties = ["1st", "2nd", "当直", "日勤"]
        else:
            daily_duties = ["1st", "2nd", "当直", "延長", "CT", "MRI"]

        for duty in daily_duties:
            candidates = []
            for s in st.session_state.staff_list:
                # 1. 当直明けチェック
                if d_idx > 0 and schedule[s][d_idx-1] == "当直":
                    schedule[s][d_idx] = "明"
                    continue
                
                # 2. 基本スキルチェック
                skill_col = "当直" if duty == "日勤" else duty
                can_do = edited_skills.loc[edited_skills["名前"] == s, skill_col].values[0]
                
                # 3. 不都合日・連勤・重複チェック
                not_busy = day_num not in unavail_dict.get(s, [])
                not_continuous = last_duty_date[s] < d_idx - 1
                not_assigned_today = schedule[s][d_idx] == "-"
                
                if can_do and not_busy and not_continuous and not_assigned_today:
                    candidates.append(s)
            
            # 平等化：当番回数が少ない順にソート
            candidates.sort(key=lambda x: duty_counts[x])
            
            if candidates:
                chosen = candidates[0]
                schedule[chosen][d_idx] = duty
                duty_counts[chosen] += 1
                last_duty_date[chosen] = d_idx
                
                # 代休(◎)付与（土日祝の当直・日勤）
                if is_holiday and duty in ["当直", "日勤"]:
                    for future_idx in range(d_idx + 1, num_days):
                        if dates[future_idx].weekday() < 5 and schedule[chosen][future_idx] == "-":
                            schedule[chosen][future_idx] = "◎"
                            break

    # 結果表示
    res_df = pd.DataFrame(schedule, index=[d.strftime("%d(%a)") for d in dates]).T
    st.subheader("📋 生成されたシフト表")
    st.dataframe(res_df)
    
    st.subheader("📊 当番回数の集計（平等性の確認）")
    st.bar_chart(pd.Series(duty_counts))

    csv = res_df.to_csv().encode('utf_8_sig')
    st.download_button("Excel用CSVをダウンロード", csv, f"shift_{year}_{month}.csv", "text/csv")