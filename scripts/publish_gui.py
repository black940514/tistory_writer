#!/usr/bin/env python3
"""
논문 리뷰 발행기 Pro v3.0
Professional Paper Review Publisher with Modern UI

Features:
- 기존 논문 리스트에서 선택하여 발행
- 새 논문 제목으로 검색하여 발행
- 배치 발행 (대기열 시스템)
- PDF 자동 다운로드
- 전문적인 다크 모드 UI
"""
import sys
import json
import random
from pathlib import Path
import webbrowser
import subprocess
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QLineEdit,
    QCheckBox, QTextEdit, QProgressBar, QMessageBox, QGroupBox,
    QHeaderView, QAbstractItemView, QTabWidget, QFrame, QShortcut,
    QMenu, QAction, QCompleter, QSplitter, QDialog, QDialogButtonBox,
    QFileDialog, QComboBox, QSpacerItem, QSizePolicy, QGraphicsDropShadowEffect,
    QScrollArea, QSpinBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QStringListModel, QUrl, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QKeySequence, QPalette, QColor, QIcon, QLinearGradient, QBrush
import requests
import re
import logging

# 로거 설정
logger = logging.getLogger(__name__)

# ===== 색상 팔레트 (상용 프로그램 수준) =====
class Colors:
    """전문적인 다크 테마 색상 팔레트"""
    # 배경
    BG_DARK = "#1a1a1f"
    BG_MAIN = "#222228"
    BG_CARD = "#2a2a32"
    BG_ELEVATED = "#32323c"
    BG_HOVER = "#3a3a45"

    # 테두리
    BORDER = "#3d3d47"
    BORDER_LIGHT = "#4a4a55"
    BORDER_FOCUS = "#5a9fff"

    # 텍스트
    TEXT_PRIMARY = "#f0f0f5"
    TEXT_SECONDARY = "#a0a0ab"
    TEXT_MUTED = "#707080"
    TEXT_DISABLED = "#505058"

    # 강조 색상
    PRIMARY = "#5a9fff"        # 메인 액센트 (파랑)
    PRIMARY_DARK = "#4080e0"
    PRIMARY_LIGHT = "#7ab5ff"

    SUCCESS = "#4ade80"        # 성공 (초록)
    SUCCESS_DARK = "#22c55e"

    WARNING = "#fbbf24"        # 경고 (노랑)
    WARNING_DARK = "#f59e0b"

    ERROR = "#f87171"          # 에러 (빨강)
    ERROR_DARK = "#ef4444"

    INFO = "#38bdf8"           # 정보 (하늘)

    # 상태 색상
    STATUS_PENDING = "#6b7280"
    STATUS_RUNNING = "#3b82f6"
    STATUS_SUCCESS = "#22c55e"
    STATUS_FAILED = "#ef4444"


# ===== 논문 분야 분류 시스템 =====
class PaperCategorizer:
    """AI 논문을 분야별로 분류하고 추천하는 시스템"""
    
    # 2024-2025 최신 AI 분야 분류
    CATEGORIES = {
        # === LLM & 추론 ===
        "LLM & Reasoning": {
            "keywords": ["large language model", "llm", "gpt-4", "claude", "llama", "gemini",
                        "chain-of-thought", "reasoning", "in-context learning", "prompting",
                        "instruction tuning", "chatgpt", "few-shot", "zero-shot"],
            "color": "#8b5cf6",  # Purple
            "icon": "🧠"
        },
        "AI Agents": {
            "keywords": ["ai agent", "autonomous agent", "tool use", "function calling",
                        "multi-agent", "agent framework", "agentic", "planning agent",
                        "autogpt", "langchain", "react agent", "tool learning"],
            "color": "#f59e0b",  # Amber
            "icon": "🤖"
        },
        "Code Generation": {
            "keywords": ["code generation", "code synthesis", "program synthesis", "copilot",
                        "code llm", "automated programming", "code completion", "codex",
                        "code review", "debugging", "software engineering"],
            "color": "#10b981",  # Emerald
            "icon": "💻"
        },
        "RAG & Knowledge": {
            "keywords": ["retrieval augmented", "rag", "knowledge retrieval", "dense retrieval",
                        "vector database", "knowledge base", "embedding retrieval", "semantic search",
                        "question answering", "document understanding"],
            "color": "#06b6d4",  # Cyan
            "icon": "📚"
        },
        # === 비전 & 멀티모달 ===
        "Computer Vision": {
            "keywords": ["computer vision", "object detection", "image segmentation", "image classification",
                        "visual recognition", "vit", "cnn", "yolo", "resnet", "imagenet",
                        "pose estimation", "scene understanding"],
            "color": "#3b82f6",  # Blue
            "icon": "👁️"
        },
        "Vision-Language": {
            "keywords": ["vision-language", "vlm", "gpt-4v", "multimodal llm", "clip",
                        "image-text", "visual question answering", "image captioning",
                        "visual instruction", "llava", "gemini vision"],
            "color": "#f43f5e",  # Rose
            "icon": "🔗"
        },
        "Video & World Models": {
            "keywords": ["video generation", "world model", "sora", "video understanding",
                        "temporal modeling", "video prediction", "spatiotemporal",
                        "action recognition", "video synthesis"],
            "color": "#ec4899",  # Pink
            "icon": "🎬"
        },
        "3D & Spatial": {
            "keywords": ["3d reconstruction", "nerf", "gaussian splatting", "3d generation",
                        "point cloud", "depth estimation", "3d vision", "spatial ai",
                        "mesh", "volumetric", "3d object"],
            "color": "#14b8a6",  # Teal
            "icon": "🌐"
        },
        # === 생성 모델 ===
        "Image Generation": {
            "keywords": ["diffusion model", "image generation", "text-to-image", "stable diffusion",
                        "dall-e", "midjourney", "image synthesis", "generative model",
                        "gan", "vae", "controlnet", "lora"],
            "color": "#a855f7",  # Violet
            "icon": "🎨"
        },
        "Audio & Speech": {
            "keywords": ["text-to-speech", "tts", "speech recognition", "asr", "audio generation",
                        "voice synthesis", "speech synthesis", "audio llm", "whisper",
                        "music generation", "voice cloning"],
            "color": "#84cc16",  # Lime
            "icon": "🎵"
        },
        # === 학습 & 최적화 ===
        "Reinforcement Learning": {
            "keywords": ["reinforcement learning", "rl", "rlhf", "policy optimization",
                        "reward model", "ppo", "decision making", "offline rl",
                        "q-learning", "dqn", "game playing"],
            "color": "#eab308",  # Yellow
            "icon": "🎮"
        },
        "Efficient AI": {
            "keywords": ["model compression", "quantization", "pruning", "distillation",
                        "efficient inference", "lightweight model", "edge ai", "peft", "lora",
                        "qlora", "flash attention", "mixture of experts", "moe"],
            "color": "#22c55e",  # Green
            "icon": "⚡"
        },
        # === 응용 & 안전 ===
        "Robotics": {
            "keywords": ["robotics", "robot learning", "manipulation", "navigation",
                        "embodied ai", "robot control", "autonomous robot", "locomotion",
                        "dexterous", "grasping"],
            "color": "#f97316",  # Orange
            "icon": "🦾"
        },
        "Scientific AI": {
            "keywords": ["ai for science", "alphafold", "protein structure", "drug discovery",
                        "molecular generation", "scientific discovery", "chemistry ai",
                        "materials science", "biology ai", "physics simulation"],
            "color": "#0ea5e9",  # Sky
            "icon": "🔬"
        },
        "AI Safety": {
            "keywords": ["ai safety", "alignment", "red teaming", "jailbreak",
                        "constitutional ai", "interpretability", "explainable ai", "fairness",
                        "bias", "robustness", "adversarial"],
            "color": "#ef4444",  # Red
            "icon": "🛡️"
        },
        "Other": {
            "keywords": [],  # 분류되지 않은 논문
            "color": "#6b7280",  # Gray
            "icon": "📄"
        }
    }

    # field 코드 → 카테고리명 매핑 (검색 시 저장된 field와 매칭)
    FIELD_TO_CATEGORY = {
        "llm_reasoning": "LLM & Reasoning",
        "ai_agents": "AI Agents",
        "code_generation": "Code Generation",
        "rag_knowledge": "RAG & Knowledge",
        "computer_vision": "Computer Vision",
        "vision_language": "Vision-Language",
        "video_world": "Video & World Models",
        "3d_spatial": "3D & Spatial",
        "image_generation": "Image Generation",
        "audio_speech": "Audio & Speech",
        "reinforcement_learning": "Reinforcement Learning",
        "efficient_ai": "Efficient AI",
        "robotics": "Robotics",
        "scientific_ai": "Scientific AI",
        "ai_safety": "AI Safety",
    }

    # 캐싱 변수
    _cache = {
        'papers_hash': None,
        'categorized': None,
        'stats': None,
        'paper_categories': {}  # paper_id -> category 매핑
    }

    @classmethod
    def _get_papers_hash(cls, papers: list) -> str:
        """논문 리스트의 해시값 계산 (변경 감지용)"""
        return str(len(papers)) + "_" + str(sum(hash(p.get('title', '')) for p in papers[:10]))

    @classmethod
    def invalidate_cache(cls):
        """캐시 무효화"""
        cls._cache = {
            'papers_hash': None,
            'categorized': None,
            'stats': None,
            'paper_categories': {}
        }

    @classmethod
    def categorize_paper(cls, paper: dict) -> str:
        """논문을 가장 적합한 분야로 분류 (캐싱 적용)"""
        paper_id = f"{paper.get('title', '')}_{paper.get('year', '')}"

        # 캐시에 있으면 반환
        if paper_id in cls._cache['paper_categories']:
            return cls._cache['paper_categories'][paper_id]

        # 1. papers.json의 field 속성 우선 사용 (검색 시 저장된 분야)
        field = paper.get('field', '')
        if field:
            # field 코드를 카테고리명으로 변환
            category = cls.FIELD_TO_CATEGORY.get(field)
            if category and category in cls.CATEGORIES:
                cls._cache['paper_categories'][paper_id] = category
                return category
            # field가 이미 카테고리명인 경우
            if field in cls.CATEGORIES:
                cls._cache['paper_categories'][paper_id] = field
                return field

        # 2. 키워드 매칭으로 분류
        title = (paper.get('title') or '').lower()
        abstract = (paper.get('abstract') or '').lower()
        combined = title + ' ' + abstract

        scores = {}
        for category, info in cls.CATEGORIES.items():
            if category == "Other":
                continue  # Other는 기본값이므로 점수 계산에서 제외
            score = sum(1 for kw in info['keywords'] if kw in combined)
            if score > 0:
                scores[category] = score

        category = max(scores, key=scores.get) if scores else "Other"

        # 캐시에 저장
        cls._cache['paper_categories'][paper_id] = category
        return category
    
    @classmethod
    def categorize_all(cls, papers: list) -> dict:
        """모든 논문을 분야별로 분류하여 반환 (캐싱 적용)"""
        papers_hash = cls._get_papers_hash(papers)

        # 캐시 히트 - 즉시 반환
        if cls._cache['papers_hash'] == papers_hash and cls._cache['categorized']:
            return cls._cache['categorized']

        categorized = {cat: [] for cat in cls.CATEGORIES}
        categorized["Other"] = []

        for i, paper in enumerate(papers):
            category = cls.categorize_paper(paper)
            categorized[category].append((i, paper))

        # 각 분야별로 중요도 순 정렬
        for category in categorized:
            categorized[category].sort(
                key=lambda x: x[1].get('importance_score', 0),
                reverse=True
            )

        # 캐시 저장
        cls._cache['papers_hash'] = papers_hash
        cls._cache['categorized'] = categorized
        return categorized
    
    @classmethod
    def get_top_recommendations(cls, papers: list, n: int = None, exclude_reviewed: list = None) -> list:
        """리뷰할 가치가 높은 논문 추천 (n=None이면 전체 반환)"""
        exclude_reviewed = exclude_reviewed or []

        recommendations = []
        for i, paper in enumerate(papers):
            paper_id = f"{paper.get('title', '')}_{paper.get('year', '')}"
            if paper_id in exclude_reviewed:
                continue

            # 추천 점수 계산 (중요도 + 인용수 + 최신성)
            importance = paper.get('importance_score') or 50
            citations = min((paper.get('citations') or 0) / 1000, 100)  # 정규화
            year = paper.get('year') or 2000
            recency = max(0, (year - 2000) * 2)  # 최신 논문 가산점

            score = importance * 0.5 + citations * 0.3 + recency * 0.2
            category = cls.categorize_paper(paper)

            recommendations.append({
                'index': i,
                'paper': paper,
                'category': category,
                'score': score
            })

        # 점수 순 정렬
        recommendations.sort(key=lambda x: x['score'], reverse=True)

        # n이 지정되면 상위 N개만, 아니면 전체 반환
        if n is not None:
            return recommendations[:n]
        return recommendations
    
    @classmethod
    def get_category_stats(cls, papers: list) -> dict:
        """분야별 통계 반환 (캐싱 적용)"""
        papers_hash = cls._get_papers_hash(papers)

        # 캐시 히트
        if cls._cache['papers_hash'] == papers_hash and cls._cache['stats']:
            return cls._cache['stats']

        categorized = cls.categorize_all(papers)
        stats = {}
        for category, paper_list in categorized.items():
            if paper_list:
                stats[category] = {
                    'count': len(paper_list),
                    'info': cls.CATEGORIES.get(category, {'color': '#6b7280', 'icon': '📄'})
                }

        # 캐시 저장
        cls._cache['stats'] = stats
        return stats


# ===== 상용 수준 스타일시트 =====
PROFESSIONAL_STYLESHEET = f"""
/* ===== 전역 스타일 ===== */
QMainWindow {{
    background-color: {Colors.BG_DARK};
}}

QWidget {{
    font-family: 'Segoe UI', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
    font-size: 13px;
    color: {Colors.TEXT_PRIMARY};
}}

/* ===== 메인 버튼 (Primary) ===== */
QPushButton {{
    background-color: {Colors.BG_ELEVATED};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 8px 16px;
    min-width: 70px;
    min-height: 28px;
    font-weight: 500;
    color: {Colors.TEXT_PRIMARY};
}}

QPushButton:hover {{
    background-color: {Colors.BG_HOVER};
    border-color: {Colors.BORDER_LIGHT};
}}

QPushButton:pressed {{
    background-color: {Colors.BG_CARD};
}}

QPushButton:disabled {{
    background-color: {Colors.BG_MAIN};
    color: {Colors.TEXT_DISABLED};
    border-color: {Colors.BORDER};
}}

/* Primary 버튼 */
QPushButton#primaryBtn {{
    background-color: {Colors.PRIMARY};
    border: none;
    color: white;
    font-weight: 600;
}}

QPushButton#primaryBtn:hover {{
    background-color: {Colors.PRIMARY_LIGHT};
}}

QPushButton#primaryBtn:pressed {{
    background-color: {Colors.PRIMARY_DARK};
}}

QPushButton#primaryBtn:disabled {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT_DISABLED};
}}

/* Success 버튼 */
QPushButton#successBtn {{
    background-color: {Colors.SUCCESS};
    border: none;
    color: white;
    font-weight: 600;
}}

QPushButton#successBtn:hover {{
    background-color: {Colors.SUCCESS_DARK};
}}

/* Danger 버튼 */
QPushButton#dangerBtn {{
    background-color: {Colors.ERROR};
    border: none;
    color: white;
    font-weight: 600;
}}

QPushButton#dangerBtn:hover {{
    background-color: {Colors.ERROR_DARK};
}}

/* 작은 아이콘 버튼 */
QPushButton#iconBtn {{
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    padding: 0;
    border-radius: 6px;
    font-size: 14px;
}}

/* ===== 테이블 ===== */
QTableWidget {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    gridline-color: {Colors.BORDER};
    selection-background-color: {Colors.PRIMARY};
    selection-color: white;
}}

QTableWidget::item {{
    padding: 8px 12px;
    border-bottom: 1px solid {Colors.BORDER};
}}

QTableWidget::item:selected {{
    background-color: rgba(90, 159, 255, 0.3);
    color: {Colors.TEXT_PRIMARY};
}}

QTableWidget::item:hover {{
    background-color: {Colors.BG_HOVER};
}}

QHeaderView::section {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT_SECONDARY};
    padding: 10px 12px;
    border: none;
    border-bottom: 2px solid {Colors.PRIMARY};
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* ===== 입력 필드 ===== */
QLineEdit {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 8px 12px;
    color: {Colors.TEXT_PRIMARY};
    selection-background-color: {Colors.PRIMARY};
}}

QLineEdit:focus {{
    border-color: {Colors.BORDER_FOCUS};
    background-color: {Colors.BG_ELEVATED};
}}

QLineEdit:disabled {{
    background-color: {Colors.BG_MAIN};
    color: {Colors.TEXT_DISABLED};
}}

QLineEdit::placeholder {{
    color: {Colors.TEXT_MUTED};
}}

/* ===== 콤보박스 ===== */
QComboBox {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 8px 12px;
    min-width: 100px;
    color: {Colors.TEXT_PRIMARY};
}}

QComboBox:hover {{
    border-color: {Colors.BORDER_LIGHT};
}}

QComboBox:focus {{
    border-color: {Colors.BORDER_FOCUS};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid {Colors.TEXT_SECONDARY};
    margin-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {Colors.BG_ELEVATED};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    selection-background-color: {Colors.PRIMARY};
    outline: none;
}}

/* ===== 체크박스 ===== */
QCheckBox {{
    spacing: 8px;
    color: {Colors.TEXT_PRIMARY};
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid {Colors.BORDER_LIGHT};
    background-color: {Colors.BG_CARD};
}}

QCheckBox::indicator:checked {{
    background-color: {Colors.PRIMARY};
    border-color: {Colors.PRIMARY};
}}

QCheckBox::indicator:hover {{
    border-color: {Colors.PRIMARY_LIGHT};
}}

/* ===== 그룹박스 ===== */
QGroupBox {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 10px;
    margin-top: 16px;
    padding-top: 20px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 16px;
    padding: 4px 12px;
    color: {Colors.TEXT_PRIMARY};
    background-color: {Colors.BG_CARD};
    border-radius: 4px;
}}

/* ===== 진행률 바 ===== */
QProgressBar {{
    background-color: {Colors.BG_CARD};
    border: none;
    border-radius: 6px;
    height: 8px;
    text-align: center;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {Colors.PRIMARY_DARK}, stop:1 {Colors.PRIMARY_LIGHT});
    border-radius: 6px;
}}

/* ===== 탭 위젯 ===== */
QTabWidget::pane {{
    background-color: {Colors.BG_MAIN};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    border-top-left-radius: 0px;
    margin-top: -1px;
}}

QTabBar::tab {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-bottom: none;
    padding: 10px 24px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    color: {Colors.TEXT_SECONDARY};
    font-weight: 500;
}}

QTabBar::tab:selected {{
    background-color: {Colors.BG_MAIN};
    color: {Colors.PRIMARY};
    border-bottom: 2px solid {Colors.PRIMARY};
}}

QTabBar::tab:hover:!selected {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT_PRIMARY};
}}

/* ===== 텍스트 에디터 ===== */
QTextEdit {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    padding: 12px;
    color: {Colors.TEXT_PRIMARY};
    selection-background-color: {Colors.PRIMARY};
}}

QTextEdit:focus {{
    border-color: {Colors.BORDER_FOCUS};
}}

/* ===== 스크롤바 ===== */
QScrollBar:vertical {{
    background-color: {Colors.BG_MAIN};
    width: 10px;
    border-radius: 5px;
    margin: 2px;
}}

QScrollBar::handle:vertical {{
    background-color: {Colors.BORDER_LIGHT};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {Colors.TEXT_MUTED};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: {Colors.BG_MAIN};
    height: 10px;
    border-radius: 5px;
    margin: 2px;
}}

QScrollBar::handle:horizontal {{
    background-color: {Colors.BORDER_LIGHT};
    border-radius: 5px;
    min-width: 30px;
}}

/* ===== 스플리터 ===== */
QSplitter::handle {{
    background-color: {Colors.BORDER};
    width: 2px;
}}

QSplitter::handle:hover {{
    background-color: {Colors.PRIMARY};
}}

/* ===== 상태바 ===== */
QStatusBar {{
    background-color: {Colors.BG_ELEVATED};
    border-top: 1px solid {Colors.BORDER};
    color: {Colors.TEXT_SECONDARY};
    padding: 4px 12px;
}}

/* ===== 레이블 ===== */
QLabel {{
    color: {Colors.TEXT_PRIMARY};
}}

QLabel#headerTitle {{
    font-size: 20px;
    font-weight: 700;
    color: {Colors.TEXT_PRIMARY};
}}

QLabel#headerSubtitle {{
    font-size: 12px;
    color: {Colors.TEXT_MUTED};
}}

QLabel#sectionTitle {{
    font-size: 14px;
    font-weight: 600;
    color: {Colors.TEXT_PRIMARY};
}}

QLabel#statLabel {{
    font-size: 24px;
    font-weight: 700;
    color: {Colors.PRIMARY};
}}

QLabel#mutedLabel {{
    color: {Colors.TEXT_MUTED};
    font-size: 11px;
}}

/* ===== 메뉴 ===== */
QMenu {{
    background-color: {Colors.BG_ELEVATED};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    padding: 8px 0;
}}

QMenu::item {{
    padding: 8px 24px;
    color: {Colors.TEXT_PRIMARY};
}}

QMenu::item:selected {{
    background-color: {Colors.PRIMARY};
    color: white;
}}

QMenu::separator {{
    height: 1px;
    background-color: {Colors.BORDER};
    margin: 4px 12px;
}}

/* ===== 툴팁 ===== */
QToolTip {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12px;
}}

/* ===== 메시지 박스 ===== */
QMessageBox {{
    background-color: {Colors.BG_CARD};
}}

QMessageBox QLabel {{
    color: {Colors.TEXT_PRIMARY};
}}
"""

# WebEngine 임포트 시도
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    WEB_ENGINE_AVAILABLE = False
    print("PyQtWebEngine not available. Paper preview will open in browser.")

# 프로젝트 루트 경로
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.main import TistoryAutoPoster
from src.data.paper_manager import PaperManager
from src.client.claude_client import ClaudeClient
from src.data.paper_searcher import PaperSearcher


# 검색 기록 파일
HISTORY_FILE = project_root / "data" / "search_history.json"


def load_search_history():
    """검색 기록 로드"""
    try:
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return []


def save_search_history(history):
    """검색 기록 저장"""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history[-50:], f, ensure_ascii=False, indent=2)
    except:
        pass


class PaperPreviewDialog(QDialog):
    """논문 미리보기 다이얼로그"""
    def __init__(self, parent, paper):
        super().__init__(parent)
        self.paper = paper
        self.setWindowTitle(f"논문 미리보기: {paper.get('title', 'N/A')[:50]}...")
        self.setGeometry(150, 150, 1000, 700)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 논문 정보 표시
        info_label = QLabel()
        title = self.paper.get('title', 'N/A')
        url = self.paper.get('url', '')
        info_html = f"<b>{title}</b>"
        if url:
            info_html += f"<br><a href='{url}'>{url}</a>"
        info_label.setText(info_html)
        info_label.setOpenExternalLinks(True)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # 웹뷰 또는 안내 메시지
        url = self.paper.get('url', '')

        if WEB_ENGINE_AVAILABLE and url:
            # arXiv URL 처리
            if 'arxiv.org/abs/' in url:
                # abs를 pdf로 변환하지 않고 abstract 페이지 표시
                pass

            self.web_view = QWebEngineView()
            self.web_view.setUrl(QUrl(url))
            layout.addWidget(self.web_view)
        else:
            # 웹엔진 없으면 안내 메시지
            msg = QLabel(
                "<h3>논문 미리보기</h3>"
                "<p>PyQtWebEngine이 설치되지 않았거나 URL이 없습니다.</p>"
                "<p>아래 버튼으로 브라우저에서 열 수 있습니다.</p>"
            )
            msg.setAlignment(Qt.AlignCenter)
            layout.addWidget(msg)

        # 버튼
        btn_layout = QHBoxLayout()

        if url:
            open_btn = QPushButton("🌐 브라우저에서 열기")
            open_btn.clicked.connect(lambda: webbrowser.open(url))
            btn_layout.addWidget(open_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)


class PublishWorker(QThread):
    """기존 논문 발행 작업을 백그라운드에서 실행"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)  # 진행 상황 시그널

    def __init__(self, poster, paper_index, save_md_only):
        super().__init__()
        self.poster = poster
        self.paper_index = paper_index
        self.save_md_only = save_md_only

    def run(self):
        try:
            result = self.poster.create_post(
                paper_index=self.paper_index,
                save_md_only=self.save_md_only,
                progress_callback=self.progress.emit
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class SearchWorker(QThread):
    """논문 검색 작업을 백그라운드에서 실행"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)  # 진행 상황 시그널

    def __init__(self, poster, paper_title):
        super().__init__()
        self.poster = poster
        self.paper_title = paper_title

    def run(self):
        try:
            self.progress.emit("논문 정보 검색 중...")
            result = self.poster.search_paper_info(self.paper_title)
            self.progress.emit("검색 완료!")
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ExternalPublishWorker(QThread):
    """외부 논문 발행 작업을 백그라운드에서 실행"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)  # 진행 상황 시그널

    def __init__(self, poster, paper, save_md_only):
        super().__init__()
        self.poster = poster
        self.paper = paper
        self.save_md_only = save_md_only

    def run(self):
        try:
            result = self.poster.create_post_from_paper(
                paper=self.paper,
                save_md_only=self.save_md_only,
                progress_callback=self.progress.emit
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class BatchPublishWorker(QThread):
    """배치 발행 작업을 백그라운드에서 실행"""
    paper_started = pyqtSignal(int, str)      # (queue_index, title) - 시작 알림
    paper_progress = pyqtSignal(int, str)     # (queue_index, message) - 진행 상황
    paper_completed = pyqtSignal(int, dict)   # (queue_index, result) - 완료
    paper_failed = pyqtSignal(int, str)       # (queue_index, error) - 실패
    queue_progress = pyqtSignal(int, int)     # (current, total) - 전체 진행률
    all_completed = pyqtSignal(list)          # [results] - 전체 완료

    def __init__(self, poster, paper_indices, save_md_only=False):
        super().__init__()
        self.poster = poster
        self.paper_indices = paper_indices  # [(queue_idx, paper_idx, paper), ...]
        self.save_md_only = save_md_only  # MD만 생성 (발행 없이)
        self.is_paused = False
        self.is_stopped = False

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def stop(self):
        self.is_stopped = True
        self.is_paused = False

    def run(self):
        results = []
        total = len(self.paper_indices)

        for i, (queue_idx, paper_idx, paper) in enumerate(self.paper_indices):
            # 일시정지 대기
            while self.is_paused and not self.is_stopped:
                self.msleep(100)

            if self.is_stopped:
                break

            title = paper.get('title', 'Unknown')[:50]
            self.paper_started.emit(queue_idx, title)
            self.queue_progress.emit(i + 1, total)

            try:
                def progress_callback(msg):
                    self.paper_progress.emit(queue_idx, msg)

                if paper_idx is not None:
                    # 기존 논문
                    result = self.poster.create_post(
                        paper_index=paper_idx,
                        save_md_only=self.save_md_only,
                        progress_callback=progress_callback
                    )
                else:
                    # 외부 논문
                    result = self.poster.create_post_from_paper(
                        paper=paper,
                        save_md_only=self.save_md_only,
                        progress_callback=progress_callback
                    )

                results.append(result)
                self.paper_completed.emit(queue_idx, result)

            except Exception as e:
                self.paper_failed.emit(queue_idx, str(e))
                results.append({'success': False, 'error': str(e), 'title': title})

        self.all_completed.emit(results)


class PDFDownloadWorker(QThread):
    """PDF 다운로드 작업을 백그라운드에서 실행"""
    finished = pyqtSignal(str)  # 저장된 파일 경로
    error = pyqtSignal(str)
    progress = pyqtSignal(int)  # 다운로드 진행률

    def __init__(self, paper, save_dir):
        super().__init__()
        self.paper = paper
        self.save_dir = save_dir

    def get_pdf_url(self, url):
        """논문 URL에서 PDF URL 추출"""
        if not url:
            return None

        # arXiv URL 처리
        if 'arxiv.org' in url:
            # abs URL을 pdf URL로 변환
            # https://arxiv.org/abs/2103.00020 -> https://arxiv.org/pdf/2103.00020.pdf
            arxiv_id = None
            if '/abs/' in url:
                arxiv_id = url.split('/abs/')[-1].split('?')[0]
            elif '/pdf/' in url:
                arxiv_id = url.split('/pdf/')[-1].replace('.pdf', '')

            if arxiv_id:
                return f"https://arxiv.org/pdf/{arxiv_id}.pdf"

        # 이미 PDF URL인 경우
        if url.lower().endswith('.pdf'):
            return url

        return None

    def sanitize_filename(self, name):
        """파일명에 사용할 수 없는 문자 제거"""
        # 특수문자 제거
        name = re.sub(r'[\\/*?:"<>|]', '', name)
        # 공백을 언더스코어로
        name = name.replace(' ', '_')
        # 너무 긴 파일명 제한
        if len(name) > 100:
            name = name[:100]
        return name

    def run(self):
        try:
            url = self.paper.get('url', '')
            pdf_url = self.get_pdf_url(url)

            if not pdf_url:
                self.error.emit(f"PDF URL을 찾을 수 없습니다.\n현재 URL: {url}\n\narXiv 논문만 PDF 다운로드를 지원합니다.")
                return

            # 파일명 생성
            title = self.paper.get('title', 'unknown')
            year = self.paper.get('year', '')
            filename = self.sanitize_filename(f"{title}_{year}") + ".pdf"
            save_path = Path(self.save_dir) / filename

            # 이미 존재하면 스킵
            if save_path.exists():
                self.finished.emit(str(save_path))
                return

            # PDF 다운로드
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            response = requests.get(pdf_url, headers=headers, stream=True, timeout=60)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            # 저장 디렉토리 생성
            save_path.parent.mkdir(parents=True, exist_ok=True)

            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            self.progress.emit(progress)

            self.finished.emit(str(save_path))

        except requests.exceptions.RequestException as e:
            self.error.emit(f"다운로드 오류: {e}")
        except Exception as e:
            self.error.emit(f"오류: {e}")


class CategorySearchWorker(QThread):
    """분야별 최신 논문 검색 작업을 백그라운드에서 실행 (다양한 소스 활용)"""
    finished = pyqtSignal(list)  # 검색된 논문 리스트
    error = pyqtSignal(str)
    progress = pyqtSignal(str)  # 진행 상황
    source_info = pyqtSignal(str)  # 사용된 소스 정보

    def __init__(self, paper_searcher: PaperSearcher, category: str, keywords: list,
                 count: int = 5, previous_titles: list = None):
        super().__init__()
        self.paper_searcher = paper_searcher
        self.category = category
        self.keywords = keywords
        self.count = count
        self.previous_titles = previous_titles or []

    def run(self):
        try:
            self.progress.emit(f"🔍 {self.category} 분야 검색 중 (다양한 소스)...")

            # PaperSearcher로 다양한 소스에서 검색
            papers = self.paper_searcher.get_diverse_papers(
                category=self.category,
                keywords=self.keywords,
                count=self.count,
                previous_titles=self.previous_titles
            )

            if papers:
                # 사용된 소스 정보 수집
                sources_used = set()
                for paper in papers:
                    if paper.get("source"):
                        sources_used.add(paper["source"])

                source_str = ", ".join(sources_used) if sources_used else "Unknown"
                self.source_info.emit(f"📚 소스: {source_str}")
                self.progress.emit(f"✅ {len(papers)}개 논문 발견!")
            else:
                self.progress.emit("검색 결과 없음")

            self.finished.emit(papers if papers else [])

        except Exception as e:
            self.error.emit(f"검색 오류: {str(e)}")


class PaperPublishGUI(QMainWindow):
    """전문적인 논문 리뷰 발행 GUI"""

    VERSION = "3.0"

    def __init__(self):
        super().__init__()
        self.poster = None
        self.papers = []
        self.selected_index = None
        self.searched_paper = None
        self.last_result = None
        self.worker = None
        self.search_worker = None
        self.external_worker = None
        self.pdf_worker = None
        self.batch_worker = None
        self.category_search_worker = None
        self.searched_papers = []  # 검색 결과 저장
        self.is_lucky_search = False  # Lucky 검색 플래그
        self.claude_client = None  # Claude 클라이언트 (쿠키 없이 사용 가능)
        self.paper_searcher = PaperSearcher()  # 다양한 논문 소스 검색기
        self.search_history = load_search_history()

        # 대기열 관련 변수
        self.publish_queue = []  # [(queue_idx, paper_idx, paper), ...]
        self.queue_counter = 0
        self.is_batch_running = False
        self.is_batch_paused = False
        self.batch_start_time = None
        self.avg_publish_time = 120  # 평균 발행 시간 (초)

        self.init_ui()
        self.setup_shortcuts()
        self.apply_professional_style()
        self.load_papers()

    def closeEvent(self, event):
        """애플리케이션 종료 시 모든 워커 스레드 정리"""
        workers = [
            self.category_search_worker,
            self.search_worker,
            self.external_worker,
            self.pdf_worker,
            self.batch_worker
        ]
        for worker in workers:
            if worker is not None and worker.isRunning():
                worker.quit()
                worker.wait(2000)  # 최대 2초 대기
        event.accept()

    def init_ui(self):
        self.setWindowTitle(f"Paper Review Publisher Pro v{self.VERSION}")
        self.setGeometry(100, 100, 1450, 950)
        self.setMinimumSize(1200, 800)

        # 메인 위젯
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(16, 16, 16, 8)
        layout.setSpacing(12)

        # ===== 헤더 영역 =====
        header_widget = QWidget()
        header_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_CARD};
                border-radius: 12px;
            }}
        """)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 16, 20, 16)

        # 왼쪽: 타이틀 + 서브타이틀
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        title_label = QLabel("Paper Review Publisher")
        title_label.setObjectName("headerTitle")
        title_layout.addWidget(title_label)

        subtitle_label = QLabel(f"v{self.VERSION}  |  AI-Powered Paper Review Automation")
        subtitle_label.setObjectName("headerSubtitle")
        title_layout.addWidget(subtitle_label)

        header_layout.addLayout(title_layout)

        # 중앙: 통계
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(32)

        # 진행률 통계
        progress_stat = QVBoxLayout()
        progress_stat.setSpacing(0)
        self.stat_reviewed = QLabel("0")
        self.stat_reviewed.setObjectName("statLabel")
        self.stat_reviewed.setAlignment(Qt.AlignCenter)
        progress_stat.addWidget(self.stat_reviewed)
        stat_label = QLabel("리뷰 완료")
        stat_label.setObjectName("mutedLabel")
        stat_label.setAlignment(Qt.AlignCenter)
        progress_stat.addWidget(stat_label)
        stats_layout.addLayout(progress_stat)

        # 전체 논문 수
        total_stat = QVBoxLayout()
        total_stat.setSpacing(0)
        self.stat_total = QLabel("0")
        self.stat_total.setObjectName("statLabel")
        self.stat_total.setAlignment(Qt.AlignCenter)
        total_stat.addWidget(self.stat_total)
        total_label = QLabel("전체 논문")
        total_label.setObjectName("mutedLabel")
        total_label.setAlignment(Qt.AlignCenter)
        total_stat.addWidget(total_label)
        stats_layout.addLayout(total_stat)

        # 진행률 바
        progress_container = QVBoxLayout()
        progress_container.setSpacing(4)
        self.progress_percent_label = QLabel("0%")
        self.progress_percent_label.setAlignment(Qt.AlignCenter)
        self.progress_percent_label.setStyleSheet(f"color: {Colors.PRIMARY}; font-weight: 600; font-size: 14px;")
        progress_container.addWidget(self.progress_percent_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(180)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        progress_container.addWidget(self.progress_bar)
        stats_layout.addLayout(progress_container)

        header_layout.addStretch()
        header_layout.addLayout(stats_layout)
        header_layout.addStretch()

        # 오른쪽: 도구 버튼들
        tools_layout = QHBoxLayout()
        tools_layout.setSpacing(8)

        self.refresh_btn = QPushButton("R")
        self.refresh_btn.setObjectName("iconBtn")
        self.refresh_btn.clicked.connect(self.load_papers)
        self.refresh_btn.setToolTip("새로고침 (Ctrl+R)")
        tools_layout.addWidget(self.refresh_btn)

        self.output_btn = QPushButton("F")
        self.output_btn.setObjectName("iconBtn")
        self.output_btn.clicked.connect(self.open_output)
        self.output_btn.setToolTip("출력 폴더 (Ctrl+O)")
        tools_layout.addWidget(self.output_btn)

        self.pdf_folder_btn = QPushButton("P")
        self.pdf_folder_btn.setObjectName("iconBtn")
        self.pdf_folder_btn.clicked.connect(self.open_pdf_folder)
        self.pdf_folder_btn.setToolTip("PDF 폴더 열기")
        tools_layout.addWidget(self.pdf_folder_btn)

        self.help_btn = QPushButton("?")
        self.help_btn.setObjectName("iconBtn")
        self.help_btn.clicked.connect(self.show_help)
        self.help_btn.setToolTip("도움말")
        tools_layout.addWidget(self.help_btn)

        header_layout.addLayout(tools_layout)
        layout.addWidget(header_widget)

        # ===== 메인 콘텐츠: 좌측(논문 뷰) + 우측(발행 사이드바) =====
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setHandleWidth(2)

        # ===== 좌측: 논문 뷰 (탭 위젯) =====
        self.tab_widget = QTabWidget()

        # 탭 1: 기존 논문 리스트 (대기열 제외)
        self.create_existing_papers_tab()

        # 탭 2: 논문 추천
        self.create_recommendation_tab()

        # 탭 3: 새 논문 검색
        self.create_search_tab()

        main_splitter.addWidget(self.tab_widget)

        # ===== 우측: 발행 사이드바 (고정) =====
        sidebar_widget = QWidget()
        sidebar_widget.setStyleSheet(f"background-color: {Colors.BG_CARD}; border-radius: 10px;")
        sidebar_widget.setMinimumWidth(280)
        sidebar_widget.setMaximumWidth(350)
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.setSpacing(12)

        # --- 발행 대기열 ---
        queue_title = QLabel("📋 발행 대기열")
        queue_title.setObjectName("sectionTitle")
        sidebar_layout.addWidget(queue_title)

        # 대기열 상태
        queue_status_layout = QHBoxLayout()
        self.queue_progress_label = QLabel("0/0 대기 중")
        self.queue_progress_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        queue_status_layout.addWidget(self.queue_progress_label)
        queue_status_layout.addStretch()
        self.estimated_time_label = QLabel("")
        self.estimated_time_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10px;")
        queue_status_layout.addWidget(self.estimated_time_label)
        sidebar_layout.addLayout(queue_status_layout)

        # 대기열 테이블
        self.sidebar_queue_table = QTableWidget()
        self.sidebar_queue_table.setColumnCount(3)
        self.sidebar_queue_table.setHorizontalHeaderLabels(["#", "제목", "상태"])
        self.sidebar_queue_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.sidebar_queue_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sidebar_queue_table.verticalHeader().setVisible(False)
        self.sidebar_queue_table.setMaximumHeight(200)
        sidebar_layout.addWidget(self.sidebar_queue_table)

        # 대기열 버튼
        queue_btn_layout = QHBoxLayout()
        queue_btn_layout.setSpacing(6)

        self.sidebar_publish_btn = QPushButton("▶ 전체 발행")
        self.sidebar_publish_btn.setObjectName("successBtn")
        self.sidebar_publish_btn.clicked.connect(self.start_batch_publish)
        queue_btn_layout.addWidget(self.sidebar_publish_btn)

        self.sidebar_pause_btn = QPushButton("⏸")
        self.sidebar_pause_btn.setFixedWidth(36)
        self.sidebar_pause_btn.clicked.connect(self.toggle_pause)
        self.sidebar_pause_btn.setEnabled(False)
        queue_btn_layout.addWidget(self.sidebar_pause_btn)

        self.sidebar_stop_btn = QPushButton("⏹")
        self.sidebar_stop_btn.setFixedWidth(36)
        self.sidebar_stop_btn.clicked.connect(self.stop_batch_publish)
        self.sidebar_stop_btn.setEnabled(False)
        self.sidebar_stop_btn.setStyleSheet(f"color: {Colors.ERROR};")
        queue_btn_layout.addWidget(self.sidebar_stop_btn)

        self.sidebar_clear_btn = QPushButton("🗑")
        self.sidebar_clear_btn.setFixedWidth(36)
        self.sidebar_clear_btn.clicked.connect(self.clear_queue)
        queue_btn_layout.addWidget(self.sidebar_clear_btn)

        sidebar_layout.addLayout(queue_btn_layout)

        # 기존 코드 호환성을 위한 참조
        self.queue_list = self.sidebar_queue_table
        self.batch_publish_btn = self.sidebar_publish_btn
        self.pause_btn = self.sidebar_pause_btn
        self.stop_batch_btn = self.sidebar_stop_btn

        # 구분선
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"background-color: {Colors.BORDER};")
        sidebar_layout.addWidget(separator)

        # --- 발행 결과 ---
        result_title = QLabel("📝 발행 결과")
        result_title.setObjectName("sectionTitle")
        sidebar_layout.addWidget(result_title)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("발행 결과가 여기에 표시됩니다...")
        sidebar_layout.addWidget(self.result_text, 1)

        self.open_url_btn = QPushButton("발행된 글 열기")
        self.open_url_btn.setObjectName("primaryBtn")
        self.open_url_btn.setEnabled(False)
        self.open_url_btn.clicked.connect(self.open_url)
        sidebar_layout.addWidget(self.open_url_btn)

        # 클립보드 복사 및 폴더 열기 버튼들
        copy_btn_layout = QHBoxLayout()
        self.copy_md_btn = QPushButton("📋 MD")
        self.copy_md_btn.setToolTip("마지막 발행된 MD 내용을 클립보드에 복사")
        self.copy_md_btn.clicked.connect(self.copy_last_md_to_clipboard)
        copy_btn_layout.addWidget(self.copy_md_btn)

        self.copy_html_btn = QPushButton("🌐 HTML")
        self.copy_html_btn.setToolTip("MD를 HTML로 변환하여 클립보드에 복사")
        self.copy_html_btn.clicked.connect(self.copy_md_as_html)
        copy_btn_layout.addWidget(self.copy_html_btn)

        self.open_output_btn = QPushButton("📁 폴더")
        self.open_output_btn.setToolTip("출력 폴더 열기 (Ctrl+O)")
        self.open_output_btn.clicked.connect(self.open_output)
        copy_btn_layout.addWidget(self.open_output_btn)
        sidebar_layout.addLayout(copy_btn_layout)

        main_splitter.addWidget(sidebar_widget)
        main_splitter.setSizes([700, 300])  # 초기 비율

        layout.addWidget(main_splitter, 1)

        # ===== 상태바 =====
        status_bar = self.statusBar()
        status_bar.showMessage("Ready  |  Ctrl+P: 발행  |  Ctrl+R: 새로고침  |  Ctrl+O: 출력폴더  |  Ctrl+F: 검색")

    def setup_shortcuts(self):
        """단축키 설정"""
        QShortcut(QKeySequence("Ctrl+R"), self, self.load_papers)
        QShortcut(QKeySequence("Ctrl+O"), self, self.open_output)
        QShortcut(QKeySequence("Ctrl+P"), self, self.shortcut_publish)
        QShortcut(QKeySequence("Ctrl+F"), self, self.focus_search)
        QShortcut(QKeySequence("Ctrl+1"), self, lambda: self.tab_widget.setCurrentIndex(0))
        QShortcut(QKeySequence("Ctrl+2"), self, lambda: self.tab_widget.setCurrentIndex(1))
        QShortcut(QKeySequence("Return"), self.table, self.publish)

    def shortcut_publish(self):
        if self.tab_widget.currentIndex() == 0:
            self.publish()
        else:
            self.publish_external()

    def focus_search(self):
        if self.tab_widget.currentIndex() == 0:
            self.search_input.setFocus()
            self.search_input.selectAll()
        else:
            self.external_search_input.setFocus()
            self.external_search_input.selectAll()

    def apply_professional_style(self):
        """상용 프로그램 수준의 전문적인 스타일 적용"""
        # 팔레트 설정
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(Colors.BG_DARK))
        palette.setColor(QPalette.WindowText, QColor(Colors.TEXT_PRIMARY))
        palette.setColor(QPalette.Base, QColor(Colors.BG_CARD))
        palette.setColor(QPalette.AlternateBase, QColor(Colors.BG_ELEVATED))
        palette.setColor(QPalette.ToolTipBase, QColor(Colors.BG_ELEVATED))
        palette.setColor(QPalette.ToolTipText, QColor(Colors.TEXT_PRIMARY))
        palette.setColor(QPalette.Text, QColor(Colors.TEXT_PRIMARY))
        palette.setColor(QPalette.Button, QColor(Colors.BG_ELEVATED))
        palette.setColor(QPalette.ButtonText, QColor(Colors.TEXT_PRIMARY))
        palette.setColor(QPalette.BrightText, QColor(Colors.ERROR))
        palette.setColor(QPalette.Link, QColor(Colors.PRIMARY))
        palette.setColor(QPalette.Highlight, QColor(Colors.PRIMARY))
        palette.setColor(QPalette.HighlightedText, Qt.white)
        QApplication.instance().setPalette(palette)

        # 전문적인 스타일시트 적용
        self.setStyleSheet(PROFESSIONAL_STYLESHEET)

    def show_help(self):
        help_text = f"""
<h2 style="color: {Colors.PRIMARY};">Paper Review Publisher Pro v{self.VERSION}</h2>

<h3>논문 리스트 탭</h3>
<p>
- 체크박스로 여러 논문 선택 후 대기열에 추가<br>
- 클릭: 논문 선택 / 더블클릭: 논문 미리보기<br>
- 필터: 제목, 연도 범위, 인용수 최소값<br>
- 정렬: 제목순, 연도순, 인용수순<br>
- 빠른 선택: 랜덤, 인용수 최고, 최신 논문 자동 선택
</p>

<h3>대기열 발행</h3>
<p>
1. 체크박스로 논문 선택<br>
2. [+ 추가] 버튼으로 대기열에 추가<br>
3. [전체 발행] 버튼으로 순차 발행<br>
- 일시정지 (||) / 중지 (X) 가능<br>
- 단일 발행 중에도 대기열 추가 가능
</p>

<h3>새 논문 검색</h3>
<p>
- 논문 제목을 입력하면 Claude AI가 검색<br>
- 리스트에 없는 논문도 발행 가능
</p>

<h3>발행 시 자동 처리</h3>
<p>
- 마크다운(MD) 파일 자동 저장<br>
- arXiv 논문 PDF 자동 다운로드<br>
- 티스토리 자동 발행
</p>

<h3 style="color: {Colors.PRIMARY};">단축키</h3>
<table style="margin-left: 10px;">
<tr><td style="padding: 4px 16px 4px 0;"><b>Ctrl+P</b></td><td>발행하기</td></tr>
<tr><td style="padding: 4px 16px 4px 0;"><b>Ctrl+R</b></td><td>새로고침</td></tr>
<tr><td style="padding: 4px 16px 4px 0;"><b>Ctrl+O</b></td><td>출력 폴더 열기</td></tr>
<tr><td style="padding: 4px 16px 4px 0;"><b>Ctrl+F</b></td><td>검색창 포커스</td></tr>
<tr><td style="padding: 4px 16px 4px 0;"><b>Ctrl+1/2</b></td><td>탭 전환</td></tr>
</table>
"""
        QMessageBox.information(self, "도움말", help_text)

    def create_existing_papers_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # ===== 필터 영역 =====
        filter_widget = QWidget()
        filter_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_CARD};
                border-radius: 10px;
            }}
        """)
        filter_main_layout = QVBoxLayout(filter_widget)
        filter_main_layout.setContentsMargins(16, 14, 16, 14)
        filter_main_layout.setSpacing(12)

        # 첫 번째 줄: 검색 + 필터
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(12)

        # 검색 입력
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("논문 제목으로 검색... (Ctrl+F)")
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self.filter_papers)
        row1_layout.addWidget(self.search_input, 1)

        # 미리뷰 필터
        self.unreviewed_check = QCheckBox("미리뷰만 표시")
        self.unreviewed_check.setChecked(True)
        self.unreviewed_check.stateChanged.connect(self.filter_papers)
        row1_layout.addWidget(self.unreviewed_check)

        # 구분선
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setStyleSheet(f"background-color: {Colors.BORDER};")
        row1_layout.addWidget(separator)

        # 연도 필터
        row1_layout.addWidget(QLabel("연도:"))
        self.year_from = QLineEdit()
        self.year_from.setPlaceholderText("시작")
        self.year_from.setFixedWidth(65)
        self.year_from.textChanged.connect(self.filter_papers)
        row1_layout.addWidget(self.year_from)
        row1_layout.addWidget(QLabel("-"))
        self.year_to = QLineEdit()
        self.year_to.setPlaceholderText("끝")
        self.year_to.setFixedWidth(65)
        self.year_to.textChanged.connect(self.filter_papers)
        row1_layout.addWidget(self.year_to)

        # 인용수 필터
        row1_layout.addWidget(QLabel("인용수 ≥"))
        self.citation_min = QLineEdit()
        self.citation_min.setPlaceholderText("0")
        self.citation_min.setFixedWidth(65)
        self.citation_min.textChanged.connect(self.filter_papers)
        row1_layout.addWidget(self.citation_min)

        filter_main_layout.addLayout(row1_layout)

        # 두 번째 줄: 정렬 + 추천 + 통계
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(12)

        row2_layout.addWidget(QLabel("정렬:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "제목순", "연도 (최신)", "연도 (오래된)",
            "인용수 (높음)", "인용수 (낮음)",
            "상태 (미리뷰 우선)", "상태 (리뷰 우선)"
        ])
        self.sort_combo.setFixedWidth(150)
        self.sort_combo.currentIndexChanged.connect(self.filter_papers)
        row2_layout.addWidget(self.sort_combo)

        # 추천 기능
        self.recommend_combo = QComboBox()
        self.recommend_combo.addItems(["빠른 선택...", "랜덤 선택", "인용수 최고", "가장 최신"])
        self.recommend_combo.setFixedWidth(120)
        self.recommend_combo.currentIndexChanged.connect(self.on_recommend_select)
        row2_layout.addWidget(self.recommend_combo)

        row2_layout.addStretch()

        # 논문 수 표시
        self.table_count_label = QLabel("0개 논문")
        self.table_count_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-weight: 500;")
        row2_layout.addWidget(self.table_count_label)

        filter_main_layout.addLayout(row2_layout)
        layout.addWidget(filter_widget)

        # ===== 메인 영역: 테이블 + 대기열 (좌우 분할) =====
        splitter = QSplitter(Qt.Horizontal)

        # 왼쪽: 논문 테이블
        table_container = QWidget()
        table_container.setStyleSheet(f"background-color: {Colors.BG_CARD}; border-radius: 10px;")
        table_main_layout = QVBoxLayout(table_container)
        table_main_layout.setContentsMargins(12, 12, 12, 12)
        table_main_layout.setSpacing(8)

        # 테이블 헤더
        table_header = QHBoxLayout()
        self.select_all_check = QCheckBox("전체 선택")
        self.select_all_check.stateChanged.connect(self.toggle_select_all)
        table_header.addWidget(self.select_all_check)
        table_header.addStretch()
        table_main_layout.addLayout(table_header)

        # 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["", "#", "상태", "논문 제목", "년도", "인용"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.on_select)
        self.table.itemDoubleClicked.connect(self.show_paper_preview)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_table_context_menu)
        table_main_layout.addWidget(self.table)

        # 테이블 하단 버튼
        table_btn_layout = QHBoxLayout()
        table_btn_layout.setSpacing(8)

        self.add_to_queue_btn = QPushButton("📋 대기열 추가")
        self.add_to_queue_btn.clicked.connect(self.add_selected_to_queue)
        table_btn_layout.addWidget(self.add_to_queue_btn)

        table_btn_layout.addStretch()
        table_main_layout.addLayout(table_btn_layout)

        layout.addWidget(table_container, 1)

        # ===== 선택된 논문 정보 =====
        info_widget = QWidget()
        info_widget.setStyleSheet(f"background-color: {Colors.BG_CARD}; border-radius: 10px;")
        info_main_layout = QVBoxLayout(info_widget)
        info_main_layout.setContentsMargins(16, 12, 16, 12)
        info_main_layout.setSpacing(8)

        info_header = QHBoxLayout()
        info_title = QLabel("선택된 논문")
        info_title.setObjectName("sectionTitle")
        info_header.addWidget(info_title)
        info_header.addStretch()
        info_main_layout.addLayout(info_header)

        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(65)
        self.info_text.setPlaceholderText("논문을 선택하면 상세 정보가 표시됩니다...")
        info_main_layout.addWidget(self.info_text)

        # 하단 액션 버튼
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)

        self.preview_btn = QPushButton("미리보기")
        self.preview_btn.setEnabled(False)
        self.preview_btn.clicked.connect(self.show_selected_paper_preview)
        self.preview_btn.setMinimumHeight(42)
        action_layout.addWidget(self.preview_btn)

        self.publish_btn = QPushButton("발행하기")
        self.publish_btn.setObjectName("primaryBtn")
        self.publish_btn.setEnabled(False)
        self.publish_btn.clicked.connect(self.publish)
        self.publish_btn.setMinimumHeight(42)
        self.publish_btn.setToolTip("선택한 논문 발행 (Ctrl+P)")
        action_layout.addWidget(self.publish_btn)

        self.auto_btn = QPushButton("자동 선택 발행")
        self.auto_btn.clicked.connect(self.auto_publish)
        self.auto_btn.setMinimumHeight(42)
        self.auto_btn.setToolTip("다음 미리뷰 논문 자동 선택 후 발행")
        action_layout.addWidget(self.auto_btn)

        info_main_layout.addLayout(action_layout)
        layout.addWidget(info_widget)

        # 논문 리스트 탭은 논문 추천 탭과 통합되어 탭에 추가하지 않음
        # 위젯들은 다른 메서드에서 참조하므로 숨겨진 참조로 유지 (Qt 삭제 방지)
        self._hidden_papers_tab = tab
        # self.tab_widget.addTab(tab, "논문 리스트")

    def create_search_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # ===== 검색 영역 =====
        search_widget = QWidget()
        search_widget.setStyleSheet(f"background-color: {Colors.BG_CARD}; border-radius: 10px;")
        search_main_layout = QVBoxLayout(search_widget)
        search_main_layout.setContentsMargins(20, 16, 20, 16)
        search_main_layout.setSpacing(12)

        search_title = QLabel("새 논문 검색")
        search_title.setObjectName("sectionTitle")
        search_main_layout.addWidget(search_title)

        # 검색 입력
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)

        self.external_search_input = QLineEdit()
        self.external_search_input.setPlaceholderText("검색할 논문의 정확한 제목을 입력하세요...")
        self.external_search_input.returnPressed.connect(self.search_external_paper)
        self.external_search_input.setMinimumHeight(40)

        self.completer = QCompleter(self.search_history)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.external_search_input.setCompleter(self.completer)

        input_layout.addWidget(self.external_search_input, 1)

        self.search_btn = QPushButton("검색")
        self.search_btn.setObjectName("primaryBtn")
        self.search_btn.clicked.connect(self.search_external_paper)
        self.search_btn.setMinimumHeight(40)
        self.search_btn.setMinimumWidth(100)
        input_layout.addWidget(self.search_btn)

        search_main_layout.addLayout(input_layout)

        help_label = QLabel("Claude AI가 논문 정보를 검색합니다. 정확한 제목 입력을 권장합니다.")
        help_label.setObjectName("mutedLabel")
        search_main_layout.addWidget(help_label)

        layout.addWidget(search_widget)

        # ===== 검색 결과 =====
        result_widget = QWidget()
        result_widget.setStyleSheet(f"background-color: {Colors.BG_CARD}; border-radius: 10px;")
        result_main_layout = QVBoxLayout(result_widget)
        result_main_layout.setContentsMargins(20, 16, 20, 16)
        result_main_layout.setSpacing(12)

        result_header = QHBoxLayout()
        result_title = QLabel("검색 결과")
        result_title.setObjectName("sectionTitle")
        result_header.addWidget(result_title)
        result_header.addStretch()

        # 히스토리 관리 버튼
        self.clear_search_btn = QPushButton("초기화")
        self.clear_search_btn.clicked.connect(self.clear_search)
        result_header.addWidget(self.clear_search_btn)

        self.clear_history_btn = QPushButton("기록 삭제")
        self.clear_history_btn.clicked.connect(self.clear_history)
        result_header.addWidget(self.clear_history_btn)

        result_main_layout.addLayout(result_header)

        self.search_result_text = QTextEdit()
        self.search_result_text.setReadOnly(True)
        self.search_result_text.setPlaceholderText("검색 결과가 여기에 표시됩니다...")
        self.search_result_text.setMinimumHeight(140)
        result_main_layout.addWidget(self.search_result_text)

        # 액션 버튼
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)

        self.external_preview_btn = QPushButton("미리보기")
        self.external_preview_btn.setEnabled(False)
        self.external_preview_btn.clicked.connect(self.show_external_paper_preview)
        self.external_preview_btn.setMinimumHeight(42)
        action_layout.addWidget(self.external_preview_btn)

        self.external_publish_btn = QPushButton("발행하기")
        self.external_publish_btn.setObjectName("primaryBtn")
        self.external_publish_btn.setEnabled(False)
        self.external_publish_btn.clicked.connect(self.publish_external)
        self.external_publish_btn.setMinimumHeight(42)
        self.external_publish_btn.setToolTip("PDF 다운로드 + MD 저장 + 티스토리 발행")
        action_layout.addWidget(self.external_publish_btn)

        action_layout.addStretch()
        result_main_layout.addLayout(action_layout)

        layout.addWidget(result_widget)
        layout.addStretch()

        self.tab_widget.addTab(tab, "새 논문 검색")

    def create_recommendation_tab(self):
        """논문 추천 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        # ===== 메인 콘텐츠: 분야 선택 + 추천 목록 =====
        content_splitter = QSplitter(Qt.Horizontal)

        # 왼쪽: 분야 필터
        filter_widget = QWidget()
        filter_widget.setStyleSheet(f"background-color: {Colors.BG_CARD}; border-radius: 10px;")
        filter_widget.setMinimumWidth(200)
        filter_widget.setMaximumWidth(280)
        filter_layout = QVBoxLayout(filter_widget)
        filter_layout.setContentsMargins(16, 16, 16, 16)
        filter_layout.setSpacing(8)

        filter_title = QLabel("분야 필터")
        filter_title.setObjectName("sectionTitle")
        filter_layout.addWidget(filter_title)

        # 전체 선택
        self.category_all_check = QCheckBox("전체 분야")
        self.category_all_check.setChecked(True)
        self.category_all_check.stateChanged.connect(self.on_category_all_changed)
        filter_layout.addWidget(self.category_all_check)

        # 분야별 체크박스 - 스크롤 가능한 영역
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(f"background-color: transparent;")

        scroll_content = QWidget()
        scroll_content.setStyleSheet(f"background-color: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(4)

        self.category_checks = {}
        for category, info in PaperCategorizer.CATEGORIES.items():
            cb = QCheckBox(f"{info['icon']} {category}")
            cb.setChecked(True)
            cb.stateChanged.connect(self.filter_recommendations)
            self.category_checks[category] = cb
            scroll_layout.addWidget(cb)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        filter_layout.addWidget(scroll_area, 1)  # stretch factor 1로 공간 확보

        # 정렬 옵션
        sort_label = QLabel("정렬")
        sort_label.setObjectName("mutedLabel")
        filter_layout.addWidget(sort_label)

        self.rec_sort_combo = QComboBox()
        self.rec_sort_combo.addItems([
            "🎲 랜덤",
            "📅 연도 ↑ (오래된순)",
            "📅 연도 ↓ (최신순)",
            "📊 인용수 ↑ (적은순)",
            "📊 인용수 ↓ (많은순)",
            "📥 최근 추가순"
        ])
        self.rec_sort_combo.setCurrentIndex(5)  # 기본: 최근 추가순
        self.rec_sort_combo.currentIndexChanged.connect(self.filter_recommendations)
        filter_layout.addWidget(self.rec_sort_combo)

        # 연도 필터
        year_label = QLabel("연도 범위")
        year_label.setObjectName("mutedLabel")
        filter_layout.addWidget(year_label)

        year_layout = QHBoxLayout()
        current_year = 2026

        self.year_from_spin = QSpinBox()
        self.year_from_spin.setRange(1990, current_year)
        self.year_from_spin.setValue(1990)  # 전체 논문 표시를 위해 범위 확대
        self.year_from_spin.valueChanged.connect(self.filter_recommendations)
        year_layout.addWidget(self.year_from_spin)

        year_layout.addWidget(QLabel("~"))

        self.year_to_spin = QSpinBox()
        self.year_to_spin.setRange(2000, current_year)
        self.year_to_spin.setValue(current_year)
        self.year_to_spin.valueChanged.connect(self.filter_recommendations)
        year_layout.addWidget(self.year_to_spin)

        filter_layout.addLayout(year_layout)

        self.exclude_reviewed_check = QCheckBox("리뷰 완료 제외")
        self.exclude_reviewed_check.setChecked(True)
        self.exclude_reviewed_check.stateChanged.connect(self.filter_recommendations)
        filter_layout.addWidget(self.exclude_reviewed_check)

        # 구분선
        filter_separator = QFrame()
        filter_separator.setFrameShape(QFrame.HLine)
        filter_separator.setStyleSheet(f"background-color: {Colors.BORDER}; margin: 8px 0;")
        filter_layout.addWidget(filter_separator)

        # ===== Claude 최신 논문 검색 =====
        search_title = QLabel("🔍 AI 최신 논문 검색")
        search_title.setObjectName("sectionTitle")
        search_title.setStyleSheet(f"color: {Colors.PRIMARY}; font-weight: bold;")
        filter_layout.addWidget(search_title)

        search_desc = QLabel("Claude가 선택한 분야의\n최신 AI 논문을 검색합니다")
        search_desc.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
        search_desc.setWordWrap(True)
        filter_layout.addWidget(search_desc)

        # 검색 개수 선택
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("검색 개수:"))
        self.search_count_combo = QComboBox()
        self.search_count_combo.addItems(["3개", "5개", "10개"])
        self.search_count_combo.setCurrentIndex(1)  # 기본 5개
        count_layout.addWidget(self.search_count_combo)
        count_layout.addStretch()
        filter_layout.addLayout(count_layout)

        # 검색 버튼 레이아웃
        search_btn_layout = QHBoxLayout()

        # 선택 분야 검색 버튼
        self.category_search_btn = QPushButton("🚀 선택 분야 검색")
        self.category_search_btn.setObjectName("primaryBtn")
        self.category_search_btn.clicked.connect(self.search_latest_papers)
        self.category_search_btn.setMinimumHeight(40)
        search_btn_layout.addWidget(self.category_search_btn)

        # Lucky 검색 버튼 (랜덤 분야 1개 논문)
        self.lucky_search_btn = QPushButton("🎲 Lucky")
        self.lucky_search_btn.setToolTip("랜덤 분야에서 최신 AI 논문 1개를 검색합니다")
        self.lucky_search_btn.clicked.connect(self.search_lucky_paper)
        self.lucky_search_btn.setMinimumHeight(40)
        self.lucky_search_btn.setMaximumWidth(80)
        self.lucky_search_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SUCCESS};
                color: white;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.SUCCESS_DARK};
            }}
        """)
        search_btn_layout.addWidget(self.lucky_search_btn)

        filter_layout.addLayout(search_btn_layout)

        # 검색 상태 표시
        self.search_status_label = QLabel("")
        self.search_status_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
        self.search_status_label.setWordWrap(True)
        filter_layout.addWidget(self.search_status_label)

        content_splitter.addWidget(filter_widget)

        # 오른쪽: 추천 논문 목록
        rec_widget = QWidget()
        rec_widget.setStyleSheet(f"background-color: {Colors.BG_CARD}; border-radius: 10px;")
        rec_layout = QVBoxLayout(rec_widget)
        rec_layout.setContentsMargins(16, 16, 16, 16)
        rec_layout.setSpacing(12)

        rec_header = QHBoxLayout()
        rec_title = QLabel("추천 논문")
        rec_title.setObjectName("sectionTitle")
        rec_header.addWidget(rec_title)

        self.rec_count_label = QLabel("0개")
        self.rec_count_label.setObjectName("mutedLabel")
        rec_header.addWidget(self.rec_count_label)
        rec_header.addStretch()

        # AI 일괄 코멘트 생성 버튼
        self.batch_comment_btn = QPushButton("🤖 AI 코멘트 생성")
        self.batch_comment_btn.setToolTip("선택한 논문 또는 전체 미생성 논문에 AI 코멘트를 생성합니다")
        self.batch_comment_btn.clicked.connect(self.generate_batch_comments)
        self.batch_comment_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_DARK};
            }}
        """)
        rec_header.addWidget(self.batch_comment_btn)

        # 대기열 추가 버튼
        self.add_rec_to_queue_btn = QPushButton("선택 항목 대기열 추가")
        self.add_rec_to_queue_btn.setObjectName("successBtn")
        self.add_rec_to_queue_btn.clicked.connect(self.add_recommended_to_queue)
        rec_header.addWidget(self.add_rec_to_queue_btn)
        rec_layout.addLayout(rec_header)

        # 추천 테이블
        self.rec_table = QTableWidget()
        self.rec_table.setColumnCount(8)
        self.rec_table.setHorizontalHeaderLabels([
            "", "분야", "제목", "연도", "인용", "AI 코멘트", "점수", "상태"
        ])
        self.rec_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.rec_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.rec_table.setAlternatingRowColors(True)
        self.rec_table.verticalHeader().setVisible(False)
        self.rec_table.itemSelectionChanged.connect(self.on_rec_selection_changed)
        self.rec_table.itemDoubleClicked.connect(self.show_rec_paper_detail)
        rec_layout.addWidget(self.rec_table)

        # 선택된 논문 정보
        self.rec_info_text = QTextEdit()
        self.rec_info_text.setReadOnly(True)
        self.rec_info_text.setMaximumHeight(100)
        self.rec_info_text.setPlaceholderText("논문을 선택하면 상세 정보가 표시됩니다...")
        rec_layout.addWidget(self.rec_info_text)

        # 액션 버튼
        action_layout = QHBoxLayout()
        
        self.rec_preview_btn = QPushButton("미리보기")
        self.rec_preview_btn.setEnabled(False)
        self.rec_preview_btn.clicked.connect(self.preview_rec_paper)
        action_layout.addWidget(self.rec_preview_btn)

        self.rec_publish_btn = QPushButton("선택 논문 발행")
        self.rec_publish_btn.setObjectName("primaryBtn")
        self.rec_publish_btn.setEnabled(False)
        self.rec_publish_btn.clicked.connect(self.publish_rec_paper)
        action_layout.addWidget(self.rec_publish_btn)

        action_layout.addStretch()
        rec_layout.addLayout(action_layout)

        content_splitter.addWidget(rec_widget)
        content_splitter.setSizes([220, 800])

        layout.addWidget(content_splitter, 1)

        self.tab_widget.addTab(tab, "논문 추천")

    def search_latest_papers(self):
        """선택된 분야의 최신 논문을 다양한 소스에서 검색 (첫 번째 분야에서만 전체 개수 검색)"""
        # 선택된 분야 확인
        selected_categories = [
            cat for cat, cb in self.category_checks.items()
            if cb.isChecked() and cat != "Other"
        ]

        if not selected_categories:
            QMessageBox.warning(self, "분야 선택 필요", "검색할 분야를 하나 이상 선택해주세요.")
            return

        # 검색 개수 파싱
        count_text = self.search_count_combo.currentText()
        count = int(count_text.replace("개", ""))

        # 첫 번째 선택된 분야만 사용 (사용자 요청: 하나의 분야에서만 검색)
        target_category = selected_categories[0]
        if len(selected_categories) > 1:
            self.statusBar().showMessage(f"💡 '{target_category}' 분야에서 {count}개 검색합니다 (첫 번째 선택 분야)")

        # UI 비활성화
        self.category_search_btn.setEnabled(False)
        self.category_search_btn.setText("🔄 검색 중...")
        self.lucky_search_btn.setEnabled(False)
        self.search_status_label.setText(f"📚 {target_category}에서 {count}개 검색 중...")
        self.searched_papers = []

        # 이전 검색 결과의 제목 수집 (중복 방지)
        self.previous_search_titles = [p.get('title', '') for p in self.papers]

        # 첫 번째 선택된 분야에서만 전체 개수 검색
        self.search_categories_queue = [target_category]
        self.search_count_per_category = count  # 분야 나누지 않고 전체 개수
        self.is_lucky_search = False  # 일반 검색
        self.start_next_category_search()

    def search_lucky_paper(self):
        """랜덤 분야에서 최신 AI 논문 1개 검색 (Lucky 검색)"""
        import random

        # Other 제외한 모든 분야에서 랜덤 선택
        all_categories = [cat for cat in PaperCategorizer.CATEGORIES.keys() if cat != "Other"]
        if not all_categories:
            QMessageBox.warning(self, "오류", "검색 가능한 분야가 없습니다.")
            return

        random_category = random.choice(all_categories)

        # UI 비활성화
        self.lucky_search_btn.setEnabled(False)
        self.lucky_search_btn.setText("🎲...")
        self.category_search_btn.setEnabled(False)
        self.search_status_label.setText(f"🎲 Lucky! '{random_category}' 분야에서 논문 검색 중...")
        self.statusBar().showMessage(f"🎲 랜덤 분야 '{random_category}'에서 최신 논문 1개 검색 중...")
        self.searched_papers = []

        # 이전 검색 결과의 제목 수집 (중복 방지)
        self.previous_search_titles = [p.get('title', '') for p in self.papers]

        # 랜덤 분야에서 1개만 검색
        self.search_categories_queue = [random_category]
        self.search_count_per_category = 1
        self.is_lucky_search = True  # Lucky 검색 플래그
        self.start_next_category_search()

    def start_next_category_search(self):
        """다음 분야 검색 시작"""
        if not self.search_categories_queue:
            # 모든 분야 검색 완료
            self.on_all_categories_searched()
            return

        category = self.search_categories_queue.pop(0)
        keywords = PaperCategorizer.CATEGORIES.get(category, {}).get('keywords', [])

        self.search_status_label.setText(f"🔍 {category} 검색 중...")
        self.statusBar().showMessage(f"🔍 {category} 분야 최신 논문 검색 중 (arXiv, Semantic Scholar 등)...")

        # 이미 검색된 논문 제목 + 기존 논문 제목
        previous_titles = self.previous_search_titles + [p.get('title', '') for p in self.searched_papers]

        self.category_search_worker = CategorySearchWorker(
            self.paper_searcher, category, keywords,
            self.search_count_per_category, previous_titles
        )
        self.category_search_worker.finished.connect(self.on_category_search_finished)
        self.category_search_worker.error.connect(self.on_category_search_error)
        self.category_search_worker.progress.connect(self.on_category_search_progress)
        self.category_search_worker.source_info.connect(self.on_source_info)
        self.category_search_worker.start()

    def on_source_info(self, info: str):
        """검색 소스 정보 표시"""
        self.statusBar().showMessage(info)

    def on_category_search_progress(self, message: str):
        """분야 검색 진행 상황"""
        self.search_status_label.setText(message)

    def on_category_search_finished(self, papers: list):
        """분야 검색 완료"""
        self.searched_papers.extend(papers)
        self.search_status_label.setText(f"✅ {len(papers)}개 논문 발견")

        # 이전 워커 정리 (스레드 종료 대기 후 삭제)
        self._cleanup_search_worker()

        # 다음 분야 검색
        self.start_next_category_search()

    def on_category_search_error(self, error: str):
        """분야 검색 오류"""
        self.search_status_label.setText(f"⚠️ 오류 발생")
        self.statusBar().showMessage(f"검색 오류: {error}")

        # 이전 워커 정리
        self._cleanup_search_worker()

        # 오류가 있어도 다음 분야 계속 검색
        self.start_next_category_search()

    def _cleanup_search_worker(self):
        """검색 워커 정리 (스레드 안전)"""
        if self.category_search_worker is not None:
            # 스레드가 아직 실행 중이면 종료 대기
            if self.category_search_worker.isRunning():
                self.category_search_worker.wait(1000)  # 최대 1초 대기
            # 안전하게 나중에 삭제
            self.category_search_worker.deleteLater()
            self.category_search_worker = None

    def on_all_categories_searched(self):
        """모든 분야 검색 완료"""
        # 마지막 워커 정리
        self._cleanup_search_worker()

        # UI 복원
        self.category_search_btn.setEnabled(True)
        self.category_search_btn.setText("🚀 선택 분야 검색")
        self.lucky_search_btn.setEnabled(True)
        self.lucky_search_btn.setText("🎲 Lucky")

        if self.searched_papers:
            if self.is_lucky_search:
                # Lucky 검색 완료 메시지
                paper = self.searched_papers[0]
                category = paper.get('searched_category', 'AI')
                self.search_status_label.setText(f"🎲 Lucky! '{category}' 분야 논문 발견!")
                self.statusBar().showMessage(f"🎲 Lucky 검색 완료: '{paper.get('title', '')[:50]}...'")
            else:
                self.search_status_label.setText(f"✅ 총 {len(self.searched_papers)}개 논문 발견!")
                self.statusBar().showMessage(f"✅ 검색 완료: {len(self.searched_papers)}개 최신 논문 발견")

            self.display_searched_papers()

            # 검색된 논문을 papers.json에 자동 저장
            self._save_searched_papers_to_json()
        else:
            self.search_status_label.setText("검색 결과 없음")
            self.statusBar().showMessage("검색 결과가 없습니다.")

        # Lucky 플래그 리셋
        self.is_lucky_search = False

    def display_searched_papers(self):
        """검색된 논문을 테이블에 표시"""
        self.rec_table.setRowCount(0)

        for paper in self.searched_papers:
            row = self.rec_table.rowCount()
            self.rec_table.insertRow(row)

            # 분야 분류
            category = PaperCategorizer.categorize_paper(paper)
            cat_info = PaperCategorizer.CATEGORIES.get(category, {'icon': '📄', 'color': '#6b7280'})
            cat_color = cat_info.get('color', '#6b7280')

            # 체크박스
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            check_item.setCheckState(Qt.Unchecked)
            self.rec_table.setItem(row, 0, check_item)

            # 분야 (색상 배경 적용)
            cat_item = QTableWidgetItem(f"{cat_info['icon']} {category[:8]}")
            cat_item.setToolTip(category)
            cat_item.setBackground(QColor(cat_color).lighter(180))
            cat_item.setForeground(QColor(cat_color).darker(150))
            self.rec_table.setItem(row, 1, cat_item)

            # 제목
            title = paper.get('title', 'Unknown')
            title_item = QTableWidgetItem(title[:50] + "..." if len(title) > 50 else title)
            title_item.setToolTip(title)
            self.rec_table.setItem(row, 2, title_item)

            # 연도
            year = paper.get('year', '')
            self.rec_table.setItem(row, 3, QTableWidgetItem(str(year) if year else "-"))

            # 인용수
            citations = paper.get('citations', 0)
            cit_str = f"{citations/1000:.1f}K" if citations >= 1000 else (str(citations) if citations else "-")
            self.rec_table.setItem(row, 4, QTableWidgetItem(cit_str))

            # AI 코멘트 (새 검색된 논문은 아직 없음)
            comment_item = QTableWidgetItem("🔄 저장 후 생성")
            comment_item.setForeground(QColor(Colors.PRIMARY))
            self.rec_table.setItem(row, 5, comment_item)

            # 점수 (검색된 논문은 중요도로 표시)
            importance = paper.get('importance_score', 0)
            self.rec_table.setItem(row, 6, QTableWidgetItem(f"{importance:.0f}"))

            # 상태 (새로 검색된 논문)
            status_item = QTableWidgetItem("🆕")
            status_item.setTextAlignment(Qt.AlignCenter)
            self.rec_table.setItem(row, 7, status_item)

            # paper 데이터 저장
            check_item.setData(Qt.UserRole, paper)
            check_item.setData(Qt.UserRole + 1, True)  # 검색된 논문 플래그

        self.rec_count_label.setText(f"{len(self.searched_papers)}개 (검색)")

        # 컬럼 너비 조정
        self.rec_table.setColumnWidth(0, 30)
        self.rec_table.setColumnWidth(1, 110)
        self.rec_table.setColumnWidth(3, 45)
        self.rec_table.setColumnWidth(4, 45)
        self.rec_table.setColumnWidth(5, 200)
        self.rec_table.setColumnWidth(6, 40)
        self.rec_table.setColumnWidth(7, 35)

    def _save_searched_papers_to_json(self):
        """검색된 논문을 papers.json에 저장하고 자동 AI 코멘트 생성"""
        import json
        from datetime import datetime

        papers_file = project_root / "data" / "papers.json"

        try:
            # 기존 데이터 로드
            existing_papers = []
            if papers_file.exists():
                with open(papers_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        existing_papers = data
                    elif isinstance(data, dict) and "papers" in data:
                        existing_papers = data.get("papers", [])

            # 기존 논문 제목 집합 (중복 체크용)
            existing_titles = {p.get("title", "").lower() for p in existing_papers if p.get("title")}

            # 새 논문 추가 (중복 제외)
            added_count = 0
            new_papers = []
            for paper in self.searched_papers:
                title = paper.get("title", "")
                if title and title.lower() not in existing_titles:
                    # 분야 분류
                    category = PaperCategorizer.categorize_paper(paper)
                    field_code = category.lower().replace(' ', '_').replace('-', '_') if category else ""

                    # papers.json 형식에 맞게 변환
                    paper_entry = {
                        "title": title,
                        "year": paper.get("year", datetime.now().year),
                        "authors": paper.get("authors", []),
                        "arxiv_id": paper.get("arxiv_id", ""),
                        "url": paper.get("url", ""),
                        "pdf_url": paper.get("pdf_url", ""),
                        "abstract": paper.get("abstract", ""),
                        "source": paper.get("source", ""),
                        "field": field_code,
                        "field_name": category,
                        "citations": paper.get("citations", 0),
                        "added_at": datetime.now().isoformat(),
                        "status": "pending",
                        "comment": "",  # 나중에 AI 코멘트 생성
                    }
                    new_papers.append(paper_entry)
                    existing_papers.insert(0, paper_entry)
                    existing_titles.add(title.lower())
                    added_count += 1

            # 저장
            if added_count > 0:
                papers_file.parent.mkdir(parents=True, exist_ok=True)
                with open(papers_file, 'w', encoding='utf-8') as f:
                    json.dump(existing_papers, f, ensure_ascii=False, indent=2)

                # 자동 AI 코멘트 생성 (백그라운드)
                self._generate_comments_for_new_papers(new_papers, existing_papers, papers_file)

                self.statusBar().showMessage(
                    f"✅ {added_count}개 논문 추가됨, AI 코멘트 생성 중..."
                )

                # 메인 리스트 갱신
                self.load_papers()
            else:
                self.statusBar().showMessage(
                    f"✅ 검색 완료: {len(self.searched_papers)}개 발견 (모두 이미 저장됨)"
                )

        except Exception as e:
            self.statusBar().showMessage(f"⚠️ 저장 오류: {str(e)[:50]}")

    def _generate_comments_for_new_papers(self, new_papers, all_papers, papers_file):
        """새로 추가된 논문에 AI 코멘트 자동 생성"""
        if not self.ensure_claude_client():
            return

        try:
            success_count = 0
            total = len(new_papers)

            for i, paper in enumerate(new_papers):
                title = paper.get('title', '')
                if not title:
                    continue

                self.statusBar().showMessage(f"🤖 코멘트 생성 중... ({i+1}/{total})")
                QApplication.processEvents()

                comment = self.claude_client.generate_paper_comment(
                    title=title,
                    abstract=paper.get('abstract', ''),
                    field=paper.get('field_name', '')
                )

                if comment:
                    # all_papers에서 해당 논문 찾아서 코멘트 추가
                    for p in all_papers:
                        if p.get('title') == title:
                            p['comment'] = comment
                            break
                    success_count += 1

            # 코멘트가 추가된 경우 다시 저장
            if success_count > 0:
                with open(papers_file, 'w', encoding='utf-8') as f:
                    json.dump(all_papers, f, ensure_ascii=False, indent=2)

                self.load_papers()
                self.statusBar().showMessage(f"✅ {total}개 논문 추가, {success_count}개 AI 코멘트 생성 완료")

        except Exception as e:
            logger.error(f"자동 코멘트 생성 실패: {e}")

    def on_category_all_changed(self, state):
        """전체 분야 체크박스 변경"""
        checked = state == Qt.Checked
        for cb in self.category_checks.values():
            cb.blockSignals(True)
            cb.setChecked(checked)
            cb.blockSignals(False)
        self.filter_recommendations()

    def filter_recommendations(self):
        """추천 논문 필터링 및 표시"""
        if not self.papers or not hasattr(self, 'paper_manager'):
            return

        # 선택된 분야
        selected_categories = [
            cat for cat, cb in self.category_checks.items() 
            if cb.isChecked()
        ]

        # 리뷰 완료 목록
        exclude_list = []
        if self.exclude_reviewed_check.isChecked():
            progress = self.paper_manager.get_progress_info()
            exclude_list = self.paper_manager.state.get('reviewed_papers', [])

        # 논문 목록 생성 (전체)
        recommendations = PaperCategorizer.get_top_recommendations(
            self.papers, n=None, exclude_reviewed=exclude_list
        )

        # 분야 필터 적용 (분야가 없거나 매칭 안되면 Other로 처리하여 포함)
        filtered = []
        for r in recommendations:
            cat = r['category']
            # 선택된 분야에 있거나, Other이거나, 분야가 없으면 포함
            if cat in selected_categories or cat == 'Other' or not cat:
                filtered.append(r)
            # 선택된 분야에 'Other'가 있으면 매칭 안되는 분야도 포함
            elif 'Other' in selected_categories:
                filtered.append(r)

        # 연도 필터 적용 (연도가 없으면 포함)
        year_from = self.year_from_spin.value()
        year_to = self.year_to_spin.value()
        filtered = [
            r for r in filtered
            if not r['paper'].get('year') or year_from <= r['paper'].get('year', 9999) <= year_to
        ]

        # 정렬
        import random
        sort_index = self.rec_sort_combo.currentIndex()
        if sort_index == 0:  # 랜덤
            random.shuffle(filtered)
        elif sort_index == 1:  # 연도 오름차순 (오래된순)
            filtered.sort(key=lambda x: x['paper'].get('year', 0), reverse=False)
        elif sort_index == 2:  # 연도 내림차순 (최신순)
            filtered.sort(key=lambda x: x['paper'].get('year', 0), reverse=True)
        elif sort_index == 3:  # 인용수 오름차순 (적은순)
            filtered.sort(key=lambda x: x['paper'].get('citations', 0), reverse=False)
        elif sort_index == 4:  # 인용수 내림차순 (많은순)
            filtered.sort(key=lambda x: x['paper'].get('citations', 0), reverse=True)
        elif sort_index == 5:  # 최근 추가순
            filtered.sort(key=lambda x: x['paper'].get('added_at', ''), reverse=True)

        # 테이블 업데이트
        self.rec_table.setRowCount(0)
        for rec in filtered:  # 전체 논문 표시
            row = self.rec_table.rowCount()
            self.rec_table.insertRow(row)

            paper = rec['paper']
            is_reviewed = self.paper_manager.is_paper_reviewed(paper)

            # 분야별 색상 가져오기
            cat_info = PaperCategorizer.CATEGORIES.get(rec['category'], {'icon': '📄', 'color': '#6b7280'})
            cat_color = cat_info.get('color', '#6b7280')

            # 체크박스
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            check_item.setCheckState(Qt.Unchecked)
            check_item.setData(Qt.UserRole, rec['index'])  # 원본 인덱스 저장
            self.rec_table.setItem(row, 0, check_item)

            # 분야 (색상 배경 적용)
            cat_item = QTableWidgetItem(f"{cat_info['icon']} {rec['category'][:8]}")
            cat_item.setToolTip(rec['category'])
            cat_item.setBackground(QColor(cat_color).lighter(180))
            cat_item.setForeground(QColor(cat_color).darker(150))
            self.rec_table.setItem(row, 1, cat_item)

            # 제목
            title = paper.get('title', '')[:50]
            if len(paper.get('title', '')) > 50:
                title += "..."
            title_item = QTableWidgetItem(title)
            title_item.setToolTip(paper.get('title', ''))
            self.rec_table.setItem(row, 2, title_item)

            # 연도
            self.rec_table.setItem(row, 3, QTableWidgetItem(str(paper.get('year', '-'))))

            # 인용수
            citations = paper.get('citations', 0)
            if citations >= 1000:
                cit_str = f"{citations/1000:.1f}K"
            else:
                cit_str = str(citations) if citations else "-"
            self.rec_table.setItem(row, 4, QTableWidgetItem(cit_str))

            # AI 코멘트 (papers.json에서 로드)
            comment = paper.get('comment', '')
            comment_display = comment[:30] + "..." if len(comment) > 30 else comment
            comment_item = QTableWidgetItem(comment_display if comment else "🤖 미생성")
            comment_item.setToolTip(comment if comment else "코멘트가 없습니다")
            if not comment:
                comment_item.setForeground(QColor(Colors.TEXT_MUTED))
            self.rec_table.setItem(row, 5, comment_item)

            # 점수
            score_item = QTableWidgetItem(f"{rec['score']:.0f}")
            self.rec_table.setItem(row, 6, score_item)

            # 상태
            status = "✅" if is_reviewed else "⏳"
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignCenter)
            self.rec_table.setItem(row, 7, status_item)

        # 컬럼 너비
        self.rec_table.setColumnWidth(0, 30)   # 체크박스
        self.rec_table.setColumnWidth(1, 110)  # 분야
        self.rec_table.setColumnWidth(3, 45)   # 연도
        self.rec_table.setColumnWidth(4, 45)   # 인용
        self.rec_table.setColumnWidth(5, 200)  # 코멘트
        self.rec_table.setColumnWidth(6, 40)   # 점수
        self.rec_table.setColumnWidth(7, 35)   # 상태

        self.rec_count_label.setText(f"{len(filtered)}개 표시")

    def on_rec_selection_changed(self):
        """추천 테이블 선택 변경"""
        selected = self.rec_table.selectedItems()
        if selected:
            row = selected[0].row()
            idx_item = self.rec_table.item(row, 0)
            if idx_item:
                data = idx_item.data(Qt.UserRole)
                is_searched = idx_item.data(Qt.UserRole + 1)

                # 검색된 논문인 경우 (data가 dict)
                if is_searched and isinstance(data, dict):
                    self.show_rec_paper_info(data)
                    self.rec_preview_btn.setEnabled(True)
                    self.rec_publish_btn.setEnabled(True)
                    return
                # 기존 논문인 경우 (data가 int index)
                elif isinstance(data, int) and data < len(self.papers):
                    paper = self.papers[data]
                    self.show_rec_paper_info(paper)
                    self.rec_preview_btn.setEnabled(True)
                    self.rec_publish_btn.setEnabled(True)
                    return

        self.rec_info_text.clear()
        self.rec_preview_btn.setEnabled(False)
        self.rec_publish_btn.setEnabled(False)

    def show_rec_paper_info(self, paper):
        """추천 논문 상세 정보 표시"""
        category = PaperCategorizer.categorize_paper(paper)
        cat_info = PaperCategorizer.CATEGORIES.get(category, {'icon': '📄'})
        
        info = f"""<b>{cat_info['icon']} {paper.get('title', 'Unknown')}</b><br>
<span style="color: {Colors.TEXT_SECONDARY};">
저자: {', '.join(paper.get('authors', [])[:3])}<br>
연도: {paper.get('year', 'N/A')} | 인용수: {paper.get('citations', 'N/A'):,} | 분야: {category}
</span><br><br>
{paper.get('abstract', 'No abstract available.')[:300]}...
"""
        self.rec_info_text.setHtml(info)

    def show_rec_paper_detail(self, item):
        """추천 논문 더블클릭 시 상세 보기"""
        row = item.row()
        paper = self._get_paper_from_rec_table(row)
        if paper:
            url = paper.get('url', '')
            if url:
                webbrowser.open(url)

    def preview_rec_paper(self):
        """선택된 추천 논문 미리보기"""
        selected = self.rec_table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        paper = self._get_paper_from_rec_table(row)
        if paper:
            url = paper.get('url', '')
            if url:
                webbrowser.open(url)

    def publish_rec_paper(self):
        """선택된 추천 논문 발행"""
        selected = self.rec_table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        paper = self._get_paper_from_rec_table(row)
        if not paper:
            return

        # 발행 방식 선택 다이얼로그
        msg = QMessageBox(self)
        msg.setWindowTitle("발행 방식 선택")
        msg.setText(f"'{paper.get('title', '')[:50]}...' 논문을 어떻게 발행하시겠습니까?")
        msg.setIcon(QMessageBox.Question)
        
        blog_btn = msg.addButton("📤 블로그 발행", QMessageBox.AcceptRole)
        md_btn = msg.addButton("💾 MD만 저장", QMessageBox.ActionRole)
        msg.addButton("취소", QMessageBox.RejectRole)
        
        msg.exec_()
        clicked = msg.clickedButton()
        
        if clicked == blog_btn:
            save_md_only = False
        elif clicked == md_btn:
            save_md_only = True
        else:
            return  # 취소
        
        # 검색된 논문인 경우 외부 발행으로 처리
        idx_item = self.rec_table.item(row, 0)
        is_searched = idx_item.data(Qt.UserRole + 1) if idx_item else False

        if is_searched:
            # 검색된 논문은 외부 발행 처리
            self.searched_paper = paper
            self.run_external_publish(save_md_only=save_md_only)
        else:
            # 기존 논문은 인덱스로 발행
            paper_idx = idx_item.data(Qt.UserRole)
            if isinstance(paper_idx, int):
                self.selected_index = paper_idx
                self.run_publish(self.selected_index, save_md_only=save_md_only)

    def publish_searched_paper(self):
        """검색된 논문 발행 (레거시 - run_external_publish 사용 권장)"""
        if not self.searched_paper:
            return

        self.statusBar().showMessage("검색된 논문 발행 중...")

        self.external_worker = ExternalPublishWorker(
            self.poster,
            self.searched_paper,
            save_md_only=False
        )
        self.external_worker.finished.connect(self.on_publish_complete)
        self.external_worker.error.connect(self.on_publish_error)
        self.external_worker.progress.connect(self.on_publish_progress)
        self.external_worker.start()

    def _get_paper_from_rec_table(self, row: int) -> dict:
        """추천 테이블에서 논문 데이터 가져오기"""
        idx_item = self.rec_table.item(row, 0)
        if not idx_item:
            return None

        data = idx_item.data(Qt.UserRole)
        is_searched = idx_item.data(Qt.UserRole + 1)

        # 검색된 논문인 경우
        if is_searched and isinstance(data, dict):
            return data
        # 기존 논문인 경우
        elif isinstance(data, int) and data < len(self.papers):
            return self.papers[data]
        return None

    def generate_batch_comments(self):
        """전체 논문에 AI 코멘트 일괄 생성 (기존 코멘트 덮어쓰기)"""
        if not self.ensure_claude_client():
            QMessageBox.warning(self, "API 오류", "Claude API 클라이언트 초기화에 실패했습니다.\nconfig.yaml의 API 키를 확인해주세요.")
            return

        # 전체 논문 처리
        papers_to_process = self.papers
        if not papers_to_process:
            QMessageBox.information(self, "알림", "처리할 논문이 없습니다.")
            return

        # 확인 대화상자
        reply = QMessageBox.question(
            self, "AI 코멘트 생성",
            f"전체 {len(papers_to_process)}개 논문에 AI 코멘트를 생성합니다.\n(기존 코멘트는 덮어쓰기됩니다)\n\n계속하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        # 진행 상황 표시
        self.statusBar().showMessage("🤖 AI 코멘트 생성 중...")
        QApplication.processEvents()

        success_count = 0
        total = len(papers_to_process)

        for i, paper in enumerate(papers_to_process):
            title = paper.get('title', '')
            if not title:
                continue

            self.statusBar().showMessage(f"🤖 코멘트 생성 중... ({i+1}/{total})")
            QApplication.processEvents()

            try:
                # 분야 재매핑
                new_category = PaperCategorizer.categorize_paper(paper)
                if new_category and new_category != 'Other':
                    paper['field'] = new_category.lower().replace(' ', '_').replace('-', '_')
                    paper['field_name'] = new_category

                # AI 코멘트 생성
                comment = self.claude_client.generate_paper_comment(
                    title=title,
                    abstract=paper.get('abstract', ''),
                    field=paper.get('field_name', paper.get('field', ''))
                )

                if comment:
                    paper['comment'] = comment
                    success_count += 1

            except Exception as e:
                logger.error(f"코멘트 생성 실패 ({title}): {e}")
                continue

        # papers.json 저장
        self._save_papers_with_comments()

        # 테이블 새로고침
        self.filter_recommendations()

        self.statusBar().showMessage(f"✅ {success_count}개 논문에 AI 코멘트 생성 완료")
        QMessageBox.information(
            self, "완료",
            f"{success_count}/{total}개 논문에 AI 코멘트가 생성되었습니다."
        )

    def _save_papers_with_comments(self):
        """papers.json에 코멘트와 분야 정보 저장"""
        try:
            papers_file = project_root / "data" / "papers.json"
            with open(papers_file, 'w', encoding='utf-8') as f:
                json.dump(self.papers, f, ensure_ascii=False, indent=2)
            logger.info("papers.json 저장 완료 (코멘트 포함)")
        except Exception as e:
            logger.error(f"papers.json 저장 실패: {e}")

    def add_recommended_to_queue(self):
        """체크된 추천 논문들을 대기열에 추가"""
        added_count = 0
        for row in range(self.rec_table.rowCount()):
            item = self.rec_table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                data = item.data(Qt.UserRole)
                is_searched = item.data(Qt.UserRole + 1)

                paper = None
                paper_idx = -1  # 검색된 논문은 음수 인덱스 사용

                # 검색된 논문인 경우
                if is_searched and isinstance(data, dict):
                    paper = data
                    # 검색된 논문은 제목을 키로 사용하여 중복 체크
                    paper_title = paper.get('title', '')
                    is_duplicate = any(
                        p[2].get('title', '') == paper_title for p in self.publish_queue
                    )
                # 기존 논문인 경우
                elif isinstance(data, int) and data < len(self.papers):
                    paper_idx = data
                    paper = self.papers[paper_idx]
                    is_duplicate = any(
                        p[1] == paper_idx for p in self.publish_queue
                    )
                else:
                    continue

                if paper and not is_duplicate:
                    queue_id = len(self.publish_queue) + 1
                    self.publish_queue.append((queue_id, paper_idx, paper))
                    added_count += 1

                # 체크 해제
                item.setCheckState(Qt.Unchecked)

        if added_count > 0:
            self.update_queue_display()
            self.statusBar().showMessage(f"{added_count}개 논문이 대기열에 추가되었습니다.")
        else:
            self.statusBar().showMessage("추가할 논문을 선택해주세요.")

    def show_paper_preview(self, item):
        """테이블에서 더블클릭 시 미리보기"""
        row = item.row()
        idx = int(self.table.item(row, 1).text())  # 컬럼 1이 인덱스
        paper = self.papers[idx]
        self.open_preview_dialog(paper)

    def show_selected_paper_preview(self):
        """선택된 논문 미리보기"""
        if self.selected_index is not None:
            paper = self.papers[self.selected_index]
            self.open_preview_dialog(paper)

    def show_external_paper_preview(self):
        """외부 검색 논문 미리보기"""
        if self.searched_paper:
            self.open_preview_dialog(self.searched_paper)

    def open_preview_dialog(self, paper):
        """미리보기 다이얼로그 열기"""
        url = paper.get('url', '')
        if url:
            dialog = PaperPreviewDialog(self, paper)
            dialog.exec_()
        else:
            QMessageBox.information(
                self, "미리보기",
                f"논문 URL이 없습니다.\n\n제목: {paper.get('title', 'N/A')}"
            )

    def clear_history(self):
        reply = QMessageBox.question(
            self, "확인",
            "모든 검색 기록을 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes or reply == QMessageBox.StandardButton.Yes:
            self.search_history = []
            save_search_history([])
            self.completer.setModel(QStringListModel([]))
            self.statusBar().showMessage("검색 기록이 삭제되었습니다.")

    def load_papers(self):
        """논문 로드 (papers.json에서만 로드, 발행 시에만 API 사용)"""
        self.statusBar().showMessage("논문 로딩 중...")
        QApplication.processEvents()

        try:
            # PaperManager만 사용하여 논문 로드 (쿠키 검증 없이)
            papers_file = project_root / "data" / "papers.json"
            self.paper_manager = PaperManager(papers_file=str(papers_file))
            self.papers = self.paper_manager.get_all_papers()

            progress = self.paper_manager.get_progress_info()
            reviewed = progress['reviewed_count']
            total = progress['total_papers']
            percent = progress['progress_percent']

            # 헤더 통계 업데이트
            self.stat_reviewed.setText(str(reviewed))
            self.stat_total.setText(str(total))
            self.progress_percent_label.setText(f"{percent:.1f}%")
            self.progress_bar.setValue(int(percent))

            self.filter_papers()

            # 추천 탭 업데이트
            self.filter_recommendations()

            self.statusBar().showMessage(f"총 {total}개 논문 로드됨 ({reviewed}개 리뷰 완료)")

        except Exception as e:
            QMessageBox.critical(self, "오류", f"논문 로드 실패:\n{e}")
            self.statusBar().showMessage("오류 발생")

    def ensure_poster(self) -> bool:
        """발행에 필요한 TistoryAutoPoster 초기화 (lazy initialization)

        Returns:
            bool: 초기화 성공 여부
        """
        if self.poster is not None:
            return True

        try:
            self.poster = TistoryAutoPoster()
            return True
        except Exception as e:
            error_msg = str(e).lower()
            if "cookie" in error_msg or "로그인" in error_msg or "만료" in error_msg:
                self.statusBar().showMessage("⚠️ 쿠키 만료됨 - 티스토리 로그인 후 config.yaml 쿠키 갱신 필요")
            else:
                self.statusBar().showMessage(f"⚠️ 발행 초기화 실패: {str(e)[:50]}")
            return False

    def ensure_claude_client(self) -> bool:
        """Claude 클라이언트 초기화 (티스토리 쿠키 없이 사용 가능)

        논문 검색 등 Claude API만 필요한 기능에 사용

        Returns:
            bool: 초기화 성공 여부
        """
        if self.claude_client is not None:
            return True

        try:
            import yaml
            config_path = project_root / "config.yaml"
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            if 'claude' not in config or not config['claude'].get('api_key'):
                self.statusBar().showMessage("⚠️ Claude API 키가 설정되지 않았습니다.")
                return False

            prompts_file = config.get('prompts_file', 'prompts.yaml')
            prompts_path = project_root / prompts_file

            self.claude_client = ClaudeClient(
                api_key=config['claude']['api_key'],
                model=config['claude'].get('model', 'claude-sonnet-4-20250514'),
                search_model=config['claude'].get('search_model', 'claude-3-5-haiku-20241022'),
                prompts_file=str(prompts_path)
            )
            self.statusBar().showMessage("✅ Claude 클라이언트 초기화 완료")
            return True
        except Exception as e:
            self.statusBar().showMessage(f"⚠️ Claude 초기화 실패: {str(e)[:50]}")
            return False

    def filter_papers(self):
        if not hasattr(self, 'paper_manager') or not self.papers:
            return

        search_term = self.search_input.text().lower()
        show_unreviewed = self.unreviewed_check.isChecked()

        # 연도 필터
        year_from = None
        year_to = None
        try:
            if self.year_from.text().strip():
                year_from = int(self.year_from.text().strip())
        except ValueError:
            pass
        try:
            if self.year_to.text().strip():
                year_to = int(self.year_to.text().strip())
        except ValueError:
            pass

        # 인용수 필터
        citation_min = None
        try:
            if self.citation_min.text().strip():
                citation_min = int(self.citation_min.text().strip())
        except ValueError:
            pass

        # 필터링
        filtered_papers = []
        for i, paper in enumerate(self.papers):
            is_reviewed = self.paper_manager.is_paper_reviewed(paper)

            if show_unreviewed and is_reviewed:
                continue

            title = paper.get('title', '')
            if search_term and search_term not in title.lower():
                continue

            year = paper.get('year', 0)
            if year_from and year < year_from:
                continue
            if year_to and year > year_to:
                continue

            citations = paper.get('citations', 0)
            if citation_min and citations < citation_min:
                continue

            filtered_papers.append((i, paper, is_reviewed))

        # 정렬
        sort_index = self.sort_combo.currentIndex()
        if sort_index == 1:  # 연도순↓
            filtered_papers.sort(key=lambda x: x[1].get('year', 0), reverse=True)
        elif sort_index == 2:  # 연도순↑
            filtered_papers.sort(key=lambda x: x[1].get('year', 0))
        elif sort_index == 3:  # 인용수↓
            filtered_papers.sort(key=lambda x: x[1].get('citations', 0), reverse=True)
        elif sort_index == 4:  # 인용수↑
            filtered_papers.sort(key=lambda x: x[1].get('citations', 0))
        elif sort_index == 5:  # 상태 (미리뷰 우선) - 미리뷰(False) < 리뷰완료(True)
            filtered_papers.sort(key=lambda x: (x[2], x[1].get('year', 0)), reverse=False)
        elif sort_index == 6:  # 상태 (리뷰 우선) - 리뷰완료(True) > 미리뷰(False)
            filtered_papers.sort(key=lambda x: (not x[2], x[1].get('year', 0)), reverse=False)
        # 0은 제목순 (기본)

        # 테이블 업데이트
        self.table.setRowCount(0)

        for i, paper, is_reviewed in filtered_papers:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # 체크박스
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            check_item.setCheckState(Qt.Unchecked)
            self.table.setItem(row, 0, check_item)

            status = "[O]" if is_reviewed else "[-]"
            year_str = str(paper.get('year', 'N/A'))
            citations_str = str(paper.get('citations', 'N/A'))
            title = paper.get('title', '')

            self.table.setItem(row, 1, QTableWidgetItem(str(i)))
            self.table.setItem(row, 2, QTableWidgetItem(status))
            self.table.setItem(row, 3, QTableWidgetItem(title))
            self.table.setItem(row, 4, QTableWidgetItem(year_str))
            self.table.setItem(row, 5, QTableWidgetItem(citations_str))

        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(1, 40)
        self.table.setColumnWidth(2, 40)
        self.table.setColumnWidth(4, 60)
        self.table.setColumnWidth(5, 70)

        self.table_count_label.setText(f"{len(filtered_papers)}개 표시")
        self.select_all_check.setChecked(False)

    def on_select(self):
        selected = self.table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        # 컬럼 1이 인덱스 (#)
        self.selected_index = int(self.table.item(row, 1).text())
        paper = self.papers[self.selected_index]

        info = f"<b>제목:</b> {paper.get('title', 'N/A')}<br>"
        authors = paper.get('authors', [])
        if isinstance(authors, list):
            author_str = ', '.join(authors[:3])
            if len(authors) > 3:
                author_str += f" 외 {len(authors) - 3}명"
            info += f"<b>저자:</b> {author_str}<br>"
        info += f"<b>년도:</b> {paper.get('year', 'N/A')} | "
        info += f"<b>인용수:</b> {paper.get('citations', 'N/A')}"
        if paper.get('url'):
            info += f" | <a href='{paper['url']}'>논문 링크</a>"

        self.info_text.setHtml(info)

        if not self.is_batch_running:
            self.publish_btn.setEnabled(True)
            self.preview_btn.setEnabled(True)

    def publish(self):
        if self.selected_index is None:
            QMessageBox.warning(self, "경고", "논문을 먼저 선택해주세요.")
            return

        # 발행 방식 선택 다이얼로그
        paper = self.papers[self.selected_index]
        msg = QMessageBox(self)
        msg.setWindowTitle("발행 방식 선택")
        msg.setText(f"'{paper.get('title', '')[:50]}...' 논문을 어떻게 발행하시겠습니까?")
        msg.setIcon(QMessageBox.Question)
        
        blog_btn = msg.addButton("📤 블로그 발행", QMessageBox.AcceptRole)
        md_btn = msg.addButton("💾 MD만 저장", QMessageBox.ActionRole)
        msg.addButton("취소", QMessageBox.RejectRole)
        
        msg.exec_()
        clicked = msg.clickedButton()
        
        if clicked == blog_btn:
            save_md_only = False
        elif clicked == md_btn:
            save_md_only = True
        else:
            return  # 취소
        
        self.run_publish(self.selected_index, save_md_only=save_md_only)

    def auto_publish(self):
        # 확인 없이 바로 자동 발행
        self.run_publish(None, save_md_only=False)

    def run_publish(self, index, save_md_only):
        self.statusBar().showMessage("준비 중...")

        # MD만 저장 모드는 쿠키 체크 없이 바로 진행
        if save_md_only:
            try:
                self.poster = TistoryAutoPoster(md_only=True)
            except Exception as e:
                QMessageBox.critical(self, "오류", f"초기화 실패:\n{e}")
                return
        else:
            # 블로그 발행 시에만 쿠키가 필요한 TistoryAutoPoster 초기화
            if not self.ensure_poster():
                return

        self.set_buttons_enabled(False)

        self.worker = PublishWorker(self.poster, index, save_md_only)
        self.worker.finished.connect(self.on_publish_complete)
        self.worker.error.connect(self.on_publish_error)
        self.worker.progress.connect(self.on_publish_progress)
        self.worker.start()

    def set_buttons_enabled(self, enabled):
        self.publish_btn.setEnabled(enabled and self.selected_index is not None)
        self.preview_btn.setEnabled(enabled and self.selected_index is not None)
        self.auto_btn.setEnabled(enabled)
        self.refresh_btn.setEnabled(enabled)
        self.search_btn.setEnabled(enabled)
        self.external_publish_btn.setEnabled(enabled and self.searched_paper is not None)
        self.external_preview_btn.setEnabled(enabled and self.searched_paper is not None)
        # 대기열 버튼 - 배치 발행 중에만 비활성화, 단일 발행 중에는 활성화
        if not self.is_batch_running:
            self.add_to_queue_btn.setEnabled(True)  # 단일 발행 중에도 항상 활성화
            self.batch_publish_btn.setEnabled(len(self.publish_queue) > 0)


    def on_publish_progress(self, message):
        """발행 진행 상황 업데이트"""
        self.statusBar().showMessage(message)

    def on_publish_complete(self, result):
        self.set_buttons_enabled(True)
        self.last_result = result

        if result['success']:
            self.statusBar().showMessage("발행 완료! PDF 다운로드 중...")

            output = f"<b>제목:</b> {result['title']}<br>"
            if result['url']:
                output += f"<b>URL:</b> <a href='{result['url']}'>{result['url']}</a><br>"
                self.open_url_btn.setEnabled(True)
            else:
                self.open_url_btn.setEnabled(False)

            if result['md_path']:
                output += f"<b>MD:</b> {result['md_path']}<br>"
                # MD 내용 자동 클립보드 복사
                self._copy_md_to_clipboard(result['md_path'])
                output += "<b>📋 클립보드:</b> MD 내용이 복사되었습니다!<br>"

            self.result_text.setHtml(output)
            self.load_papers()

            # 자동 PDF 다운로드 (arXiv 논문인 경우)
            paper = result.get('paper')
            if paper:
                self.auto_download_pdf(paper)
            else:
                QMessageBox.information(self, "완료", "발행이 완료되었습니다!\n\n📋 MD 내용이 클립보드에 복사되었습니다.")
        else:
            self.on_publish_error(result.get('error', '알 수 없는 오류'))


    def _copy_md_to_clipboard(self, md_path: str) -> bool:
        """MD 파일 내용을 클립보드에 복사"""
        try:
            from pathlib import Path
            md_file = Path(md_path)
            if md_file.exists():
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 클립보드에 복사
                clipboard = QApplication.clipboard()
                clipboard.setText(content)
                logger.info(f"MD 내용 클립보드 복사 완료: {md_path}")
                return True
            else:
                logger.warning(f"MD 파일 없음: {md_path}")
                return False
        except Exception as e:
            logger.error(f"클립보드 복사 실패: {e}")
            return False

    def copy_last_md_to_clipboard(self):
        """마지막 발행된 MD를 클립보드에 복사"""
        if hasattr(self, 'last_result') and self.last_result:
            md_path = self.last_result.get('md_path')
            if md_path:
                if self._copy_md_to_clipboard(md_path):
                    self.statusBar().showMessage("📋 MD 내용이 클립보드에 복사되었습니다!")
                    QMessageBox.information(self, "복사 완료", "MD 내용이 클립보드에 복사되었습니다.\n\n블로그 편집기에 붙여넣기 하세요.")
                else:
                    QMessageBox.warning(self, "오류", "MD 파일을 찾을 수 없습니다.")
            else:
                QMessageBox.warning(self, "오류", "발행된 MD 파일이 없습니다.")
        else:
            QMessageBox.warning(self, "오류", "먼저 논문을 발행해주세요.")

    def copy_md_as_html(self):
        """마지막 발행된 MD를 HTML로 변환하여 클립보드에 복사"""
        if hasattr(self, 'last_result') and self.last_result:
            md_path = self.last_result.get('md_path')
            if md_path:
                try:
                    from pathlib import Path
                    import markdown
                    
                    md_file = Path(md_path)
                    if md_file.exists():
                        with open(md_file, 'r', encoding='utf-8') as f:
                            md_content = f.read()
                        
                        # HTML로 변환
                        html = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
                        
                        # 클립보드에 복사
                        clipboard = QApplication.clipboard()
                        clipboard.setText(html)
                        
                        self.statusBar().showMessage("📋 HTML 내용이 클립보드에 복사되었습니다!")
                        QMessageBox.information(self, "복사 완료", "HTML 내용이 클립보드에 복사되었습니다.\n\n블로그 HTML 편집기에 붙여넣기 하세요.")
                    else:
                        QMessageBox.warning(self, "오류", "MD 파일을 찾을 수 없습니다.")
                except ImportError:
                    QMessageBox.warning(self, "오류", "markdown 라이브러리가 설치되지 않았습니다.\npip install markdown")
                except Exception as e:
                    QMessageBox.warning(self, "오류", f"HTML 변환 실패: {e}")
            else:
                QMessageBox.warning(self, "오류", "발행된 MD 파일이 없습니다.")
        else:
            QMessageBox.warning(self, "오류", "먼저 논문을 발행해주세요.")

    def auto_download_pdf(self, paper):
        """발행 후 자동 PDF 다운로드"""
        url = paper.get('url', '')
        if not url or 'arxiv.org' not in url:
            # arXiv가 아니면 PDF 다운로드 없이 완료
            self.statusBar().showMessage("발행 완료!")
            QMessageBox.information(self, "완료", "발행이 완료되었습니다!")
            return

        # PDF 다운로드 시작
        pdf_dir = project_root / "pdfs"
        pdf_dir.mkdir(exist_ok=True)

        self.pdf_worker = PDFDownloadWorker(paper, str(pdf_dir))
        self.pdf_worker.finished.connect(self.on_auto_pdf_complete)
        self.pdf_worker.error.connect(self.on_auto_pdf_error)
        self.pdf_worker.progress.connect(self.on_pdf_download_progress)
        self.pdf_worker.start()

    def on_auto_pdf_complete(self, file_path):
        """자동 PDF 다운로드 완료"""
        filename = Path(file_path).name
        self.statusBar().showMessage(f"발행 완료! PDF 저장: {filename}")

        # 결과 텍스트에 PDF 경로 추가
        current_html = self.result_text.toHtml()
        self.result_text.setHtml(current_html.replace("</body>", f"<b>PDF:</b> {file_path}</body>"))

        QMessageBox.information(self, "완료", f"발행이 완료되었습니다!\n\n📋 MD 내용이 클립보드에 복사되었습니다.\n📄 PDF 저장: {filename}")

    def on_auto_pdf_error(self, error):
        """자동 PDF 다운로드 오류 (발행은 성공)"""
        self.statusBar().showMessage("발행 완료! (PDF 다운로드 실패)")
        QMessageBox.information(self, "완료", f"발행이 완료되었습니다!\n\n(PDF 다운로드 실패: {error})")

    def on_publish_error(self, error):
        self.set_buttons_enabled(True)
        self.statusBar().showMessage("오류 발생")

        self.result_text.setHtml(f"<font color='red'><b>오류:</b> {error}</font>")

        if self.last_result and self.last_result.get('md_path'):
            QMessageBox.warning(
                self, "발행 실패",
                f"발행 실패, MD 파일은 저장됨\n\nMD: {self.last_result['md_path']}\n\n오류: {error}"
            )
        else:
            QMessageBox.critical(self, "오류", f"발행 실패:\n{error}")

    # ===== 외부 논문 검색 =====

    def search_external_paper(self):
        title = self.external_search_input.text().strip()
        if not title:
            QMessageBox.warning(self, "경고", "논문 제목을 입력해주세요.")
            return

        if title not in self.search_history:
            self.search_history.insert(0, title)
            save_search_history(self.search_history)
            self.completer.setModel(QStringListModel(self.search_history))

        self.statusBar().showMessage("논문 검색 준비 중...")

        # 검색에는 쿠키가 필요 없음 - Claude API만 사용
        # TistoryAutoPoster를 md_only 모드로 초기화 (쿠키 불필요)
        if self.poster is None:
            try:
                self.poster = TistoryAutoPoster(md_only=True)
            except Exception as e:
                self.search_result_text.setHtml(f"<font color='red'>❌ 초기화 실패: {e}</font>")
                return

        self.search_btn.setEnabled(False)
        self.search_result_text.setHtml("<i>검색 중...</i>")

        self.search_worker = SearchWorker(self.poster, title)
        self.search_worker.finished.connect(self.on_search_complete)
        self.search_worker.error.connect(self.on_search_error)
        self.search_worker.progress.connect(self.on_publish_progress)
        self.search_worker.start()

    def on_search_complete(self, paper):
        self.search_btn.setEnabled(True)

        if not paper or not paper.get('title'):
            self.search_result_text.setHtml(
                "<font color='orange'><b>검색 결과 없음</b></font><br>"
                "논문을 찾지 못했습니다. 제목을 다시 확인해주세요."
            )
            self.searched_paper = None
            self.external_publish_btn.setEnabled(False)
            self.external_preview_btn.setEnabled(False)
            self.statusBar().showMessage("검색 결과 없음")
            return

        self.searched_paper = paper
        self.statusBar().showMessage("검색 완료!")

        info = f"<b>제목:</b> {paper.get('title', 'N/A')}<br>"
        authors = paper.get('authors', [])
        if isinstance(authors, list):
            author_str = ', '.join(authors[:3])
            if len(authors) > 3:
                author_str += f" 외 {len(authors) - 3}명"
            info += f"<b>저자:</b> {author_str}<br>"
        info += f"<b>년도:</b> {paper.get('year', 'N/A')} | "
        info += f"<b>인용수:</b> {paper.get('citations', 'N/A')}"
        if paper.get('url'):
            info += f" | <a href='{paper['url']}'>논문 링크</a>"
        if paper.get('abstract'):
            abstract = paper.get('abstract', '')[:300]
            info += f"<br><b>초록:</b> {abstract}..."

        self.search_result_text.setHtml(info)

        self.external_publish_btn.setEnabled(True)
        self.external_preview_btn.setEnabled(True)

    def on_search_error(self, error):
        self.search_btn.setEnabled(True)
        self.searched_paper = None
        self.external_publish_btn.setEnabled(False)
        self.external_preview_btn.setEnabled(False)

        self.search_result_text.setHtml(f"<font color='red'><b>검색 오류:</b> {error}</font>")
        self.statusBar().showMessage("검색 오류 발생")

    def publish_external(self):
        if not self.searched_paper:
            QMessageBox.warning(self, "경고", "먼저 논문을 검색해주세요.")
            return

        # 발행 방식 선택 다이얼로그
        msg = QMessageBox(self)
        msg.setWindowTitle("발행 방식 선택")
        msg.setText(f"'{self.searched_paper.get('title', '')[:50]}...' 논문을 어떻게 발행하시겠습니까?")
        msg.setIcon(QMessageBox.Question)
        
        blog_btn = msg.addButton("📤 블로그 발행", QMessageBox.AcceptRole)
        md_btn = msg.addButton("💾 MD만 저장", QMessageBox.ActionRole)
        msg.addButton("취소", QMessageBox.RejectRole)
        
        msg.exec_()
        clicked = msg.clickedButton()
        
        if clicked == blog_btn:
            save_md_only = False
        elif clicked == md_btn:
            save_md_only = True
        else:
            return  # 취소
        
        self.run_external_publish(save_md_only=save_md_only)

    def run_external_publish(self, save_md_only):
        self.statusBar().showMessage("준비 중...")

        # MD만 저장 모드는 쿠키 체크 없이 바로 진행
        if save_md_only:
            try:
                self.poster = TistoryAutoPoster(md_only=True)
            except Exception as e:
                QMessageBox.critical(self, "오류", f"초기화 실패:\n{e}")
                return
        else:
            # 블로그 발행 시에만 쿠키가 필요한 TistoryAutoPoster 초기화
            if not self.ensure_poster():
                return

        self.set_buttons_enabled(False)

        self.external_worker = ExternalPublishWorker(
            self.poster, self.searched_paper, save_md_only
        )
        self.external_worker.finished.connect(self.on_publish_complete)
        self.external_worker.error.connect(self.on_publish_error)
        self.external_worker.progress.connect(self.on_publish_progress)
        self.external_worker.start()

    def clear_search(self):
        self.external_search_input.clear()
        self.search_result_text.clear()
        self.searched_paper = None
        self.external_publish_btn.setEnabled(False)
        self.external_preview_btn.setEnabled(False)
        self.statusBar().showMessage("검색 초기화됨")

    # ===== PDF 다운로드 (수동) =====

    def start_pdf_download(self, paper):
        """PDF 다운로드 시작"""
        url = paper.get('url', '')
        if not url or 'arxiv.org' not in url:
            QMessageBox.information(
                self, "안내",
                "현재 arXiv 논문만 PDF 다운로드를 지원합니다.\n\n"
                f"논문 URL: {url or '없음'}"
            )
            return

        # 저장 디렉토리
        pdf_dir = project_root / "pdfs"
        pdf_dir.mkdir(exist_ok=True)

        self.statusBar().showMessage("PDF 다운로드 중...")
        self.set_buttons_enabled(False)

        self.pdf_worker = PDFDownloadWorker(paper, str(pdf_dir))
        self.pdf_worker.finished.connect(self.on_pdf_download_complete)
        self.pdf_worker.error.connect(self.on_pdf_download_error)
        self.pdf_worker.progress.connect(self.on_pdf_download_progress)
        self.pdf_worker.start()

    def on_pdf_download_progress(self, progress):
        """PDF 다운로드 진행률"""
        self.statusBar().showMessage(f"PDF 다운로드 중... {progress}%")

    def on_pdf_download_complete(self, file_path):
        """PDF 다운로드 완료 - 자동 저장"""
        self.set_buttons_enabled(True)
        # 파일명만 추출해서 상태바에 표시
        filename = Path(file_path).name
        self.statusBar().showMessage(f"PDF 저장 완료: {filename}")

    def on_pdf_download_error(self, error):
        """PDF 다운로드 오류"""
        self.set_buttons_enabled(True)
        self.statusBar().showMessage("PDF 다운로드 실패")
        QMessageBox.warning(self, "다운로드 실패", error)

    def open_pdf_folder(self):
        """PDF 폴더 열기"""
        pdf_dir = project_root / "pdfs"
        pdf_dir.mkdir(exist_ok=True)

        if sys.platform == 'darwin':
            subprocess.run(['open', str(pdf_dir)])
        elif sys.platform == 'win32':
            subprocess.run(['explorer', str(pdf_dir)])
        else:
            subprocess.run(['xdg-open', str(pdf_dir)])

    # ===== 대기열 관련 메서드 =====

    def toggle_select_all(self, state):
        """전체 선택/해제"""
        check_state = Qt.Checked if state == Qt.Checked else Qt.Unchecked
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(check_state)

    def get_checked_papers(self):
        """체크된 논문들 가져오기"""
        checked = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                paper_idx = int(self.table.item(row, 1).text())
                paper = self.papers[paper_idx]
                checked.append((paper_idx, paper))
        return checked

    def add_selected_to_queue(self):
        """선택된 논문들을 대기열에 추가"""
        checked = self.get_checked_papers()
        if not checked:
            QMessageBox.warning(self, "경고", "체크박스로 논문을 선택해주세요.")
            return

        added_count = 0
        for paper_idx, paper in checked:
            # 중복 체크
            exists = any(q[1] == paper_idx for q in self.publish_queue)
            if not exists:
                self.queue_counter += 1
                self.publish_queue.append((self.queue_counter, paper_idx, paper))
                added_count += 1

        self.update_queue_display()
        self.statusBar().showMessage(f"{added_count}개 논문이 대기열에 추가됨 (총 {len(self.publish_queue)}개)")

        # 체크 해제
        self.select_all_check.setChecked(False)

    def clear_queue(self):
        """대기열 비우기"""
        if self.is_batch_running:
            QMessageBox.warning(self, "경고", "발행 중에는 대기열을 비울 수 없습니다.")
            return

        self.publish_queue = []
        self.update_queue_display()
        self.statusBar().showMessage("대기열이 비워졌습니다.")

    def update_queue_display(self):
        """대기열 UI 업데이트"""
        self.queue_list.setRowCount(0)

        for queue_idx, paper_idx, paper in self.publish_queue:
            row = self.queue_list.rowCount()
            self.queue_list.insertRow(row)

            # 상태 (아직 시작 안함)
            status_item = QTableWidgetItem("[-]")
            status_item.setData(Qt.UserRole, queue_idx)  # queue_idx 저장
            self.queue_list.setItem(row, 0, status_item)

            # 제목
            title = paper.get('title', 'Unknown')[:40]
            self.queue_list.setItem(row, 1, QTableWidgetItem(title))

            # 삭제 버튼
            delete_btn = QPushButton("✕")
            delete_btn.setFixedWidth(30)
            delete_btn.clicked.connect(lambda checked, qid=queue_idx: self.remove_from_queue(qid))
            self.queue_list.setCellWidget(row, 2, delete_btn)

        self.queue_list.setColumnWidth(0, 40)
        self.queue_list.setColumnWidth(2, 40)

        # 예상 시간 업데이트
        if self.publish_queue:
            total_seconds = len(self.publish_queue) * self.avg_publish_time
            minutes = total_seconds // 60
            self.estimated_time_label.setText(f"예상 시간: 약 {minutes}분")
        else:
            self.estimated_time_label.setText("예상 시간: -")

        self.queue_progress_label.setText(f"0/{len(self.publish_queue)} 대기 중")

    def remove_from_queue(self, queue_idx):
        """대기열에서 항목 제거"""
        if self.is_batch_running:
            QMessageBox.warning(self, "경고", "발행 중에는 항목을 제거할 수 없습니다.")
            return

        self.publish_queue = [q for q in self.publish_queue if q[0] != queue_idx]
        self.update_queue_display()

    def update_queue_item_status(self, queue_idx, status):
        """대기열 항목 상태 업데이트"""
        for row in range(self.queue_list.rowCount()):
            item = self.queue_list.item(row, 0)
            if item and item.data(Qt.UserRole) == queue_idx:
                item.setText(status)
                break

    def start_batch_publish(self):
        """배치 발행 시작"""
        if not self.publish_queue:
            QMessageBox.warning(self, "경고", "대기열이 비어있습니다.\n논문을 선택하고 '대기열 추가' 버튼을 눌러주세요.")
            return

        # 발행 방식 선택 다이얼로그
        msg = QMessageBox(self)
        msg.setWindowTitle("배치 발행 방식 선택")
        msg.setText(f"{len(self.publish_queue)}개 논문을 어떻게 발행하시겠습니까?")
        msg.setIcon(QMessageBox.Question)

        blog_btn = msg.addButton("📤 블로그 발행", QMessageBox.AcceptRole)
        md_btn = msg.addButton("💾 MD만 저장", QMessageBox.ActionRole)
        msg.addButton("취소", QMessageBox.RejectRole)

        msg.exec_()
        clicked = msg.clickedButton()

        if clicked == blog_btn:
            save_md_only = False
            # 블로그 발행 시에만 쿠키가 필요한 TistoryAutoPoster 초기화
            if not self.ensure_poster():
                return
        elif clicked == md_btn:
            save_md_only = True
            # MD 전용 모드로 poster 초기화 (쿠키 불필요)
            try:
                self.poster = TistoryAutoPoster(md_only=True)
            except Exception as e:
                QMessageBox.critical(self, "오류", f"초기화 실패:\n{e}")
                return
        else:
            return  # 취소

        self.is_batch_running = True
        self.is_batch_paused = False
        self.batch_start_time = datetime.now()

        self.set_batch_buttons_enabled(True)
        self.set_buttons_enabled(False)

        self.batch_worker = BatchPublishWorker(self.poster, self.publish_queue.copy(), save_md_only)
        self.batch_worker.paper_started.connect(self.on_batch_paper_started)
        self.batch_worker.paper_progress.connect(self.on_batch_paper_progress)
        self.batch_worker.paper_completed.connect(self.on_batch_paper_completed)
        self.batch_worker.paper_failed.connect(self.on_batch_paper_failed)
        self.batch_worker.queue_progress.connect(self.on_batch_queue_progress)
        self.batch_worker.all_completed.connect(self.on_batch_all_completed)
        self.batch_worker.start()

    def toggle_pause(self):
        """일시정지/재개"""
        if not self.batch_worker:
            return

        if self.is_batch_paused:
            self.batch_worker.resume()
            self.is_batch_paused = False
            self.pause_btn.setText("||")
            self.statusBar().showMessage("재개됨")
        else:
            self.batch_worker.pause()
            self.is_batch_paused = True
            self.pause_btn.setText("[>]")
            self.statusBar().showMessage("일시정지됨")

    def stop_batch_publish(self):
        """배치 발행 중지"""
        if self.batch_worker:
            self.batch_worker.stop()
            self.statusBar().showMessage("발행 중지 요청됨...")

    def set_batch_buttons_enabled(self, running):
        """배치 발행 버튼 상태 설정"""
        self.batch_publish_btn.setEnabled(not running)
        self.pause_btn.setEnabled(running)
        self.stop_batch_btn.setEnabled(running)
        self.add_to_queue_btn.setEnabled(not running)

    def on_batch_paper_started(self, queue_idx, title):
        """배치: 논문 발행 시작"""
        self.update_queue_item_status(queue_idx, "[*]")
        self.statusBar().showMessage(f"발행 중: {title}...")

    def on_batch_paper_progress(self, queue_idx, message):
        """배치: 논문 진행 상황"""
        self.statusBar().showMessage(message)

    def on_batch_paper_completed(self, queue_idx, result):
        """배치: 논문 발행 완료"""
        self.update_queue_item_status(queue_idx, "[O]")

        # 자동 PDF 다운로드
        paper = result.get('paper')
        if paper and 'arxiv.org' in paper.get('url', ''):
            pdf_dir = project_root / "pdfs"
            pdf_dir.mkdir(exist_ok=True)
            # 백그라운드에서 PDF 다운로드 (비동기, 결과 무시)
            worker = PDFDownloadWorker(paper, str(pdf_dir))
            worker.start()

    def on_batch_paper_failed(self, queue_idx, error):
        """배치: 논문 발행 실패"""
        self.update_queue_item_status(queue_idx, "[X]")

    def on_batch_queue_progress(self, current, total):
        """배치: 전체 진행률"""
        self.queue_progress_label.setText(f"{current}/{total} 발행 중")

        # 예상 남은 시간
        if current > 0 and self.batch_start_time:
            elapsed = (datetime.now() - self.batch_start_time).total_seconds()
            avg_time = elapsed / current
            remaining = (total - current) * avg_time
            minutes = int(remaining // 60)
            self.estimated_time_label.setText(f"예상 남은 시간: 약 {minutes}분")
            # 평균 시간 업데이트
            self.avg_publish_time = avg_time

    def on_batch_all_completed(self, results):
        """배치: 전체 완료"""
        self.is_batch_running = False
        self.is_batch_paused = False

        self.set_batch_buttons_enabled(False)
        self.set_buttons_enabled(True)

        # 결과 요약
        success_count = sum(1 for r in results if r.get('success'))
        fail_count = len(results) - success_count

        self.queue_progress_label.setText(f"완료! 성공:{success_count} 실패:{fail_count}")
        self.statusBar().showMessage(f"배치 발행 완료: 성공 {success_count}개, 실패 {fail_count}개")
        self.estimated_time_label.setText("예상 시간: -")

        # 대기열 비우기
        self.publish_queue = []

        # 테이블 새로고침
        self.load_papers()

        QMessageBox.information(
            self, "배치 발행 완료",
            f"총 {len(results)}개 논문 발행 완료\n\n"
            f"성공: {success_count}개\n"
            f"실패: {fail_count}개"
        )

    def open_url(self):
        if self.last_result and self.last_result.get('url'):
            webbrowser.open(self.last_result['url'])

    def open_output(self):
        output_dir = project_root / "output"
        output_dir.mkdir(exist_ok=True)

        if sys.platform == 'darwin':
            subprocess.run(['open', str(output_dir)])
        elif sys.platform == 'win32':
            subprocess.run(['explorer', str(output_dir)])
        else:
            subprocess.run(['xdg-open', str(output_dir)])

    # ===== 추천 기능 =====

    def on_recommend_select(self, index):
        """추천 콤보박스 선택"""
        if index == 0:  # "[?] 추천" 기본값
            return

        # 미리뷰 논문만 필터링
        unreviewed = []
        for i, paper in enumerate(self.papers):
            if not self.paper_manager.is_paper_reviewed(paper):
                unreviewed.append((i, paper))

        if not unreviewed:
            QMessageBox.information(self, "알림", "미리뷰 논문이 없습니다.")
            self.recommend_combo.setCurrentIndex(0)
            return

        selected_idx = None
        if index == 1:  # 랜덤 선택
            selected_idx, _ = random.choice(unreviewed)
            self.statusBar().showMessage("랜덤 논문 선택됨")
        elif index == 2:  # 인용수 높은 순
            unreviewed.sort(key=lambda x: x[1].get('citations', 0), reverse=True)
            selected_idx, _ = unreviewed[0]
            self.statusBar().showMessage("인용수 가장 높은 논문 선택됨")
        elif index == 3:  # 최신 논문
            unreviewed.sort(key=lambda x: x[1].get('year', 0), reverse=True)
            selected_idx, _ = unreviewed[0]
            self.statusBar().showMessage("가장 최신 논문 선택됨")

        if selected_idx is not None:
            self.select_paper_by_index(selected_idx)

        # 콤보박스 초기화
        self.recommend_combo.setCurrentIndex(0)

    def select_paper_by_index(self, paper_idx):
        """인덱스로 테이블에서 논문 선택"""
        for row in range(self.table.rowCount()):
            idx_item = self.table.item(row, 1)
            if idx_item and int(idx_item.text()) == paper_idx:
                self.table.selectRow(row)
                self.table.scrollToItem(idx_item)
                break

    # ===== 컨텍스트 메뉴 =====

    def show_table_context_menu(self, pos):
        """테이블 우클릭 메뉴"""
        item = self.table.itemAt(pos)
        if not item:
            return

        row = item.row()
        paper_idx = int(self.table.item(row, 1).text())
        paper = self.papers[paper_idx]

        menu = QMenu(self)

        # 미리보기
        preview_action = menu.addAction("미리보기")
        preview_action.triggered.connect(lambda: self.open_preview_dialog(paper))

        # 대기열 추가
        add_queue_action = menu.addAction("대기열에 추가")
        add_queue_action.triggered.connect(lambda: self.add_single_to_queue(paper_idx, paper))

        menu.addSeparator()

        # 단일 발행
        publish_action = menu.addAction("바로 발행")
        publish_action.triggered.connect(lambda: self.quick_publish(paper_idx))

        # URL 열기
        if paper.get('url'):
            menu.addSeparator()
            url_action = menu.addAction("논문 URL 열기")
            url_action.triggered.connect(lambda: webbrowser.open(paper['url']))

        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def add_single_to_queue(self, paper_idx, paper):
        """단일 논문을 대기열에 추가"""
        exists = any(q[1] == paper_idx for q in self.publish_queue)
        if exists:
            self.statusBar().showMessage("이미 대기열에 있습니다.")
            return

        self.queue_counter += 1
        self.publish_queue.append((self.queue_counter, paper_idx, paper))
        self.update_queue_display()
        self.statusBar().showMessage(f"대기열에 추가됨: {paper.get('title', '')[:30]}...")

    def quick_publish(self, paper_idx):
        """빠른 발행 (확인 없이)"""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "경고", "이미 발행 중입니다.")
            return

        self.selected_index = paper_idx
        self.run_publish(paper_idx, save_md_only=False)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = PaperPublishGUI()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
