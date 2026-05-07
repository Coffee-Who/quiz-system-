#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite 資料庫操作模組
管理題庫、分類、成績等
"""

import sqlite3
import json
from typing import List, Dict, Tuple
from datetime import datetime
from pathlib import Path


class QuizDatabase:
    """題庫資料庫管理"""
    
    def __init__(self, db_path: str = "quiz_database.db"):
        """初始化資料庫"""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化資料庫表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 分類表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                subject TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 題目表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                q_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                text TEXT NOT NULL,
                options TEXT NOT NULL,
                correct INTEGER NOT NULL,
                analysis TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id),
                UNIQUE(category_id, q_id)
            )
        """)
        
        # 測驗成績表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exam_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                correct_count INTEGER NOT NULL,
                score INTEGER NOT NULL,
                duration_seconds INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        """)
        
        # 錯題本表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wrong_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                exam_result_id INTEGER NOT NULL,
                user_answer TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (question_id) REFERENCES questions(id),
                FOREIGN KEY (exam_result_id) REFERENCES exam_results(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    # ===== 分類操作 =====
    
    def add_category(self, name: str, subject: str) -> bool:
        """新增分類"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO categories (name, subject) VALUES (?, ?)",
                (name, subject)
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_categories(self) -> List[Dict]:
        """取得所有分類"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, subject, 
                   (SELECT COUNT(*) FROM questions WHERE category_id = categories.id) as count
            FROM categories
            ORDER BY subject, name
        """)
        categories = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return categories
    
    def delete_category(self, category_id: int) -> bool:
        """刪除分類及其題目"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
            cursor.execute("DELETE FROM questions WHERE category_id = ?", (category_id,))
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    # ===== 題目操作 =====
    
    def add_questions(self, category_id: int, questions: List[Dict]) -> int:
        """批量新增題目"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        count = 0
        
        for q in questions:
            try:
                cursor.execute("""
                    INSERT INTO questions 
                    (category_id, q_id, type, text, options, correct, analysis)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    category_id,
                    q.get('id', 0),
                    q.get('type', 'single'),
                    q.get('text', ''),
                    json.dumps(q.get('options', []), ensure_ascii=False),
                    q.get('correct', -1),
                    q.get('analysis', '')
                ))
                count += 1
            except sqlite3.IntegrityError:
                pass
        
        conn.commit()
        conn.close()
        return count
    
    def get_questions_by_category(self, category_id: int) -> List[Dict]:
        """取得某分類的所有題目"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, q_id, type, text, options, correct, analysis
            FROM questions
            WHERE category_id = ?
            ORDER BY q_id
        """, (category_id,))
        
        questions = []
        for row in cursor.fetchall():
            q = dict(row)
            q['options'] = json.loads(q['options'])
            questions.append(q)
        
        conn.close()
        return questions
    
    def get_random_questions(self, category_id: int, count: int) -> List[Dict]:
        """隨機取得題目"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, q_id, type, text, options, correct, analysis
            FROM questions
            WHERE category_id = ?
            ORDER BY RANDOM()
            LIMIT ?
        """, (category_id, count))
        
        questions = []
        for row in cursor.fetchall():
            q = dict(row)
            q['options'] = json.loads(q['options'])
            questions.append(q)
        
        conn.close()
        return questions
    
    # ===== 成績操作 =====
    
    def save_exam_result(self, category_id: int, total: int, correct: int, 
                        duration: int, wrong_ids: List[int]) -> int:
        """保存測驗成績"""
        score = int((correct / total) * 100) if total > 0 else 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 保存成績
        cursor.execute("""
            INSERT INTO exam_results 
            (category_id, total_questions, correct_count, score, duration_seconds)
            VALUES (?, ?, ?, ?, ?)
        """, (category_id, total, correct, score, duration))
        
        exam_result_id = cursor.lastrowid
        
        # 保存錯題
        for q_id in wrong_ids:
            cursor.execute("""
                INSERT INTO wrong_questions (question_id, exam_result_id)
                VALUES (?, ?)
            """, (q_id, exam_result_id))
        
        conn.commit()
        conn.close()
        
        return exam_result_id
    
    def get_exam_history(self, category_id: int = None) -> List[Dict]:
        """取得考試歷史"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if category_id:
            cursor.execute("""
                SELECT er.id, c.name, c.subject, er.total_questions, 
                       er.correct_count, er.score, er.duration_seconds, er.created_at
                FROM exam_results er
                JOIN categories c ON er.category_id = c.id
                WHERE er.category_id = ?
                ORDER BY er.created_at DESC
            """, (category_id,))
        else:
            cursor.execute("""
                SELECT er.id, c.name, c.subject, er.total_questions, 
                       er.correct_count, er.score, er.duration_seconds, er.created_at
                FROM exam_results er
                JOIN categories c ON er.category_id = c.id
                ORDER BY er.created_at DESC
            """)
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_wrong_questions(self, exam_result_id: int = None) -> List[Dict]:
        """取得錯題"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if exam_result_id:
            cursor.execute("""
                SELECT q.id, q.text, q.options, q.correct, q.analysis, c.name
                FROM wrong_questions wq
                JOIN questions q ON wq.question_id = q.id
                JOIN categories c ON q.category_id = c.id
                WHERE wq.exam_result_id = ?
            """, (exam_result_id,))
        else:
            cursor.execute("""
                SELECT DISTINCT q.id, q.text, q.options, q.correct, q.analysis, c.name
                FROM wrong_questions wq
                JOIN questions q ON wq.question_id = q.id
                JOIN categories c ON q.category_id = c.id
                ORDER BY wq.created_at DESC
            """)
        
        wrong = []
        for row in cursor.fetchall():
            w = dict(row)
            w['options'] = json.loads(w['options'])
            wrong.append(w)
        
        conn.close()
        return wrong
    
    def get_statistics(self) -> Dict:
        """取得統計數據"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 總題數
        cursor.execute("SELECT COUNT(*) FROM questions")
        total_questions = cursor.fetchone()[0]
        
        # 總分類數
        cursor.execute("SELECT COUNT(*) FROM categories")
        total_categories = cursor.fetchone()[0]
        
        # 總測驗次數
        cursor.execute("SELECT COUNT(*) FROM exam_results")
        total_exams = cursor.fetchone()[0]
        
        # 平均分數
        cursor.execute("SELECT AVG(score) FROM exam_results")
        avg_score = cursor.fetchone()[0] or 0
        
        # 按科目統計成績
        cursor.execute("""
            SELECT c.subject, AVG(er.score) as avg_score, COUNT(*) as count
            FROM exam_results er
            JOIN categories c ON er.category_id = c.id
            GROUP BY c.subject
        """)
        subject_stats = cursor.fetchall()
        
        conn.close()
        
        return {
            "total_questions": total_questions,
            "total_categories": total_categories,
            "total_exams": total_exams,
            "avg_score": round(avg_score, 1),
            "subject_stats": [
                {"subject": s[0], "avg_score": round(s[1], 1), "count": s[2]}
                for s in subject_stats
            ]
        }
