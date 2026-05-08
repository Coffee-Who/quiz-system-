#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
資料庫操作模組 - Firebase Firestore 雲端版本
自動偵測 FIREBASE_SERVICE_ACCOUNT secret，讓不同電腦共用同一題庫
"""

import json
import os
import random
from typing import List, Dict
from datetime import datetime


def _get_firestore_client():
    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        cred_dict = None
        try:
            import streamlit as st
            raw = st.secrets.get("FIREBASE_SERVICE_ACCOUNT", None)
            if raw:
                cred_dict = json.loads(raw) if isinstance(raw, str) else dict(raw)
        except Exception:
            pass
        if not cred_dict:
            raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "")
            if raw:
                cred_dict = json.loads(raw)
        if not cred_dict:
            raise RuntimeError("請在 Streamlit Cloud → Secrets 設定 FIREBASE_SERVICE_ACCOUNT")
        firebase_admin.initialize_app(credentials.Certificate(cred_dict))
    return firestore.client()


class QuizDatabase:
    def __init__(self, db_path: str = "quiz_database.db"):
        self._db = _get_firestore_client()

    def add_category(self, name: str, subject: str) -> bool:
        existing = list(self._db.collection("categories").where("name", "==", name).limit(1).stream())
        if existing:
            return False
        self._db.collection("categories").add({"name": name, "subject": subject, "created_at": datetime.utcnow()})
        return True

    def get_categories(self) -> List[Dict]:
        cats = []
        for doc in self._db.collection("categories").stream():
            data = doc.to_dict()
            q_count = len(list(self._db.collection("questions").where("category_id", "==", doc.id).stream()))
            cats.append({"id": doc.id, "name": data["name"], "subject": data["subject"], "count": q_count})
        cats.sort(key=lambda c: (c["subject"], c["name"]))
        return cats

    def delete_category(self, category_id: str) -> bool:
        try:
            db = self._db
            batch = db.batch()
            for doc in db.collection("wrong_questions").where("category_id", "==", category_id).stream():
                batch.delete(doc.reference)
            for doc in db.collection("exam_results").where("category_id", "==", category_id).stream():
                batch.delete(doc.reference)
            for doc in db.collection("questions").where("category_id", "==", category_id).stream():
                batch.delete(doc.reference)
            batch.delete(db.collection("categories").document(category_id))
            batch.commit()
            return True
        except Exception:
            return False

    def add_questions(self, category_id: str, questions: List[Dict]) -> int:
        db = self._db
        existing_q_ids = {doc.to_dict().get("q_id") for doc in db.collection("questions").where("category_id", "==", category_id).stream()}
        count = 0
        batch = db.batch()
        batch_ops = 0
        for q in questions:
            if q.get("id", 0) in existing_q_ids:
                continue
            ref = db.collection("questions").document()
            batch.set(ref, {
                "category_id": category_id, "q_id": q.get("id", 0),
                "type": q.get("type", "single"), "text": q.get("text", ""),
                "options": json.dumps(q.get("options", []), ensure_ascii=False),
                "correct": q.get("correct", -1), "analysis": q.get("analysis", ""),
                "created_at": datetime.utcnow(),
            })
            count += 1
            batch_ops += 1
            if batch_ops >= 400:
                batch.commit()
                batch = db.batch()
                batch_ops = 0
        if batch_ops > 0:
            batch.commit()
        return count

    def get_questions_by_category(self, category_id: str) -> List[Dict]:
        questions = []
        for doc in self._db.collection("questions").where("category_id", "==", category_id).stream():
            data = doc.to_dict()
            questions.append({"id": doc.id, "q_id": data["q_id"], "type": data["type"],
                               "text": data["text"], "options": json.loads(data["options"]),
                               "correct": data["correct"], "analysis": data.get("analysis", "")})
        questions.sort(key=lambda q: q["q_id"])
        return questions

    def get_random_questions(self, category_id: str, count: int) -> List[Dict]:
        all_qs = self.get_questions_by_category(category_id)
        random.shuffle(all_qs)
        return all_qs[:count]

    def save_exam_result(self, category_id: str, total: int, correct: int, duration: int, wrong_ids: List[str]) -> str:
        score = int((correct / total) * 100) if total > 0 else 0
        db = self._db
        _, er_ref = db.collection("exam_results").add({
            "category_id": category_id, "total_questions": total,
            "correct_count": correct, "score": score,
            "duration_seconds": duration, "created_at": datetime.utcnow(),
        })
        if wrong_ids:
            batch = db.batch()
            for q_id in wrong_ids:
                ref = db.collection("wrong_questions").document()
                batch.set(ref, {"question_id": q_id, "exam_result_id": er_ref.id,
                                "category_id": category_id, "created_at": datetime.utcnow()})
            batch.commit()
        return er_ref.id

    def get_exam_history(self, category_id: str = None) -> List[Dict]:
        db = self._db
        results = []
        for doc in db.collection("exam_results").stream():
            data = doc.to_dict()
            if category_id and data.get("category_id") != category_id:
                continue
            cat_doc = db.collection("categories").document(data["category_id"]).get()
            if not cat_doc.exists:
                continue
            cat = cat_doc.to_dict()
            results.append({"id": doc.id, "name": cat["name"], "subject": cat["subject"],
                             "total_questions": data["total_questions"], "correct_count": data["correct_count"],
                             "score": data["score"], "duration_seconds": data["duration_seconds"],
                             "created_at": str(data.get("created_at", ""))})
        results.sort(key=lambda r: r["created_at"], reverse=True)
        return results

    def get_wrong_questions(self, exam_result_id: str = None) -> List[Dict]:
        db = self._db
        query = db.collection("wrong_questions")
        if exam_result_id:
            query = query.where("exam_result_id", "==", exam_result_id)
        seen = set()
        wrong = []
        for wq_doc in query.stream():
            wq = wq_doc.to_dict()
            q_id = wq["question_id"]
            if q_id in seen:
                continue
            seen.add(q_id)
            q_doc = db.collection("questions").document(q_id).get()
            if not q_doc.exists:
                continue
            q = q_doc.to_dict()
            cat_doc = db.collection("categories").document(q["category_id"]).get()
            cat_name = cat_doc.to_dict().get("name", "") if cat_doc.exists else ""
            wrong.append({"id": q_id, "text": q["text"], "options": json.loads(q["options"]),
                          "correct": q["correct"], "analysis": q.get("analysis", ""), "name": cat_name})
        return wrong

    def get_statistics(self) -> Dict:
        db = self._db
        total_questions = len(list(db.collection("questions").stream()))
        total_categories = len(list(db.collection("categories").stream()))
        exam_docs = list(db.collection("exam_results").stream())
        total_exams = len(exam_docs)
        scores = [d.to_dict().get("score", 0) for d in exam_docs]
        avg_score = sum(scores) / len(scores) if scores else 0
        subject_data: Dict[str, List[int]] = {}
        for doc in exam_docs:
            data = doc.to_dict()
            cat_doc = db.collection("categories").document(data["category_id"]).get()
            if not cat_doc.exists:
                continue
            subj = cat_doc.to_dict().get("subject", "未知")
            subject_data.setdefault(subj, []).append(data.get("score", 0))
        return {
            "total_questions": total_questions, "total_categories": total_categories,
            "total_exams": total_exams, "avg_score": round(avg_score, 1),
            "subject_stats": [{"subject": s, "avg_score": round(sum(v)/len(v), 1), "count": len(v)} for s, v in subject_data.items()],
        }
