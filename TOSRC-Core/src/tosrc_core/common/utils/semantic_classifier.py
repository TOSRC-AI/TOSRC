#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
轻量级TF-IDF语义分类器
基于TF-IDF + 朴素贝叶斯，支持增量学习、多场景分类
"""
import re
import os
import joblib
from typing import List, Dict, Any, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
from sklearn.exceptions import NotFittedError

# 模型存储路径
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "models")
os.makedirs(MODEL_DIR, exist_ok=True)

class SemanticClassifier:
    """通用语义分类器"""
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model_path = os.path.join(MODEL_DIR, f"{model_name}.pkl")
        self.vectorizer_path = os.path.join(MODEL_DIR, f"{model_name}_vectorizer.pkl")
        
        # 尝试加载已有模型
        self.model = None
        self.vectorizer = None
        self.classes = []
        self._load_model()
        
        # 默认中文分词（简单按字符切分，适合短文本，无需分词依赖）
        self.token_pattern = re.compile(r'(?u)\b\w+\b|\S')
    
    def _tokenize(self, text: str) -> List[str]:
        """简单中文分词，按字符和单词切分，适合短文本分类"""
        return [t for t in self.token_pattern.findall(text.lower()) if t.strip()]
    
    def _load_model(self) -> None:
        """加载已有模型"""
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.vectorizer_path):
                self.model = joblib.load(self.model_path)
                self.vectorizer = joblib.load(self.vectorizer_path)
                self.classes = self.model.classes_.tolist()
        except Exception as e:
            # 加载失败则新建模型
            self.model = None
            self.vectorizer = None
    
    def _save_model(self) -> None:
        """保存模型到本地"""
        if self.model and self.vectorizer:
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.vectorizer, self.vectorizer_path)
    
    def train(self, texts: List[str], labels: List[str]) -> float:
        """训练模型
        Args:
            texts: 训练文本列表
            labels: 对应标签列表
        Returns:
            训练准确率
        """
        # 初始化pipeline
        self.vectorizer = TfidfVectorizer(
            tokenizer=self._tokenize,
            ngram_range=(1, 2),  # 1-2元语法
            max_features=5000,  # 最大特征数
            token_pattern=None  # 自定义tokenizer
        )
        self.model = MultinomialNB(alpha=0.1)  # 平滑系数
        
        # 训练
        X = self.vectorizer.fit_transform(texts)
        self.model.fit(X, labels)
        self.classes = self.model.classes_.tolist()
        
        # 保存模型
        self._save_model()
        
        # 返回训练准确率
        return self.model.score(X, labels)
    
    def predict(self, text: str) -> Tuple[str, float]:
        """预测文本分类
        Args:
            text: 待分类文本
        Returns:
            (标签, 置信度)
        """
        if not self.model or not self.vectorizer:
            return ("unknown", 0.0)
        
        try:
            X = self.vectorizer.transform([text])
            proba = self.model.predict_proba(X)[0]
            max_idx = proba.argmax()
            return (self.classes[max_idx], float(proba[max_idx]))
        except NotFittedError:
            return ("unknown", 0.0)
        except Exception as e:
            return ("unknown", 0.0)
    
    def add_sample(self, text: str, label: str, retrain: bool = False) -> None:
        """新增样本，支持增量学习
        Args:
            text: 样本文本
            label: 样本标签
            retrain: 是否立即重新训练全量模型
        """
        # 简单实现：暂存样本到本地文件，积累到一定数量再重新训练
        sample_file = os.path.join(MODEL_DIR, f"{self.model_name}_samples.txt")
        with open(sample_file, "a", encoding="utf-8") as f:
            f.write(f"{label}\t{text}\n")
        
        # 立即重新训练
        if retrain:
            # 读取所有样本
            texts = []
            labels = []
            if os.path.exists(sample_file):
                with open(sample_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or "\t" not in line:
                            continue
                        label, text = line.split("\t", 1)
                        texts.append(text)
                        labels.append(label)
            
            if len(texts) >= 10:  # 至少10个样本才训练
                self.train(texts, labels)

# ------------------------------
# 数字语义分类器实例（当前优先级最高）
# 分类标签：amount(金额)/area(面积)/floor(楼层)/age(楼龄)/count(数量)/other(其他)
# ------------------------------

# 初始训练样本（冷启动用，租房场景为主）
_NUMBER_TRAIN_TEXTS = [
    # 金额样本
    "租金2200元", "月租3500", "预算4000左右", "价格不超过5000", "物业费300块", "押金7000",
    "租金多少？3500", "一个月多少钱", "每月2800", "年付3万", "3k5左右", "不超4k",
    "价格2500押一付三", "房租2300元/月", "费用大概5000", "报价4200", "成交价3800",
    "2000块钱一个月", "1800每月", "3200元整", "4500左右", "6000以内", "3000以上",
    
    # 面积样本
    "80平的房子", "120平米", "90平方", "面积100㎡", "140m²大三居", "使用面积85平",
    "建筑面积120平", "60平小两居", "75㎡两室一厅", "150平四室", "50平一居室",
    "90多平", "80左右平", "100平上下", "110平的房子", "65㎡", "58平方",
    
    # 楼层样本
    "25楼", "在3层", "高楼层28层", "低楼层3楼", "中间楼层15层", "共32层",
    "10楼以上", "5楼以下", "第8层", "12楼", "22层", "6楼", "30层", "1楼",
    
    # 楼龄样本
    "楼龄10年", "房子20年了", "5年新小区", "建成15年", "10年老房子", "3年次新房",
    "20年房龄", "5年以内", "10年以上", "8年楼龄",
    
    # 数量样本
    "3室2厅", "2卫", "1个阳台", "4个空调", "3张床", "2个衣柜", "1套家具",
    "两室一厅", "三室两厅", "四室一卫", "1个厨房", "2个卫生间",
    
    # 其他
    "80平月租2200", "3室房租3500", "25楼面积100平", "10年楼龄价格4000",
    "5个房间租金5000", "3层120平3800元", "15楼90平4200"
]

_NUMBER_TRAIN_LABELS = [
    "amount", "amount", "amount", "amount", "amount", "amount",
    "amount", "amount", "amount", "amount", "amount", "amount",
    "amount", "amount", "amount", "amount", "amount",
    "amount", "amount", "amount", "amount", "amount", "amount",
    
    "area", "area", "area", "area", "area", "area",
    "area", "area", "area", "area", "area",
    "area", "area", "area", "area", "area", "area",
    
    "floor", "floor", "floor", "floor", "floor", "floor",
    "floor", "floor", "floor", "floor", "floor", "floor", "floor", "floor",
    
    "age", "age", "age", "age", "age", "age",
    "age", "age", "age", "age",
    
    "count", "count", "count", "count", "count", "count", "count",
    "count", "count", "count", "count", "count",
    
    "other", "other", "other", "other",
    "other", "other", "other"
]

# 全局单例：数字语义分类器
number_classifier = SemanticClassifier("number_semantic")

# 冷启动：如果没有模型则用初始样本训练
if not number_classifier.model:
    acc = number_classifier.train(_NUMBER_TRAIN_TEXTS, _NUMBER_TRAIN_LABELS)
    print(f"数字语义分类器初始化完成，初始训练准确率: {acc:.2%}")
