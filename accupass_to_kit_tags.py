# -*- coding: utf-8 -*-
"""
accupass_to_kit_tags.py
Usage:
  python accupass_to_kit_tags.py --input accupass.csv --output kit_import.csv --activity "講座型(202506數創小聚)"
"""

import argparse
import sys
from pathlib import Path
import pandas as pd

# --- 1) 欄位設定（請確保與 Accupass 匯出欄名完全一致） ---
COL_ORDER = [
    "訂購人姓名",
    "訂購人Email",
    "參加人姓名",
    "參加人Email",
    "最接近您工作內容的職稱",
    "請問您的「整體」工作年資為?",
    "已參加數創小聚次數",
]

# --- 2) 對應表：職稱 → 職稱_new ---
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

# --- 3) 對應表：年資 → 年資_new ---
SENIORITY_MAP = {
    "<=2年": "年資：0 - 2年（剛入行/ 新鮮人）",
    "2~5年": "年資：2 - 5年（穩定工作中）",
    "5~10年": "年資：5 - 10年（中階實務經驗）",
    "10年以上": "年資：10 年以上（資深或主管）",
}

# --- 4) 對應表：參與次數 → 次數_new ---
FREQ_MAP = {
    "從未參加過": "參與頻率：首次參加",
    "1次": "參與頻率：參加 2 次",      # 依你的規格
    "2次以上": "參與頻率：3 次(含) 以上",
}

# ---- 輔助：正規化 ----
def _norm_str(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def _norm_name(x):
    # 名字：去頭尾空白；不做大小寫轉換（中文名不影響，英文名保留大小寫敏感度）
    return _norm_str(x)

def _norm_email(x):
    # Email：去頭尾空白 + 小寫
    return _norm_str(x).lower()

def _equal_nonempty(a, b, norm_fn):
    """兩邊都非空才比較；其餘一律回 0"""
    na, nb = norm_fn(a), norm_fn(b)
    if not na or not nb:
        return 0
    return 1 if na == nb else 0

def main():
    parser = argparse.ArgumentParser(description="Convert Accupass CSV to Kit-ready CSV with tags.")
    parser.add_argument("--input", "-i", required=True, help="Accupass 參與人員名單 CSV 路徑")
    parser.add_argument("--output", "-o", default=None, help="輸出 CSV 路徑（預設：<input_name>_kit.csv）")
    parser.add_argument("--activity", "-a", default=None, help='活動屬性字串，例如：講座型(202506數創小聚)')
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"[錯誤] 找不到輸入檔：{in_path}", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.output) if args.output else in_path.with_name(in_path.stem + "_kit.csv")

    # 嘗試以 utf-8-sig / utf-8 / big5 讀取，最大程度相容
    last_err = None
    for enc in ("utf-8-sig", "utf-8", "cp950"):
        try:
            df = pd.read_csv(in_path, encoding=enc)
            break
        except Exception as e:
            last_err = e
            df = None
    if df is None:
        print(f"[錯誤] 無法讀取 CSV（最後錯誤：{last_err}）", file=sys.stderr)
        sys.exit(1)

    # 僅保留指定欄位（若缺少會補空欄）
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

    # 規則 4：若職稱_new == "仍在學：學生" → 年資_new = "年資：我還是學生"
    mask_student = df["最接近您工作內容的職稱_new"] == "仍在學：學生"
    df.loc[mask_student, "請問您的「整體」工作年資為_new"] = "年資：我還是學生"

    # ----- 新增 3 個比較欄位 -----
    # 1) 姓名比較：兩邊皆非空，且去空白後完全一致 → 1，否則 0
    df["姓名比較"] = [
        _equal_nonempty(o, p, _norm_name)
        for o, p in zip(df["訂購人姓名"], df["參加人姓名"])
    ]

    # 2) Email比較：兩邊皆非空，且去空白小寫後一致 → 1，否則 0
    df["Email比較"] = [
        _equal_nonempty(o, p, _norm_email)
        for o, p in zip(df["訂購人Email"], df["參加人Email"])
    ]

    # 3) 姓名_Email比較：依姓名比較/Email比較的組合給值
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

    # tag：合併四個欄位（忽略空字串），用逗號分隔
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

    # 輸出：保留原 7 欄 + 新欄
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
    # 去除重複欄名保險起見
    output_cols = list(dict.fromkeys(output_cols))

    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[完成] 已輸出：{out_path.resolve()}")

if __name__ == "__main__":
    main()
