# Accupass → Kit

將 Accupass 參與人員名單 CSV 轉成 Kit 可匯入格式，並自動生成標準化欄位與 `tag`。

**注意**：最終輸出的 CSV 還是需要手動檢查 `姓名_Email比較` 欄位，來確認訂購人和參加人是否相同，及是否要再匯入一次 "訂購人 + 訂購人Email(primary key) + tags" 

## 特色
- 取出並保留原始 7 欄（訂購人/參加人姓名 & Email、職稱、年資、已參加次數）
- 產生 3 個標準化欄位：`最接近您工作內容的職稱_new`、`請問您的「整體」工作年資為_new`、`已參加數創小聚次數_new`
- 規則：若職稱_new = `仍在學：學生` ⇒ 年資_new = `年資：我還是學生`
- 產生活動欄位 `活動屬性`（由執行參數或互動輸入）
- 產生 `tag` 欄位（職稱_new、年資_new、參與次數_new、活動屬性 以逗號連接）
- 新增比對欄位：`姓名比較`、`Email比較`、`姓名_Email比較`
- 輸出 CSV（Excel 友善）

## 下載 Script
```bash
git clone https://github.com/entni-lin/accupass-to-kit.git
```

## 如何使用 Script
### 建議：先建立虛擬環境
```bash
python3 -m venv .venv # 適用 Python 2.x & Python 3.x
source .venv/bin/activate    # macOS / Linux
```
### 安裝所需 Module
```bash
## 直接安裝 Module
pip install pandas
## 或執行以下安裝所需 Module
pip install -r requirements.txt
```

### 執行以下 Command to proceed
Tips: 
- 把 input & output 檔名換掉（根據所在的 Working directory，更改相對檔案位置）
- 換掉活動名稱
- 最後執行以下 command
```bash
python accupass_to_kit_tags.py \
  --input "input.csv" \
  --output "output.csv" \
  --activity "講座型(202508數創小聚)"
```

