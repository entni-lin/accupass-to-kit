# -*- coding: utf-8 -*-
"""
accupass_to_kit_tags.py

功能：
1) 主要轉換：擷取 Accupass 指定欄位、標準化成 *_new 欄位、產生 tag、姓名/Email 比對，輸出主 CSV
2) 兩人同行票：擷取「第二人 email」，過濾現有訂閱者名單後，補上 name/tags，輸出第二個 CSV

用法範例：
  python accupass_to_kit_tags.py \
    --input ../accupass_export_csv/2025_08AI_all.csv \
    --output kit_import.csv \
    --activity "講座型(202508數創小聚)" \
    --subscribers ./subscribers.csv \
    --group-output group_new_list.csv
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

# --- 0) 共用常數 ---
COL_ORDER = [
    "訂購人姓名",
    "訂購人Email",
    "參加人姓名",
    "參加人Email",
    "最接近您工作內容的職稱",
    "請問您的「整體」工作年資為?",
    "已參加數創小聚次數",
]
GROUP_COL = "若為購買兩人同行票，請問第二人的email為？"  # 原始欄名（含全形問號）

# --- 1) 對應表：職稱 → 職稱_new ---
TITLE_MAP = {
    "企業高階主管 Founder/ Executives": "高層/ 策略決策者：創辦人/ 高階主管",
    "其他團隊主管 Other Team Lead": "管理/策略職：其他團隊主管",
    "其他 Others": "其他職能：其他",
    "專案經理 Project Manager": "管理/策略職：專案經理 Project Manager",
    "產品經理 Product Manager": "管理/策略職：產品經理 Product Manager",
    "軟體工程師 Software Engineer": "技術職：軟體工程師 Software Engineer",
    "資料工程師 Data Engineer": "技術職：資料工程師 Data Engineer",
    "資料科學家 Data Scientist": "技術職：資料科學家 Data Scientist",
    "數據分析師 Data Analyst": "技術職：資料分析師 Data Analyst",
    "數據/AI團隊主管 Data Team Lead": "管理/策略職：數據/ AI團隊主管",
    "學生 Student": "仍在學：學生",
}

# --- 2) 對應表：年資 → 年資_new ---
SENIORITY_MAP = {
    "<=2年": "年資：0 - 2年（剛入行/ 新鮮人）",
    "2~5年": "年資：2 - 5年（穩定工作中）",
    "5~10年": "年資：5 - 10年（中階實務經驗）",
    "10年以上": "年資：10 年以上（資深或主管）",
}

# --- 3) 對應表：參與次數 → 次數_new ---
FREQ_MAP = {
    "從未參加過": "參與頻率：首次參加",
    "1次": "參與頻率：參加 2 次",      # 依你的規格
    "2次以上": "參與頻率：3 次(含) 以上",
}

# ---- 4) 輔助：正規化 ----
def _norm_str(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def _norm_name(x):
    return _norm_str(x)

def _norm_email(x):
    # Email：去頭尾空白 + 小寫（沿用你的原規則）
    return _norm_str(x).lower()

def _equal_nonempty(a, b, norm_fn):
    """兩邊都非空才比較；否則回 0"""
    na, nb = norm_fn(a), norm_fn(b)
    if not na or not nb:
        return 0
    return 1 if na == nb else 0

def read_csv_fallback(path: Path) -> pd.DataFrame:
    last_err = None
    for enc in ("utf-8-sig", "utf-8", "cp950"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception as e:
            last_err = e
    raise RuntimeError(f"無法讀取 CSV：{path}（最後錯誤：{last_err}）")

def find_email_column(columns) -> str | None:
    # 先找完全等於 "email"（不分大小寫）
    for c in columns:
        if str(c).strip().lower() == "email":
            return c
    # 再寬鬆找含有 "email" 的欄名
    for c in columns:
        if "email" in str(c).strip().lower():
            return c
    return None

def main():
    parser = argparse.ArgumentParser(
        description="Convert Accupass CSV to Kit-ready CSV with tags, and build group-ticket second-person list."
    )
    parser.add_argument("--input", "-i", required=True, help="Accupass 參與人員名單 CSV 路徑")
    parser.add_argument("--output", "-o", default=None, help="第一個輸出：主轉換結果 CSV（預設：<input>_kit.csv）")
    parser.add_argument("--activity", "-a", default=None, help='活動屬性字串，例如：講座型(202506數創小聚)')
    parser.add_argument("--subscribers", "-s", default=None, help="現有訂閱者名單 CSV（需含 email 欄位）")
    parser.add_argument("--group-output", "-g", default=None, help="第二個輸出：兩人同行第二人、去重後的 Email 名單 CSV（預設：<input>_group_new_list.csv）")
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"[錯誤] 找不到輸入檔：{in_path}", file=sys.stderr)
        sys.exit(1)

    # 預設輸出路徑
    out_path = Path(args.output) if args.output else in_path.with_name(in_path.stem + "_kit.csv")
    group_out_path = Path(args.group_output) if args.group_output else in_path.with_name(in_path.stem + "_group_new_list.csv")

    # ---------- 只讀一次原始 CSV ----------
    try:
        df_full = read_csv_fallback(in_path)
    except Exception as e:
        print(f"[錯誤] {e}", file=sys.stderr)
        sys.exit(1)

    # ---------- 建立主流程 df（基於 df_full） ----------
    df = df_full.copy()
    for col in COL_ORDER:
        if col not in df.columns:
            df[col] = ""
    df = df[COL_ORDER].copy()

    # 產生 *_new 欄位
    title_src = "最接近您工作內容的職稱"
    df["最接近您工作內容的職稱_new"] = df[title_src].apply(lambda v: TITLE_MAP.get(_norm_str(v), _norm_str(v)))

    seniority_src = "請問您的「整體」工作年資為?"
    df["請問您的「整體」工作年資為_new"] = df[seniority_src].apply(lambda v: SENIORITY_MAP.get(_norm_str(v), _norm_str(v)))

    freq_src = "已參加數創小聚次數"
    df["已參加數創小聚次數_new"] = df[freq_src].apply(lambda v: FREQ_MAP.get(_norm_str(v), _norm_str(v)))

    # 規則：若職稱_new == "仍在學：學生" → 年資_new = "年資：我還是學生"
    mask_student = df["最接近您工作內容的職稱_new"] == "仍在學：學生"
    df.loc[mask_student, "請問您的「整體」工作年資為_new"] = "年資：我還是學生"

    # 比對欄位
    df["姓名比較"] = [_equal_nonempty(o, p, _norm_name) for o, p in zip(df["訂購人姓名"], df["參加人姓名"])]
    df["Email比較"] = [_equal_nonempty(o, p, _norm_email) for o, p in zip(df["訂購人Email"], df["參加人Email"])]

    def combine_flag(n_eq, e_eq):
        if n_eq == 1 and e_eq == 1:
            return "同一個人"
        if n_eq == 1 and e_eq == 0:
            return "同一個人不同Email"
        if n_eq == 0 and e_eq == 1:
            return "同一個人"
        return "可能不同人"

    df["姓名_Email比較"] = [combine_flag(n, e) for n, e in zip(df["姓名比較"], df["Email比較"])]

    # 活動屬性：參數優先，沒有就互動式輸入
    activity = args.activity
    if not activity:
        try:
            activity = input("請輸入活動屬性（例如：講座型(202506數創小聚)）：").strip()
        except EOFError:
            activity = ""
    df["活動屬性"] = activity

    # tag 欄
    def build_tag(row):
        parts = [
            _norm_str(row.get("最接近您工作內容的職稱_new", "")),
            _norm_str(row.get("請問您的「整體」工作年資為_new", "")),
            _norm_str(row.get("已參加數創小聚次數_new", "")),
            _norm_str(row.get("活動屬性", "")),
        ]
        parts = [p for p in parts if p]
        return ",".join(parts)

    df["tag"] = df.apply(build_tag, axis=1)

    # --- 第一個輸出（主轉換檔） ---
    output_cols = COL_ORDER + [
        "最接近您工作內容的職稱_new",
        "請問您的「整體」工作年資為_new",
        "已參加數創小聚次數_new",
        "活動屬性",
        "tag",
        "姓名比較",
        "Email比較",
        "姓名_Email比較",
    ]
    output_cols = list(dict.fromkeys(output_cols))
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[完成] 已輸出主轉換檔：{out_path.resolve()}")

    # ---------- 兩人同行票第二人 email：基於 df_full ----------
    if GROUP_COL in df_full.columns:
        group_df = df_full[[GROUP_COL]].copy()
        group_df.rename(columns={GROUP_COL: "group_ticket_email"}, inplace=True)

        # 清理與過濾：非空才保留
        group_df["group_ticket_email"] = group_df["group_ticket_email"].apply(_norm_email)
        group_df = group_df[group_df["group_ticket_email"] != ""].reset_index(drop=True)
        print(f"[資訊] 兩人同行第二人原始 email 筆數：{len(group_df)}")
    else:
        group_df = pd.DataFrame(columns=["group_ticket_email"])
        print(f"[警告] 原始檔缺少欄位「{GROUP_COL}」，將輸出空的兩人同行名單。")

    # --- 去掉已存在Email：比對現有訂閱者名單（可選） ---
    if args.subscribers and not group_df.empty:
        sub_path = Path(args.subscribers)
        if not sub_path.exists():
            print(f"[警告] 找不到 subscribers 檔案：{sub_path}，跳過去掉已存在Email步驟。", file=sys.stderr)
        else:
            try:
                sub_df = read_csv_fallback(sub_path)
                email_col = find_email_column(sub_df.columns)
                if not email_col:
                    print(f"[警告] subscribers 檔未找到 email 欄位，跳過去掉已存在Email步驟。", file=sys.stderr)
                else:
                    sub_emails = sub_df[email_col].map(_norm_email)
                    sub_set = set(e for e in sub_emails if e)
                    before = len(group_df)
                    group_df = group_df[~group_df["group_ticket_email"].isin(sub_set)].reset_index(drop=True)
                    removed = before - len(group_df)
                    print(f"[資訊] 已依訂閱者名單去重：移除 {removed} 筆已存在的 email。")
            except Exception as e:
                print(f"[警告] 讀取/處理 subscribers 檔失敗，跳過去掉已存在Email步驟：{e}", file=sys.stderr)

    # 補上固定欄位：name / tags
    if not group_df.empty:
        group_df["name"] = "數創夥伴"
        group_df["tags"] = activity  # 使用同一個 activity 字串
    else:
        group_df = pd.DataFrame(columns=["group_ticket_email", "name", "tags"])

    # --- 第二個輸出（兩人同行第二人新名單） ---
    group_df.to_csv(group_out_path, index=False, encoding="utf-8-sig")
    print(f"[完成] 已輸出二人同行第二人新名單：{group_out_path.resolve()}")

if __name__ == "__main__":
    main()
