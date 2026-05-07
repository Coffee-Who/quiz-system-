#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit 版本 - PDF 考卷自動解析系統
自動將國中考卷 PDF 轉換為題庫 JSON

使用方式：
    streamlit run app_streamlit.py
"""

import streamlit as st
import pdfplumber
import json
import re
from pathlib import Path
from typing import List, Dict, Tuple


class PDFQuizParser:
    """PDF 考卷解析器"""
    
    def __init__(self, pdf_file):
        """初始化解析器"""
        self.pdf_file = pdf_file
        self.text = ""
        self.questions = []
    
    def extract_text(self) -> str:
        """從 PDF 提取文本"""
        try:
            with pdfplumber.open(self.pdf_file) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
            
            self.text = text
            return text
        except Exception as e:
            st.error(f"❌ PDF 讀取失敗: {e}")
            return ""
    
    def parse_questions(self) -> List[Dict]:
        """解析題目格式"""
        
        lines = self.text.split('\n')
        questions = []
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # 匹配題號行：（ ） 1. 或 ( ) 1.
            if re.match(r'^[（(]\s*[）)]\s*\d+\.\s+', line):
                q_match = re.match(r'^[（(]\s*[）)]\s*(\d+)\.\s+(.+)$', line)
                
                if q_match:
                    q_num = q_match.group(1)
                    q_text = q_match.group(2)
                    
                    # 查找選項
                    options, answer = self._extract_options(lines, i + 1)
                    
                    if options:
                        question = {
                            "id": int(q_num),
                            "type": "single",
                            "text": q_text,
                            "options": options,
                            "correct": self._find_correct_option(answer),
                            "analysis": f"第 {q_num} 題的正確答案是 {answer}"
                        }
                        questions.append(question)
            
            i += 1
        
        self.questions = questions
        return questions
    
    def _extract_options(self, lines: List[str], start_idx: int) -> Tuple[List[str], str]:
        """提取選項"""
        options = []
        answer = ""
        
        for i in range(start_idx, min(start_idx + 5, len(lines))):
            line = lines[i].strip()
            
            if re.search(r'\([A-D]\)', line):
                matches = re.findall(r'\(([A-D])\)\s*([^(]*?)(?=\([A-D]\)|$)', line)
                
                for letter, content in matches:
                    options.append(f"({letter}) {content.strip()}")
                
                if len(options) >= 4:
                    options = options[:4]
                    break
        
        return options, answer
    
    def _find_correct_option(self, answer: str) -> int:
        """將答案字母轉換為索引"""
        if answer and answer.upper() in ['A', 'B', 'C', 'D']:
            return ord(answer.upper()) - ord('A')
        return -1
    
    def to_json(self) -> Dict:
        """轉換為 JSON 格式"""
        return {
            "metadata": {
                "total_questions": len(self.questions),
                "format_version": "1.0"
            },
            "questions": self.questions
        }


# ===== Streamlit UI =====

def main():
    """主程式"""
    
    st.set_page_config(
        page_title="PDF 考卷自動解析",
        page_icon="📚",
        layout="wide"
    )
    
    # 標題
    st.title("📚 PDF 考卷自動解析系統")
    st.markdown("---")
    
    # 側邊欄說明
    with st.sidebar:
        st.header("📖 使用說明")
        st.markdown("""
        **支援格式：**
        - 國中段考卷
        - 練習卷
        - 複習卷
        
        **自動識別：**
        - 題號 (１. 或 1.)
        - 題目內容
        - 選項 (A)(B)(C)(D)
        
        **輸出格式：**
        - JSON 題庫
        - 可直接匯入測驗系統
        
        ---
        
        **步驟：**
        1. 上傳 PDF
        2. 等待解析
        3. 預覽結果
        4. 下載 JSON
        """)
    
    # 主要內容區
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📄 上傳考卷")
        uploaded_file = st.file_uploader(
            "選擇 PDF 檔案",
            type="pdf",
            help="支援國中考卷、練習卷等 PDF 格式"
        )
    
    with col2:
        st.metric("已上傳", "已就緒" if uploaded_file else "等待中")
    
    # 處理上傳的檔案
    if uploaded_file is not None:
        st.success(f"✅ 已選擇: {uploaded_file.name}")
        
        # 解析按鈕
        if st.button("🔍 開始解析", use_container_width=True, type="primary"):
            with st.spinner("正在解析 PDF..."):
                # 初始化解析器
                parser = PDFQuizParser(uploaded_file)
                
                # 提取文本
                text = parser.extract_text()
                if not text:
                    st.stop()
                
                st.info(f"✅ 成功提取 {len(text)} 個字符")
                
                # 解析題目
                questions = parser.parse_questions()
                
                if not questions:
                    st.warning("⚠️ 未找到任何題目，請檢查 PDF 格式")
                    st.stop()
                
                st.success(f"✅ 成功解析 {len(questions)} 道題目！")
            
            # 顯示統計信息
            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📊 題目總數", len(questions))
            
            with col2:
                st.metric("📝 單選題", len([q for q in questions if q['type'] == 'single']))
            
            with col3:
                st.metric("✏️ 填空題", len([q for q in questions if q['type'] == 'fill']))
            
            with col4:
                st.metric("⚙️ 題型", "多種")
            
            # 題目預覽
            st.markdown("---")
            st.header("📋 題目預覽")
            
            # 分頁顯示
            items_per_page = 5
            num_pages = (len(questions) + items_per_page - 1) // items_per_page
            
            page = st.slider(
                "選擇頁碼",
                1,
                num_pages,
                1,
                help=f"共 {num_pages} 頁"
            )
            
            # 計算範圍
            start_idx = (page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, len(questions))
            
            # 顯示題目
            for q in questions[start_idx:end_idx]:
                with st.container(border=True):
                    st.write(f"**Q{q['id']}. {q['text']}**")
                    
                    # 選項
                    for opt in q['options']:
                        st.write(f"  {opt}")
                    
                    # 解析
                    with st.expander("📝 查看解析"):
                        st.write(q['analysis'])
            
            # 下載和操作區
            st.markdown("---")
            st.header("💾 操作")
            
            col1, col2, col3 = st.columns(3)
            
            # 轉換為 JSON
            json_data = parser.to_json()
            json_str = json.dumps(json_data, ensure_ascii=False, indent=2)
            
            with col1:
                st.download_button(
                    label="📥 下載 JSON",
                    data=json_str,
                    file_name=f"questions_{uploaded_file.name.replace('.pdf', '')}.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            with col2:
                if st.button("📋 複製 JSON", use_container_width=True):
                    st.write("```json")
                    st.write(json_str)
                    st.write("```")
                    st.info("✅ JSON 已顯示，可複製使用")
            
            with col3:
                if st.button("📊 統計信息", use_container_width=True):
                    st.json({
                        "file": uploaded_file.name,
                        "total_questions": len(questions),
                        "format_version": "1.0"
                    })
            
            # 文本預覽（可選）
            with st.expander("📄 查看提取的原始文本"):
                st.text_area(
                    "PDF 文本內容",
                    text[:2000] + "..." if len(text) > 2000 else text,
                    height=300,
                    disabled=True
                )
    
    else:
        # 沒有檔案時的提示
        st.info("👆 請先上傳 PDF 檔案")
        
        # 示例說明
        with st.expander("📖 支援的 PDF 格式示例"):
            st.code("""
（ ） 1. 下列哪一點不含通過直線 y=-2x+5？
     (A) (1,3)  (B) (0,5)  (C) (3,-1)  (D) (3,1)

（ ） 2. 在生標平面上，哪一條直線會過 (5,-2)？
     (A) 5x-2y=0  (B) x-y=3  (C) x-5=0  (D) x+2=0
            """)


if __name__ == "__main__":
    main()
