# 📚 完整 PDF 題庫測驗系統 - 使用指南

## 🚀 5分鐘快速開始

### 本地運行

```bash
# 1. 安裝依賴
pip install -r requirements.txt

# 2. 運行系統
streamlit run app_complete.py

# 3. 自動打開 http://localhost:8501
```

### 部署到 Streamlit Cloud

1. **推送代碼到 GitHub**
```bash
git init
git add .
git commit -m "Complete Quiz System"
git remote add origin https://github.com/yourusername/pdf-quiz-system.git
git push -u origin main
```

2. **去 Streamlit Cloud 部署**
   - 網址：https://streamlit.io/cloud
   - 點「New app」
   - 連接 GitHub 倉庫
   - 選擇 `app_complete.py`
   - 點「Deploy」

3. **完成！** 獲得公開 URL

---

## 📁 系統結構

```
pdf-quiz-system/
├── app_complete.py          # 主程式（Streamlit）
├── database.py              # 資料庫操作
├── requirements.txt         # 依賴
├── quiz_database.db         # SQLite 資料庫（自動建立）
└── README.md               # 項目說明
```

---

## 🎯 功能介紹

### 1️⃣ 首頁
- 顯示統計信息（題庫數、題目數、測驗次數）
- 快捷導航到各功能

### 2️⃣ 題庫管理
**上傳 PDF：**
- 選擇科目
- 輸入分類名稱
- 上傳 PDF 檔案
- 自動解析題目
- 批量匯入題庫

**查看分類：**
- 列表顯示所有分類
- 顯示每個分類的題數
- 支援刪除分類

**統計信息：**
- 分類數、題目數、平均分數

### 3️⃣ 開始測驗
- 選擇科目（基於已建立的分類）
- 選擇題數（10/20/30 或全部）
- 點擊「開始測驗」

### 4️⃣ 測驗進行中
- 顯示進度（當前題/總題）
- 計時器（實時顯示）
- 題目內容和選項
- 上一題/下一題導航
- 提交測驗按鈕

### 5️⃣ 測驗結果
- 成績展示（分數/100）
- 統計信息（正確/錯誤/耗時）
- 返回首頁或重新測驗選項

### 6️⃣ 錯題本
- 顯示所有做錯的題目
- 顯示正確答案
- 顯示解析說明

### 7️⃣ 成績統計
- 總測驗次數
- 平均分數
- 按科目統計成績
- 最近 20 次考試歷史

---

## 💾 資料庫結構

### categories（分類表）
```
id          - 分類 ID
name        - 分類名稱（例如：CH2 圖形）
subject     - 科目（數學/國文/英文/...）
created_at  - 建立時間
```

### questions（題目表）
```
id          - 題目 ID
category_id - 所屬分類
q_id        - 題號
type        - 題型（single/fill/tf）
text        - 題目內容
options     - 選項（JSON）
correct     - 正確答案索引
analysis    - 解析說明
created_at  - 建立時間
```

### exam_results（成績表）
```
id                  - 成績記錄 ID
category_id         - 分類 ID
total_questions     - 總題數
correct_count       - 正確題數
score               - 百分比分數
duration_seconds    - 耗時（秒）
created_at          - 測驗時間
```

### wrong_questions（錯題表）
```
id              - 錯題記錄 ID
question_id     - 題目 ID
exam_result_id  - 成績記錄 ID
user_answer     - 使用者答案
created_at      - 記錄時間
```

---

## 🔧 支援的 PDF 格式

系統自動識別以下格式：

```
（ ） 1. 題目內容？
     (A) 選項A  (B) 選項B  (C) 選項C  (D) 選項D

( ) 2. 另一個題目
   (A) 選項A (B) 選項B (C) 選項C (D) 選項D
```

---

## 📊 JSON 輸出格式

系統內部使用以下題目格式：

```json
{
  "id": 1,
  "type": "single",
  "text": "下列哪一點不含通過直線 y=-2x+5？",
  "options": [
    "(A) (1,3)",
    "(B) (0,5)",
    "(C) (3,-1)",
    "(D) (3,1)"
  ],
  "correct": 3,
  "analysis": "代入驗證各點...正確答案是 (D)"
}
```

---

## 🎓 使用場景

### 場景 1：教師使用
1. 上傳各章節考卷 PDF
2. 建立對應分類（例如：CH1、CH2）
3. 學生自主練習
4. 教師查看成績統計

### 場景 2：學生自主學習
1. 上傳自己的複習筆記 PDF
2. 系統自動提取題目
3. 定期測驗鞏固知識
4. 追蹤錯題並複習

### 場景 3：模擬考試
1. 上傳整份模擬考卷
2. 學生進行計時測驗
3. 自動判卷並反饋
4. 分析哪些知識點需要加強

---

## ⚙️ 進階配置

### 修改默認題數
編輯 `app_complete.py`，找到 `page_start_exam()` 函數：
```python
num_questions = st.radio(
    "選擇題數",
    options=[5, 10, 15, 20],  # 修改這裡
    horizontal=True
)
```

### 修改科目選項
編輯 `page_quiz_manage()` 中的 selectbox：
```python
subject = st.selectbox(
    "科目",
    ["數學", "國文", "英文", "社會", "自然", "物理", "化學"]  # 新增或刪除
)
```

### 支援更多題型
在 `database.py` 和 `app_complete.py` 中擴展：
```python
# 在題型判斷中添加
elif q['type'] == 'multiple':
    # 複選題邏輯
    pass
```

---

## 🐛 常見問題

**Q: 部署失敗？**
A: 檢查 `requirements.txt` 和 Python 版本（需 3.8+）

**Q: 無法上傳 PDF？**
A: 確保檔案格式正確、大小 < 200MB

**Q: 成績沒有保存？**
A: 檢查 `quiz_database.db` 是否有寫權限

**Q: 題目識別失敗？**
A: 確保 PDF 格式標準，查看 PDF_AI_QUIZ_GUIDE.md

---

## 📈 系統特點

✅ **完全免費** - 無隱藏費用  
✅ **本地資料庫** - 數據完全掌控  
✅ **手機相容** - Streamlit 原生支持  
✅ **快速部署** - 3 分鐘上線  
✅ **易於擴展** - 支援自定義修改  
✅ **實時更新** - Streamlit Cloud 自動同步  

---

## 📞 技術支援

遇到問題時：

1. 檢查控制台錯誤信息
2. 查看 `quiz_database.db` 是否存在
3. 嘗試清除瀏覽器快取
4. 重新啟動 Streamlit

---

## 📝 更新日誌

**v1.0 (2026-05-07)**
- ✅ PDF 批量解析
- ✅ 自定義題庫分類
- ✅ SQLite 存儲
- ✅ 完整測驗系統
- ✅ 自動計分
- ✅ 錯題本
- ✅ 成績統計
- ✅ 手機相容

---

## 🎯 後續改進

- [ ] 支援用戶登入
- [ ] 教師後台管理
- [ ] 實時成績排行榜
- [ ] 題目難度標記
- [ ] AI 推薦複習時間
- [ ] 導出成績報告

---

**版本：** 1.0  
**更新：** 2026-05-07  
**狀態：** ✅ 生產就緒

