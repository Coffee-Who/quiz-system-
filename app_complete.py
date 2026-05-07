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

    # 支援半角 (A)、全角 （A）、全角字母 （Ａ） 三種格式
    OPTION_RE = re.compile(r'[（(]([A-DＡ-Ｄ])[）)]')

    # 題號格式（多種）
    Q_NUM_PATTERNS = [
        re.compile(r'[（(]\s*[）)]\s*(\d+)\s*[.、．]'),  # （ ）1.
        re.compile(r'(?:^|\s)(\d+)\s*[.、．]\s'),         # 1.
        re.compile(r'第\s*(\d+)\s*[題题]'),               # 第1題
    ]

    @staticmethod
    def extract_text(pdf_file) -> str:
        try:
            with pdfplumber.open(pdf_file) as pdf:
                pages_text = []
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        pages_text.append(t)
            return "\n".join(pages_text)
        except Exception as e:
            st.error(f"❌ PDF 讀取失敗: {e}")
            return ""

    @staticmethod
    def parse_questions(text: str) -> List[Dict]:
        """先找選項行，再往上找題號 — 適合台灣考卷格式"""
        lines = text.split('\n')
        debug_log = [
            f"📄 總字符：{len(text)}　📋 總行數：{len(lines)}",
            f"🔍 半角選項 (A)：{len(re.findall(chr(40)+'[A-D]'+chr(41), text))} 個　"
            f"全角選項 （A）：{len(re.findall('（[A-D]）', text))} 個",
        ]

        # 找出每行含有哪些選項字母
        def get_letters(line):
            return [m.group(1) for m in PDFQuizParser.OPTION_RE.finditer(line)]

        # 合併相鄰選項行（有些 PDF 把 ABCD 拆成兩行）
        opt_groups = []   # [(opt_text, last_line_idx)]
        i = 0
        while i < len(lines):
            letters = get_letters(lines[i])
            if letters:
                opt_text = lines[i]
                last_i = i
                # 如果下一行也有選項且不包含 A（避免把下一題的選項合進來）
                if i + 1 < len(lines):
                    next_letters = get_letters(lines[i + 1])
                    if next_letters and 'A' not in next_letters:
                        opt_text += ' ' + lines[i + 1]
                        last_i = i + 1
                        i += 1
                opt_groups.append((opt_text, last_i))
            i += 1

        debug_log.append(f"📌 找到 {len(opt_groups)} 個選項群組")

        questions = []
        seen_q_nums = set()

        for opt_text, opt_line_idx in opt_groups:
            options = PDFQuizParser._extract_all_options(opt_text)
            if len(options) < 2:
                continue

            # 往上找題號（最多搜尋 10 行）
            q_num = None
            q_text_parts = []

            for j in range(opt_line_idx - 1, max(opt_line_idx - 10, -1), -1):
                line = lines[j].strip()
                if not line:
                    continue
                # 遇到其他選項行就停止
                if PDFQuizParser.OPTION_RE.search(line):
                    break

                # 嘗試從這行找題號
                found = False
                for pat in PDFQuizParser.Q_NUM_PATTERNS:
                    m = pat.search(line)
                    if m:
                        q_num = int(m.group(1))
                        after = line[m.end():].strip()
                        if after:
                            q_text_parts.insert(0, after)
                        found = True
                        break

                if found:
                    break
                else:
                    q_text_parts.insert(0, line)

            if q_num is None or q_num in seen_q_nums:
                continue
            seen_q_nums.add(q_num)

            q_text = ' '.join(q_text_parts).strip()
            questions.append({
                "id": q_num,
                "type": "single",
                "text": q_text,
                "options": options[:4],
                "correct": -1,
                "analysis": f"第 {q_num} 題"
            })

        questions.sort(key=lambda x: x['id'])
        debug_log.append(f"✨ 最終解析：{len(questions)} 題")

        # 若上面方法失敗，用舊的文字區塊法備援
        if len(questions) == 0:
            for pat in PDFQuizParser.Q_NUM_PATTERNS:
                qs = PDFQuizParser._parse_with_pattern(text, lines, pat)
                debug_log.append(f"   備援策略：{len(qs)} 題")
                if len(qs) > len(questions):
                    questions = qs

        st.session_state.pdf_parse_debug = "\n".join(debug_log)
        return questions

    @staticmethod
    def _parse_with_pattern(text: str, lines: List[str], q_pattern: re.Pattern) -> List[Dict]:
        """備援：用題號切塊再找選項"""
        matches = list(q_pattern.finditer(text))
        if not matches:
            return []
        questions = []
        for idx, match in enumerate(matches):
            q_num = int(match.group(1))
            block_start = match.end()
            block_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            q_block = text[block_start:block_end]
            first_opt = PDFQuizParser.OPTION_RE.search(q_block)
            if not first_opt:
                continue
            q_text = q_block[:first_opt.start()].strip()
            options = PDFQuizParser._extract_all_options(q_block[first_opt.start():])
            if len(options) >= 2:
                questions.append({
                    "id": q_num, "type": "single",
                    "text": q_text, "options": options[:4],
                    "correct": -1, "analysis": f"第 {q_num} 題"
                })
        return questions

    @staticmethod
    def _extract_all_options(block: str) -> List[str]:
        """提取選項，支援半角 (A) 和全角 （A）"""
        positions = [
            {'letter': m.group(1), 'pos': m.start(), 'start': m.end()}
            for m in PDFQuizParser.OPTION_RE.finditer(block)
        ]
        if not positions:
            return []
        options = []
        for i, p in enumerate(positions):
            text_end = positions[i + 1]['pos'] if i + 1 < len(positions) else len(block)
            content = block[p['start']:text_end].strip()
            content = re.sub(r'[。，、；：.,:;\s]+$', '', content)
            # 全角字母正規化為半角
            letter = p['letter'] if p['letter'] in 'ABCD' else chr(ord(p['letter']) - 0xFF21 + 0x41)
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
                st.subheader("🔍 偵測結果")

                if text:
                    half_opts = len(re.findall(r'\([A-D]\)', text))
                    full_opts = len(re.findall(r'（[A-D]）', text))
                    st.write(f"**選項括號**：半角 `(A)` {half_opts} 個 ／ 全角 `（A）` {full_opts} 個")

                    for pat_str, desc in [
                        (r'[（(]\s*[）)]\s*\d+[.、．]', "格式1：（ ）1."),
                        (r'(?:^|\s)\d+[.、．]\s', "格式2：行首 1."),
                        (r'第\s*\d+\s*[題题]', "格式3：第N題"),
                    ]:
                        n = len(re.findall(pat_str, text, re.MULTILINE))
                        st.write(f"**{desc}**：找到 {n} 個")

                st.divider()
                st.subheader("📋 前 20 行原始文字（關鍵）")
                if text:
                    preview_lines = text.split('\n')[:20]
                    for idx, ln in enumerate(preview_lines):
                        st.code(f"{idx+1:3d} | {ln}", language="text")
        
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
