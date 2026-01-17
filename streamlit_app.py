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
    # 初期値としてサンプルを入力。ここに実際の52名分を貼り付けてください。
    default_staff = "\n".join([f"スタッフ{i}" for i in range(1, 53)])
    staff_input = st.text_area("名前を改行区切りで入力", height=200, value=default_staff)

st.session_state.staff_list = [s.strip() for s in staff_input.split('\n') if s.strip()]

# --- 業務スキル設定 ---
st.header("🛠 業務スキル設定")
# 初回のみスキル表を作成
if 'df_skills' not in st.session_state:
    default_skills = [{"名前": s, "1st": True, "2nd": True, "当直": True, "延長": True, "CT": True, "MRI": True} for s in st.session_state.staff_list]
    st.session_state.df_skills = pd.DataFrame(default_skills)

edited_skills = st.data_editor(st.session_state.df_skills, hide_index=True)

# --- 生成ロジック ---
if st.button("✨ シフトを自動生成"):
    num_days = calendar.monthrange(year, month)[1]
    dates = [datetime(year, month, d) for d in range(1, num_days + 1)]
    
    # データ初期化
    duty_counts = {s: 0 for s in st.session_state.staff_list}
    schedule = {s: [""] * num_days for s in st.session_state.staff_list}
    last_duty_idx = {s: -2 for s in st.session_state.staff_list}

    # 1. メインの当番割り当て
    for d_idx in range(num_days):
        date = dates[d_idx]
        is_holiday = date.weekday() >= 5
        # 祝日判定（簡易的に土日以外も考慮する場合はリスト化が必要）
        daily_duties = ["1st", "2nd", "当直", "日勤"] if is_holiday else ["1st", "2nd", "当直", "延長", "CT", "MRI"]

        for duty in daily_duties:
            candidates = []
            for s in st.session_state.staff_list:
                # 当直明けは最優先で「明」を入れる
                if d_idx > 0 and schedule[s][d_idx-1] == "当直":
                    schedule[s][d_idx] = "明"
                    continue
                
                # 既に何かが埋まっている場合はスキップ
                if schedule[s][d_idx] != "": continue
                
                # スキルと連勤チェック
                skill_col = "当直" if duty == "日勤" else duty
                if edited_skills.loc[edited_skills["名前"] == s, skill_col].values[0]:
                    if last_duty_idx[s] < d_idx - 1: # 2日連続禁止
                        candidates.append(s)
            
            # 平等化：回数が少ない順にソート
            candidates.sort(key=lambda x: duty_counts[x])
            
            if candidates:
                chosen = candidates[0]
                schedule[chosen][d_idx] = duty
                duty_counts[chosen] += 1
                last_duty_idx[chosen] = d_idx
                
                # 【重要】代休(◎)付与ロジックの強化
                # 土日祝に当直・日勤をした場合、翌日以降の「平日」に空きがあれば即座に◎を予約する
                if is_holiday and duty in ["当直", "日勤"]:
                    for f_idx in range(d_idx + 1, num_days):
                        # 翌日以降の「平日」かつ「まだ何も入っていない」日を探す
                        if dates[f_idx].weekday() < 5 and schedule[chosen][f_idx] == "":
                            schedule[chosen][f_idx] = "◎"
                            break

    # 2. 最終仕上げ：空欄を「×」または「-」で埋める
    for s in st.session_state.staff_list:
        for d_idx in range(num_days):
            if schedule[s][d_idx] == "":
                if dates[d_idx].weekday() >= 5:
                    schedule[s][d_idx] = "×" # 何もない土日は休み
                else:
                    schedule[s][d_idx] = "-" # 何もない平日は通常

    # 結果の表示
    res_df = pd.DataFrame(schedule, index=[d.strftime("%d(%a)") for d in dates]).T
    st.subheader("📋 生成されたシフト表")
    st.dataframe(res_df.style.highlight_contains("◎", color="#90ee90").highlight_contains("当直", color="#ffcccb"))
    
    st.subheader("📊 当番回数の集計")
    st.bar_chart(pd.Series(duty_counts))
