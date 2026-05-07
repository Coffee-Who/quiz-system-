#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整 PDF 題庫 + 測驗系統
Streamlit + SQLite

功能：
1. PDF 批量解析
2. 自定義題庫分類
3. 線上測驗
4. 自動計分
5. 錯題本
6. 成績統計
"""

import streamlit as st
import pdfplumber
import json
import time
import re
from datetime import datetime
from typing import List, Dict
from database import QuizDatabase


# ===== 頁面配置 =====

st.set_page_config(
    page_title="PDF 題庫測驗系統",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== 初始化 =====

if 'db' not in st.session_state:
    st.session_state.db = QuizDatabase()

if 'current_page' not in st.session_state:
    st.session_state.current_page = "首頁"

if 'exam_state' not in st.session_state:
    st.session_state.exam_state = {
        'active': False,
        'start_time': None,
        'questions': [],
        'answers': [],
        'current_idx': 0
    }


# ===== PDF 解析器 =====

class PDFQuizParser:
    """PDF 考卷解析"""
    
    @staticmethod
    def extract_text(pdf_file) -> str:
        """提取 PDF 文本"""
        try:
            with pdfplumber.open(pdf_file) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
            return text
        except Exception as e:
            st.error(f"❌ PDF 讀取失敗: {e}")
            return ""
    
    @staticmethod
    def parse_questions(text: str) -> List[Dict]:
        """解析題目 - 正確的題號格式：（ ） 1."""
        
        questions = []
        
        # 正確的題號模式：( ) 或 （ ） + 數字 + .
        pattern = r'[（(]\s*[）)]\s*(\d+)\.\s+'
        
        lines = text.split('\n')
        i = 0
        
        # 調試：記錄找到的題號
        found_questions_debug = []
        
        while i < len(lines):
            line = lines[i]
            match = re.search(pattern, line)
            
            if match:
                q_num = int(match.group(1))
                q_start = match.end()
                q_text = line[q_start:].strip()
                
                found_questions_debug.append(f"題{q_num}")
                
                # 蒐集後續行直到下一個題號
                options = []
                j = i + 1
                
                while j < len(lines):
                    next_line = lines[j]
                    
                    # 檢查是否是下一個題號
                    if re.search(pattern, next_line):
                        break
                    
                    next_line_stripped = next_line.strip()
                    
                    if not next_line_stripped:
                        j += 1
                        continue
                    
                    # 尋找選項：(A) (B) 等（全角或半角括號都支援）
                    if re.search(r'[（(][A-D][）)]', next_line_stripped):
                        opts = PDFQuizParser._extract_all_options(next_line_stripped)
                        options.extend(opts)
                    else:
                        # 沒有選項就加到題文
                        if len(options) == 0:
                            q_text += " " + next_line_stripped
                    
                    j += 1
                    
                    # 找到 4 個選項就停止
                    if len(options) >= 4:
                        break
                
                # 創建題目
                if len(options) >= 2:
                    question = {
                        "id": q_num,
                        "type": "single",
                        "text": q_text.strip(),
                        "options": options[:4],
                        "correct": -1,
                        "analysis": f"第 {q_num} 題"
                    }
                    questions.append(question)
                else:
                    # 調試：記錄未成功創建的題目
                    found_questions_debug.append(f"  ❌ 題{q_num}：只找到 {len(options)} 個選項")
                
                i = j
                continue
            
            i += 1
        
        # 將調試信息存儲在 session_state（供前端顯示）
        import streamlit as st
        if 'last_parse_debug' not in st.session_state:
            st.session_state.last_parse_debug = []
        st.session_state.last_parse_debug = found_questions_debug
        
        return questions

    
    @staticmethod
    def _extract_all_options(block: str) -> List[str]:
        """從選項區塊提取所有 A B C D 選項"""
        options = []
        
        # 找所有選項的位置
        positions = []
        for match in re.finditer(r'[（(]([A-D])[）)]', block):
            positions.append({
                'letter': match.group(1),
                'start': match.end(),
                'pos': match.start()
            })
        
        if not positions:
            return []
        
        # 根據位置提取內容
        for i, pos_info in enumerate(positions):
            letter = pos_info['letter']
            text_start = pos_info['start']
            
            # 到下一個選項開始前結束
            if i + 1 < len(positions):
                text_end = positions[i + 1]['pos']
            else:
                text_end = len(block)
            
            content = block[text_start:text_end].strip()
            
            # 移除末尾標點符號
            content = re.sub(r'[。，、；：\.\,;:\s]+$', '', content)
            
            if content:
                options.append(f"({letter}) {content}")
        
        return options



# ===== 頁面函數 =====

def page_home():
    """首頁"""
    st.title("📚 PDF 題庫測驗系統")
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📚 題庫分類", st.session_state.db.get_statistics()['total_categories'])
    
    with col2:
        st.metric("📝 總題數", st.session_state.db.get_statistics()['total_questions'])
    
    with col3:
        st.metric("✅ 測驗次數", st.session_state.db.get_statistics()['total_exams'])
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📤 題庫管理", use_container_width=True, key="home_manage"):
            st.session_state.current_page = "題庫管理"
            st.rerun()
    
    with col2:
        if st.button("✏️ 開始測驗", use_container_width=True, key="home_exam"):
            st.session_state.current_page = "開始測驗"
            st.rerun()
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("❌ 錯題本", use_container_width=True, key="home_wrong"):
            st.session_state.current_page = "錯題本"
            st.rerun()
    
    with col2:
        if st.button("📊 成績統計", use_container_width=True, key="home_stats"):
            st.session_state.current_page = "成績統計"
            st.rerun()


def page_quiz_manage():
    """題庫管理"""
    st.title("📚 題庫管理")
    st.markdown("---")
    
    tabs = st.tabs(["上傳 PDF", "查看分類", "分類統計"])
    
    # Tab 1: 上傳 PDF
    with tabs[0]:
        st.subheader("📤 上傳 PDF 並建立分類")
        
        col1, col2 = st.columns(2)
        
        with col1:
            category_name = st.text_input("分類名稱", placeholder="例如：CH2 圖形")
        
        with col2:
            subject = st.selectbox("科目", ["數學", "國文", "英文", "社會", "自然", "其他"])
        
        uploaded_file = st.file_uploader("選擇 PDF", type="pdf")
        
        if uploaded_file:
            st.success(f"✅ 已選擇: {uploaded_file.name}")
            
            # 調試：顯示原始文本
            with st.expander("📄 查看提取的文本（調試用）"):
                text = PDFQuizParser.extract_text(uploaded_file)
                
                st.subheader("完整原始文本（前 3000 字）")
                st.text_area(
                    "原始文本內容",
                    text[:3000] if text else "（無法提取）",
                    height=400,
                    disabled=True,
                    key="debug_text_main"
                )
                
                st.divider()
                st.subheader("🔍 題號偵測結果")
                
                question_patterns = [
                    (r'[（(]\s*[）)]\s+', "括號題號（無數字）"),
                    (r'[（(]\s*[）)]\s*\d+\.', "括號題號（有數字）"),
                    (r'^\d+\.', "純數字題號"),
                ]
                
                for pattern, desc in question_patterns:
                    matches = list(re.finditer(pattern, text)) if text else []
                    st.write(f"**{desc}**: 找到 {len(matches)} 個")
                
                st.divider()
                st.subheader("顯示前 10 個括號位置（調試用）")
                matches = list(re.finditer(r'[（(]\s*[）)]', text)) if text else []
                
                if matches:
                    for i, m in enumerate(matches[:10]):
                        start = max(0, m.start() - 30)
                        end = min(len(text), m.end() + 80)
                        preview = text[start:end]
                        st.code(f"位置 {i+1}: ...{preview}...", language="text")
        
        if uploaded_file and category_name:
            if st.button("🔍 解析並匯入", use_container_width=True):
                with st.spinner("正在解析..."):
                    # 提取文本
                    text = PDFQuizParser.extract_text(uploaded_file)
                    if not text:
                        st.stop()
                    
                    st.info(f"✅ 成功提取 {len(text)} 個字符")
                    
                    # 解析題目
                    questions = PDFQuizParser.parse_questions(text)
                    
                    if questions:
                        st.success(f"✅ 找到 {len(questions)} 道題目")
                        
                        # 新增分類
                        if st.session_state.db.add_category(category_name, subject):
                            # 取得新分類 ID
                            categories = st.session_state.db.get_categories()
                            cat_id = [c['id'] for c in categories if c['name'] == category_name][0]
                            
                            # 匯入題目
                            count = st.session_state.db.add_questions(cat_id, questions)
                            st.success(f"✅ 成功匯入 {count} 道題目到 [{category_name}]")
                        else:
                            st.warning(f"⚠️ 分類名稱已存在")
                    else:
                        st.error("❌ 未找到任何題目")
                        st.warning("請檢查 PDF 格式是否標準，或在上方「查看提取的文本」中查看內容")
    
    # Tab 2: 查看分類
    with tabs[1]:
        st.subheader("📋 已有分類")
        
        categories = st.session_state.db.get_categories()
        
        if categories:
            for cat in categories:
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**{cat['subject']} - {cat['name']}**")
                
                with col2:
                    st.metric("題數", cat['count'])
                
                with col3:
                    if st.button("🗑️", key=f"del_{cat['id']}"):
                        st.session_state.db.delete_category(cat['id'])
                        st.success("✅ 已刪除")
                        st.rerun()
        else:
            st.info("還沒有分類")
    
    # Tab 3: 統計
    with tabs[2]:
        stats = st.session_state.db.get_statistics()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("分類數", stats['total_categories'])
        with col2:
            st.metric("題目數", stats['total_questions'])
        with col3:
            st.metric("平均分數", f"{stats['avg_score']}分")


def page_start_exam():
    """開始測驗"""
    st.title("✏️ 開始測驗")
    st.markdown("---")
    
    categories = st.session_state.db.get_categories()
    
    if not categories:
        st.warning("⚠️ 沒有題庫，請先在【題庫管理】上傳 PDF")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_cat = st.selectbox(
            "選擇科目",
            options=[f"{c['subject']} - {c['name']}" for c in categories],
            format_func=lambda x: x
        )
        category_id = [c['id'] for c in categories if f"{c['subject']} - {c['name']}" == selected_cat][0]
    
    with col2:
        num_questions = st.radio(
            "選擇題數",
            options=[10, 20, 30],
            horizontal=True
        )
    
    if st.button("🚀 開始測驗", use_container_width=True, type="primary"):
        # 隨機取題
        questions = st.session_state.db.get_random_questions(category_id, num_questions)
        
        if questions:
            st.session_state.exam_state = {
                'active': True,
                'start_time': time.time(),
                'category_id': category_id,
                'questions': questions,
                'answers': [-1] * len(questions),
                'current_idx': 0
            }
            st.session_state.current_page = "進行中"
            st.rerun()
        else:
            st.error("❌ 題數不足")


def page_exam_ongoing():
    """進行中的測驗"""
    exam = st.session_state.exam_state
    
    if not exam['active']:
        st.warning("⚠️ 測驗未啟動")
        return
    
    st.title("📋 測驗進行中")
    
    # 上方欄位
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        st.metric("進度", f"{exam['current_idx'] + 1}/{len(exam['questions'])}")
    
    with col2:
        progress = (exam['current_idx'] + 1) / len(exam['questions'])
        st.progress(progress)
    
    with col3:
        elapsed = int(time.time() - exam['start_time'])
        minutes = elapsed // 60
        seconds = elapsed % 60
        st.metric("時間", f"{minutes}:{seconds:02d}")
    
    st.markdown("---")
    
    # 顯示當前題目
    if exam['current_idx'] < len(exam['questions']):
        q = exam['questions'][exam['current_idx']]
        
        st.subheader(f"Q{exam['current_idx'] + 1}. {q['text']}")
        
        # 單選題
        if q['type'] == 'single':
            selected = st.radio(
                "選擇答案：",
                options=list(range(len(q['options']))),
                format_func=lambda x: q['options'][x],
                key=f"q_{exam['current_idx']}"
            )
            exam['answers'][exam['current_idx']] = selected
        
        # 填空題
        elif q['type'] == 'fill':
            answer = st.text_input(
                "填寫答案：",
                key=f"q_fill_{exam['current_idx']}"
            )
            exam['answers'][exam['current_idx']] = answer
        
        st.markdown("---")
        
        # 導航按鈕
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("⬅️ 上一題", use_container_width=True):
                if exam['current_idx'] > 0:
                    exam['current_idx'] -= 1
                    st.rerun()
        
        with col2:
            if st.button("➡️ 下一題", use_container_width=True):
                if exam['current_idx'] < len(exam['questions']) - 1:
                    exam['current_idx'] += 1
                    st.rerun()
        
        with col3:
            if st.button("✅ 提交測驗", use_container_width=True, type="primary"):
                # 計算成績
                correct = 0
                wrong_ids = []
                
                for i, q in enumerate(exam['questions']):
                    if q['type'] == 'single':
                        if exam['answers'][i] == q['correct']:
                            correct += 1
                        else:
                            wrong_ids.append(q['id'])
                
                # 保存成績
                duration = int(time.time() - exam['start_time'])
                st.session_state.db.save_exam_result(
                    exam['category_id'],
                    len(exam['questions']),
                    correct,
                    duration,
                    wrong_ids
                )
                
                # 跳轉到結果頁
                st.session_state.exam_state['active'] = False
                st.session_state.current_page = "測驗結果"
                st.session_state.last_result = {
                    'total': len(exam['questions']),
                    'correct': correct,
                    'score': int((correct / len(exam['questions'])) * 100),
                    'duration': duration,
                    'questions': exam['questions'],
                    'answers': exam['answers']
                }
                st.rerun()


def page_exam_result():
    """測驗結果"""
    st.title("🎉 測驗完成")
    st.markdown("---")
    
    result = st.session_state.last_result
    
    # 成績圓圈
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        score = result['score']
        if score >= 80:
            emoji = "🎉"
            msg = "太棒了！"
        elif score >= 60:
            emoji = "👍"
            msg = "不錯！"
        else:
            emoji = "💪"
            msg = "加油！"
        
        st.markdown(f"<h1 style='text-align: center'>{emoji} {score}/100 分</h1>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align: center'>{msg}</h3>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 統計
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("✅ 正確", result['correct'])
    
    with col2:
        st.metric("❌ 錯誤", result['total'] - result['correct'])
    
    with col3:
        minutes = result['duration'] // 60
        seconds = result['duration'] % 60
        st.metric("⏱️ 耗時", f"{minutes}分{seconds}秒")
    
    st.markdown("---")
    
    # 返回按鈕
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🏠 返回首頁", use_container_width=True):
            st.session_state.current_page = "首頁"
            st.rerun()
    
    with col2:
        if st.button("📝 再練一次", use_container_width=True):
            st.session_state.current_page = "開始測驗"
            st.rerun()


def page_wrong_questions():
    """錯題本"""
    st.title("❌ 錯題本")
    st.markdown("---")
    
    wrong_list = st.session_state.db.get_wrong_questions()
    
    if not wrong_list:
        st.info("✅ 沒有錯題！")
        return
    
    st.write(f"共 {len(wrong_list)} 道錯題")
    st.markdown("---")
    
    for i, q in enumerate(wrong_list, 1):
        with st.container(border=True):
            st.write(f"**{q['name']} - Q{i}**")
            st.write(f"**題目：** {q['text']}")
            
            st.write("**選項：**")
            for opt in q['options']:
                st.write(f"  {opt}")
            
            st.write(f"**正確答案：** {q['options'][q['correct']]}")
            
            with st.expander("📝 查看解析"):
                st.write(q['analysis'])


def page_statistics():
    """成績統計"""
    st.title("📊 成績統計")
    st.markdown("---")
    
    stats = st.session_state.db.get_statistics()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("總測驗次數", stats['total_exams'])
    
    with col2:
        st.metric("平均分數", f"{stats['avg_score']}")
    
    with col3:
        st.metric("題庫分類", stats['total_categories'])
    
    with col4:
        st.metric("總題數", stats['total_questions'])
    
    st.markdown("---")
    
    # 按科目統計
    if stats['subject_stats']:
        st.subheader("按科目統計")
        for s in stats['subject_stats']:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"{s['subject']}")
            with col2:
                st.metric("平均分", f"{s['avg_score']}", f"({s['count']}次)")
    
    st.markdown("---")
    
    # 考試歷史
    st.subheader("📜 考試歷史")
    
    history = st.session_state.db.get_exam_history()
    
    if history:
        for h in history[:20]:  # 顯示最近 20 次
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col1:
                st.write(f"**{h['subject']} - {h['name']}**")
            with col2:
                st.write(f"{h['correct_count']}/{h['total_questions']}")
            with col3:
                st.write(f"{h['score']}分")
            with col4:
                st.caption(h['created_at'][:10])
    else:
        st.info("還沒有考試記錄")


# ===== 主程式 =====

def main():
    """主程式"""
    
    # 側邊欄導航
    with st.sidebar:
        st.title("📚 題庫系統")
        st.markdown("---")
        
        pages = ["首頁", "題庫管理", "開始測驗", "錯題本", "成績統計"]
        
        for page in pages:
            if st.button(page, use_container_width=True, 
                        key=f"nav_{page}",
                        type="primary" if st.session_state.current_page == page else "secondary"):
                st.session_state.current_page = page
                st.rerun()
    
    # 路由
    if st.session_state.current_page == "首頁":
        page_home()
    
    elif st.session_state.current_page == "題庫管理":
        page_quiz_manage()
    
    elif st.session_state.current_page == "開始測驗":
        page_start_exam()
    
    elif st.session_state.current_page == "進行中":
        page_exam_ongoing()
    
    elif st.session_state.current_page == "測驗結果":
        page_exam_result()
    
    elif st.session_state.current_page == "錯題本":
        page_wrong_questions()
    
    elif st.session_state.current_page == "成績統計":
        page_statistics()


if __name__ == "__main__":
    main()
