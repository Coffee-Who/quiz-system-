# Streamlit 版本 - PDF 考卷自動解析系統

## 🚀 快速開始

### 本地運行（1分鐘）

```bash
# 1. 安裝依賴
pip install -r requirements.txt

# 2. 運行 Streamlit
streamlit run app_streamlit.py

# 3. 自動打開瀏覽器
# http://localhost:8501
```

### GitHub 部署到 Streamlit Cloud（3分鐘）

1. **推送代碼到 GitHub**
```bash
git init
git add .
git commit -m "PDF Quiz System - Streamlit Version"
git remote add origin https://github.com/yourusername/pdf-quiz-system.git
git push -u origin main
```

2. **連接 Streamlit Cloud**
   - 去 https://streamlit.io/cloud
   - 點「New app」
   - 選擇 GitHub 倉庫
   - 選擇分支和檔案：`app_streamlit.py`
   - 點「Deploy」

3. **完成！**
   - Streamlit 自動部署
   - 獲得公開 URL（例如 `https://yourapp-abc123.streamlit.app`）

---

## 📁 檔案結構

```
pdf-quiz-system/
├── app_streamlit.py          # Streamlit 主程式
├── requirements.txt          # Python 依賴
├── .gitignore               # Git 忽略檔案（可選）
└── README.md                # 項目說明（可選）
```

---

## 🎯 功能

✅ **PDF 上傳**
- 拖拽或點擊上傳
- 支援國中考卷、練習卷

✅ **自動解析**
- 識別題號、題目、選項
- 支援格式：`（ ） 1. 題目？ (A) ... (B) ... (C) ... (D) ...`

✅ **即時預覽**
- 顯示解析結果
- 分頁瀏覽題目

✅ **下載 JSON**
- 標準格式：`{question, options, answer, explanation}`
- 可直接匯入測驗系統

---

## 📊 JSON 輸出示例

```json
{
  "metadata": {
    "total_questions": 10,
    "format_version": "1.0"
  },
  "questions": [
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
      "correct": -1,
      "analysis": "第 1 題的正確答案是"
    }
  ]
}
```

---

## 💡 使用技巧

### 快速測試
```bash
streamlit run app_streamlit.py --logger.level=debug
```

### 清除快取
```bash
streamlit cache clear
```

### 部署後更新
在 Streamlit Cloud 控制台點「Rerun」即可更新

---

## 🔧 自訂設置

### 修改頁面配置
```python
st.set_page_config(
    page_title="自訂標題",
    page_icon="🎓",
    layout="wide"  # 或 "centered"
)
```

### 修改每頁顯示題數
```python
items_per_page = 10  # 改為 10 題
```

---

## ⚠️ 常見問題

**Q: 部署失敗？**
A: 確保 `requirements.txt` 在根目錄，且包含所有依賴

**Q: 無法上傳 PDF？**
A: 檢查檔案大小（<200MB）和格式（PDF）

**Q: 無法解析某些題目？**
A: 確保 PDF 格式標準，如需修改正則表達式見代碼註釋

---

## 📈 進階功能

### 支援更多題型
```python
def parse_questions(self):
    # 添加填空題判斷
    if '_____' in line or '填空' in line:
        question['type'] = 'fill'
```

### 自動答案檢測
```python
# 從答案卷 PDF 自動提取答案
# 需要額外的 OCR 模型
```

---

## 🌐 部署後的 URL

部署後您的應用會在以下地址可用：
```
https://[your-username]-pdf-quiz-system.streamlit.app
```

可分享給學生使用！

---

## 📝 項目佈置清單

- [ ] 下載 3 個檔案
- [ ] 推送到 GitHub
- [ ] 連接 Streamlit Cloud
- [ ] 測試上傳 PDF
- [ ] 驗證 JSON 輸出
- [ ] 分享 URL 給學生

---

**版本：** 1.0  
**更新：** 2026-05-07  
**狀態：** ✅ 準備部署

