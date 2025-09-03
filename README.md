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
- **兩個輸出 CSV 檔：**
  1. 主轉換結果（供 Kit 匯入）
  2. 兩人同行票第二人新名單（已去除現有訂閱者，並附上 `name` 與 `tags`）

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
- 所有的檔名，請根據所在的 Working directory，更改相對檔案位置
- 更改 input （來自 Accuspass）& output（要 Import 至 Kit）檔名
- 更改 subscribers 檔名（Kit confirmed subscribers 名單，請**每次跑流程時重新下載一次**）
- 更改 group-output 檔名（兩人同行票的第二人的 Email，也是要 Import 至 Kit）
- 換掉活動名稱
- 最後執行以下 command
```bash
python accupass_to_kit_tags.py \
  --input ../accupass_export_csv/2025_08AI_all.csv \
  --output kit_import.csv \
  --activity "講座型(202508數創小聚)" \
  --subscribers ./subscribers.csv \
  --group-output group_new_list.csv
```

