#!/usr/bin/env python3
"""
CallIQ — AI-Powered Customer Support Quality Auditor
Premium Professional Edition
"""

import os
import json
import tempfile
import datetime
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
import requests
from pathlib import Path

# Milestone 4 — Alerts & Reports
try:
    from alerts import dispatch_alerts, evaluate_triggers, load_alert_log, DEFAULT_THRESHOLDS
    ALERTS_AVAILABLE = True
except ImportError:
    ALERTS_AVAILABLE = False

try:
    from report_exporter import build_pdf_report, build_excel_report
    REPORTS_AVAILABLE = True
except ImportError:
    REPORTS_AVAILABLE = False

# RAG Engine (Milestone 3)
try:
    from rag_engine import (
        ingest_policy_docs, retrieve_policy_context, rag_audit,
        list_policy_docs, get_index_stats, POLICY_DOCS_DIR, ensure_sample_policies,
    )
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="CallIQ — Support Quality Auditor",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================================
# PREMIUM CSS
# ============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, [class*="css"] { font-family: 'Inter', sans-serif; background: #050508; color: #e8e8f0; }
.stApp { background: #050508; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 2rem 4rem !important; max-width: 1400px; }
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #0d0d14; }
::-webkit-scrollbar-thumb { background: #ff4d6d; border-radius: 4px; }

/* HERO */
.hero-wrap {
    position: relative; overflow: hidden;
    background: linear-gradient(135deg, #07070f 0%, #0e0e1c 50%, #07070f 100%);
    border-bottom: 1px solid rgba(255,77,109,0.15);
    padding: 3.5rem 3rem 3rem;
    margin: 0 -2rem 2.5rem;
}
.hero-wrap::before {
    content: ''; position: absolute; inset: 0;
    background:
        radial-gradient(ellipse 60% 50% at 20% 50%, rgba(255,77,109,0.08) 0%, transparent 70%),
        radial-gradient(ellipse 40% 60% at 80% 30%, rgba(100,60,255,0.06) 0%, transparent 70%);
    pointer-events: none;
}
.hero-grid {
    position: absolute; inset: 0;
    background-image: linear-gradient(rgba(255,77,109,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,77,109,0.04) 1px, transparent 1px);
    background-size: 60px 60px; pointer-events: none;
}
.hero-content { position: relative; z-index: 2; }
.hero-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(255,77,109,0.1); border: 1px solid rgba(255,77,109,0.3);
    border-radius: 20px; padding: 4px 14px;
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: #ff4d6d;
    margin-bottom: 1.2rem;
}
.hero-badge::before {
    content: ''; width: 6px; height: 6px; background: #ff4d6d; border-radius: 50%;
    box-shadow: 0 0 8px #ff4d6d; animation: pulse-dot 2s infinite;
}
@keyframes pulse-dot { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.5;transform:scale(0.8)} }
.hero-title {
    font-family: 'Syne', sans-serif; font-size: 3.2rem; font-weight: 800;
    line-height: 1.05; letter-spacing: -0.03em; color: #f0f0f8; margin-bottom: 0.8rem;
}
.hero-title span {
    background: linear-gradient(135deg, #ff4d6d 0%, #ff8c42 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.hero-sub { font-size: 1rem; color: #7878a0; font-weight: 400; max-width: 520px; line-height: 1.6; }
.hero-stats { display: flex; gap: 2.5rem; margin-top: 2rem; }
.hero-stat-num { font-family: 'Syne', sans-serif; font-size: 1.6rem; font-weight: 700; color: #f0f0f8; }
.hero-stat-lbl { font-size: 0.75rem; color: #555570; text-transform: uppercase; letter-spacing: 0.08em; }

/* SECTION LABEL */
.sec-label {
    display: flex; align-items: center; gap: 10px;
    font-family: 'Syne', sans-serif; font-size: 0.7rem; font-weight: 700;
    letter-spacing: 0.15em; text-transform: uppercase; color: #ff4d6d; margin-bottom: 1rem;
}
.sec-label::after { content: ''; flex: 1; height: 1px; background: linear-gradient(90deg, rgba(255,77,109,0.3) 0%, transparent 100%); }

/* GLASS CARD */
.glass-card {
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px; padding: 1.5rem; position: relative; overflow: hidden; transition: border-color 0.3s;
}
.glass-card:hover { border-color: rgba(255,77,109,0.2); }
.glass-card::before {
    content: ''; position: absolute; inset: 0;
    background: linear-gradient(135deg, rgba(255,255,255,0.03) 0%, transparent 60%); pointer-events: none;
}

/* METRIC CARDS */
.metric-card {
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px; padding: 1.4rem 1.2rem; text-align: center;
    position: relative; overflow: hidden; transition: all 0.3s;
}
.metric-card:hover { transform: translateY(-3px); border-color: rgba(255,77,109,0.3); box-shadow: 0 12px 40px rgba(255,77,109,0.08); }
.metric-card::after {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #ff4d6d, #ff8c42);
}
.metric-lbl { font-size: 0.68rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: #555570; margin-bottom: 0.5rem; }
.metric-val { font-family: 'Syne', sans-serif; font-size: 2.4rem; font-weight: 800; color: #f0f0f8; line-height: 1; }
.metric-sub { font-size: 0.78rem; color: #555570; margin-top: 0.3rem; }
.metric-accent { color: #ff4d6d; }

/* PILLS */
.pill { display: inline-flex; align-items: center; gap: 5px; padding: 5px 14px; border-radius: 20px; font-size: 0.78rem; font-weight: 600; letter-spacing: 0.04em; }
.pill-positive { background: rgba(52,211,153,0.1); color: #34d399; border: 1px solid rgba(52,211,153,0.25); }
.pill-neutral  { background: rgba(251,191,36,0.1);  color: #fbbf24; border: 1px solid rgba(251,191,36,0.25); }
.pill-negative { background: rgba(248,113,113,0.1); color: #f87171; border: 1px solid rgba(248,113,113,0.25); }
.pill-low    { background: rgba(52,211,153,0.1); color: #34d399; border: 1px solid rgba(52,211,153,0.25); }
.pill-medium { background: rgba(251,191,36,0.1);  color: #fbbf24; border: 1px solid rgba(251,191,36,0.25); }
.pill-high   { background: rgba(248,113,113,0.1); color: #f87171; border: 1px solid rgba(248,113,113,0.25); }
.pill-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

/* DIMENSION BARS */
.dim-row { margin-bottom: 1.2rem; }
.dim-header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 5px; }
.dim-name { font-size: 0.85rem; font-weight: 500; color: #b0b0c8; }
.dim-score { font-family: 'Syne', sans-serif; font-size: 1rem; font-weight: 700; }
.dim-track { height: 6px; background: rgba(255,255,255,0.06); border-radius: 6px; overflow: hidden; }
.dim-fill  { height: 100%; border-radius: 6px; }
.dim-desc  { font-size: 0.75rem; color: #444460; margin-top: 4px; font-style: italic; }

/* TRANSCRIPT */
.transcript-box {
    background: #08080f; border: 1px solid rgba(255,255,255,0.06); border-radius: 12px;
    padding: 1.2rem 1.4rem; font-family: 'SF Mono','Fira Code','Consolas',monospace;
    font-size: 0.82rem; color: #8888aa; line-height: 1.75;
    max-height: 280px; overflow-y: auto; white-space: pre-wrap; position: relative;
}
.transcript-box::before {
    content: 'TRANSCRIPT'; position: absolute; top: 10px; right: 14px;
    font-size: 0.6rem; letter-spacing: 0.15em; color: #2a2a44; font-weight: 700;
}

/* VIOLATION / SUGGESTION */
.violation-item {
    display: flex; align-items: flex-start; gap: 10px;
    background: rgba(248,113,113,0.05); border: 1px solid rgba(248,113,113,0.15);
    border-radius: 10px; padding: 0.75rem 1rem; margin: 0.4rem 0;
    font-size: 0.85rem; color: #f8a0a0;
}
.suggestion-item {
    display: flex; align-items: flex-start; gap: 10px;
    background: rgba(52,211,153,0.04); border: 1px solid rgba(52,211,153,0.12);
    border-radius: 10px; padding: 0.75rem 1rem; margin: 0.4rem 0;
    font-size: 0.85rem; color: #a0e8cc;
}
.item-icon { flex-shrink: 0; width: 20px; height: 20px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.7rem; font-weight: 700; }
.icon-v { background: rgba(248,113,113,0.2); color: #f87171; }
.icon-s { background: rgba(52,211,153,0.2); color: #34d399; }

/* KEYWORD CHIPS */
.kw-chip {
    display: inline-block; background: rgba(251,191,36,0.08); border: 1px solid rgba(251,191,36,0.2);
    color: #fbbf24; padding: 3px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 500; margin: 3px;
}

/* GRADE CIRCLE */
.grade-circle {
    width: 72px; height: 72px; border-radius: 50%; border: 3px solid #ff4d6d;
    display: flex; align-items: center; justify-content: center; margin: 0 auto 0.5rem;
    background: rgba(255,77,109,0.08); box-shadow: 0 0 30px rgba(255,77,109,0.15), inset 0 0 20px rgba(255,77,109,0.05);
}
.grade-letter { font-family: 'Syne', sans-serif; font-size: 1.8rem; font-weight: 800; color: #ff4d6d; }

/* STREAMLIT OVERRIDES */
.stButton > button {
    background: linear-gradient(135deg, #ff4d6d 0%, #e63950 100%) !important;
    color: #fff !important; border: none !important; border-radius: 10px !important;
    font-family: 'Syne', sans-serif !important; font-weight: 700 !important;
    font-size: 0.9rem !important; letter-spacing: 0.05em !important;
    padding: 0.7rem 1.5rem !important; transition: all 0.2s !important;
    box-shadow: 0 4px 20px rgba(255,77,109,0.3) !important;
}
.stButton > button:hover { transform: translateY(-2px) !important; box-shadow: 0 8px 30px rgba(255,77,109,0.45) !important; }
.stDownloadButton > button {
    background: rgba(255,77,109,0.08) !important; color: #ff4d6d !important;
    border: 1px solid rgba(255,77,109,0.3) !important; border-radius: 10px !important;
    font-family: 'Syne', sans-serif !important; font-weight: 600 !important;
}
.stDownloadButton > button:hover { background: rgba(255,77,109,0.15) !important; }
div[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.02) !important; border: 2px dashed rgba(255,77,109,0.2) !important;
    border-radius: 14px !important; padding: 1rem !important; transition: all 0.3s !important;
}
div[data-testid="stFileUploader"]:hover { border-color: rgba(255,77,109,0.45) !important; background: rgba(255,77,109,0.03) !important; }
.stTabs [data-baseweb="tab-list"] { background: transparent !important; gap: 0.5rem !important; border-bottom: 1px solid rgba(255,255,255,0.06) !important; }
.stTabs [data-baseweb="tab"] {
    background: transparent !important; border-radius: 8px 8px 0 0 !important; color: #555570 !important;
    font-family: 'Syne', sans-serif !important; font-weight: 600 !important; font-size: 0.82rem !important;
    letter-spacing: 0.06em !important; text-transform: uppercase !important; padding: 0.6rem 1.4rem !important;
    border: none !important; transition: color 0.2s !important;
}
.stTabs [aria-selected="true"] { color: #ff4d6d !important; background: rgba(255,77,109,0.06) !important; border-bottom: 2px solid #ff4d6d !important; }
div[data-testid="metric-container"] { background: rgba(255,255,255,0.02) !important; border: 1px solid rgba(255,255,255,0.07) !important; border-radius: 12px !important; padding: 1rem !important; }
div[data-testid="metric-container"] label { color: #555570 !important; font-size: 0.72rem !important; letter-spacing: 0.08em !important; text-transform: uppercase !important; font-weight: 600 !important; }
div[data-testid="metric-container"] [data-testid="stMetricValue"] { color: #f0f0f8 !important; font-family: 'Syne', sans-serif !important; font-size: 1.8rem !important; font-weight: 800 !important; }
.stExpander { background: rgba(255,255,255,0.02) !important; border: 1px solid rgba(255,255,255,0.07) !important; border-radius: 12px !important; }
.stExpander summary { color: #7878a0 !important; font-size: 0.85rem !important; }
.stDataFrame table { background: #08080f !important; }
.stDataFrame th { background: rgba(255,77,109,0.08) !important; color: #ff4d6d !important; font-family: 'Syne', sans-serif !important; font-size: 0.72rem !important; letter-spacing: 0.08em !important; text-transform: uppercase !important; border: none !important; }
.stDataFrame td { color: #a0a0c0 !important; border-color: rgba(255,255,255,0.04) !important; font-size: 0.84rem !important; }
.stSpinner > div { border-top-color: #ff4d6d !important; }
hr { border-color: rgba(255,255,255,0.06) !important; }

/* RAG STYLES */
.rag-chunk-card {
    background: rgba(100,60,255,0.05); border: 1px solid rgba(100,60,255,0.18);
    border-radius: 12px; padding: 1rem 1.2rem; margin-bottom: 0.7rem;
}
.rag-chunk-source { font-size: 0.68rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #7c5ff5; margin-bottom: 0.3rem; }
.rag-chunk-score { font-size: 0.68rem; color: #444460; margin-bottom: 0.5rem; }
.rag-chunk-text { font-size: 0.83rem; color: #9898bb; line-height: 1.6; }
.rag-policy-card {
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px; padding: 0.9rem 1.1rem; margin-bottom: 0.6rem;
}
.rag-policy-name { font-size: 0.82rem; font-weight: 600; color: #c0c0e0; }
.rag-policy-meta { font-size: 0.72rem; color: #444460; margin-top: 0.2rem; }
.rag-policy-preview { font-size: 0.78rem; color: #666688; margin-top: 0.5rem; line-height: 1.5; font-style: italic; }
.rag-violation-item {
    display: flex; align-items: flex-start; gap: 10px;
    background: rgba(248,113,113,0.05); border: 1px solid rgba(248,113,113,0.18);
    border-radius: 10px; padding: 0.75rem 1rem; margin: 0.4rem 0;
    font-size: 0.85rem; color: #f8a0a0;
}
.rag-compliant-item {
    display: flex; align-items: flex-start; gap: 10px;
    background: rgba(52,211,153,0.04); border: 1px solid rgba(52,211,153,0.15);
    border-radius: 10px; padding: 0.75rem 1rem; margin: 0.4rem 0;
    font-size: 0.85rem; color: #a0e8cc;
}
.rag-coaching-box {
    background: rgba(96,165,250,0.05); border: 1px solid rgba(96,165,250,0.18);
    border-radius: 12px; padding: 1rem 1.2rem; margin-bottom: 1rem;
}
.rag-coaching-label { font-size: 0.68rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #60a5fa; margin-bottom: 0.5rem; }
.rag-coaching-text { font-size: 0.88rem; color: #b0c8e8; line-height: 1.7; }
.rag-index-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(52,211,153,0.08); border: 1px solid rgba(52,211,153,0.25);
    border-radius: 20px; padding: 4px 12px; font-size: 0.75rem; font-weight: 600; color: #34d399;
}
.rag-index-badge-off {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(255,77,109,0.06); border: 1px solid rgba(255,77,109,0.2);
    border-radius: 20px; padding: 4px 12px; font-size: 0.75rem; font-weight: 600; color: #ff4d6d;
}

/* ALERT STYLES */
.alert-card-critical {
    background: rgba(248,113,113,0.06); border: 1px solid rgba(248,113,113,0.3);
    border-left: 4px solid #f87171; border-radius: 12px; padding: 1rem 1.2rem; margin-bottom: 0.6rem;
}
.alert-card-warning {
    background: rgba(251,191,36,0.05); border: 1px solid rgba(251,191,36,0.25);
    border-left: 4px solid #fbbf24; border-radius: 12px; padding: 1rem 1.2rem; margin-bottom: 0.6rem;
}
.alert-title { font-size: 0.88rem; font-weight: 700; color: #e0e0f0; margin-bottom: 0.3rem; }
.alert-detail { font-size: 0.8rem; color: #888899; line-height: 1.5; }
.alert-meta { font-size: 0.7rem; color: #444460; margin-top: 0.4rem; }
.alert-badge-critical { background: rgba(248,113,113,0.12); color: #f87171; border: 1px solid rgba(248,113,113,0.3); padding: 2px 10px; border-radius: 6px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; }
.alert-badge-warning  { background: rgba(251,191,36,0.1);  color: #fbbf24; border: 1px solid rgba(251,191,36,0.25);  padding: 2px 10px; border-radius: 6px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; }

/* STRENGTHS */
.strength-item {
    display: flex; align-items: flex-start; gap: 10px;
    padding: 0.6rem 0; border-bottom: 1px solid rgba(255,255,255,0.04);
}
.strength-item:last-child { border-bottom: none; }
.strength-dot { width: 8px; height: 8px; border-radius: 50%; background: #34d399; flex-shrink: 0; margin-top: 5px; box-shadow: 0 0 8px rgba(52,211,153,0.4); }
.strength-text { font-size: 0.85rem; color: #a0e8cc; line-height: 1.4; }

/* CALL SUMMARY */
.call-summary-box {
    background: rgba(96,165,250,0.05); border: 1px solid rgba(96,165,250,0.15);
    border-radius: 12px; padding: 1rem 1.2rem; margin-bottom: 1.2rem;
}
.call-summary-label { font-size: 0.68rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #60a5fa; margin-bottom: 0.4rem; }
.call-summary-text { font-size: 0.88rem; color: #b0c8e8; line-height: 1.6; }

/* SUGGESTION CARDS */
.sugg-card {
    background: rgba(255,255,255,0.025); border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px; margin-bottom: 0.7rem; overflow: hidden; transition: border-color 0.25s;
}
.sugg-card:hover { border-color: rgba(255,255,255,0.14); }
.sugg-header {
    display: flex; align-items: center; gap: 10px;
    padding: 0.85rem 1rem; cursor: pointer; user-select: none;
}
.sugg-priority-dot {
    width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0;
}
.priority-High   { background: #f87171; box-shadow: 0 0 8px rgba(248,113,113,0.5); }
.priority-Medium { background: #fbbf24; box-shadow: 0 0 8px rgba(251,191,36,0.4); }
.priority-Low    { background: #34d399; box-shadow: 0 0 8px rgba(52,211,153,0.4); }
.sugg-title { font-size: 0.88rem; font-weight: 600; color: #d0d0e8; flex: 1; }
.sugg-meta { display: flex; align-items: center; gap: 6px; }
.sugg-cat-tag {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
    padding: 2px 8px; border-radius: 5px; background: rgba(255,255,255,0.05); color: #666688;
    border: 1px solid rgba(255,255,255,0.07);
}
.sugg-pri-tag {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
    padding: 2px 8px; border-radius: 5px;
}
.pri-High   { background: rgba(248,113,113,0.1); color: #f87171; border: 1px solid rgba(248,113,113,0.25); }
.pri-Medium { background: rgba(251,191,36,0.1);  color: #fbbf24; border: 1px solid rgba(251,191,36,0.25); }
.pri-Low    { background: rgba(52,211,153,0.1);  color: #34d399; border: 1px solid rgba(52,211,153,0.25); }
.sugg-chevron { color: #333350; font-size: 1.1rem; transition: transform 0.25s; }
.sugg-chevron.open { transform: rotate(90deg); color: #a0a0c0; }
.sugg-body {
    display: none; padding: 0 1rem 1rem;
    border-top: 1px solid rgba(255,255,255,0.05);
    animation: fadeSlide 0.2s ease;
}
.sugg-body.open { display: block; }
.sugg-row { display: flex; gap: 8px; margin-top: 0.7rem; align-items: flex-start; }
.sugg-row-icon { font-size: 0.75rem; margin-top: 2px; flex-shrink: 0; width: 18px; text-align: center; }
.sugg-row-label { font-size: 0.68rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #444460; min-width: 52px; margin-top: 2px; }
.sugg-row-text { font-size: 0.83rem; color: #a0a0c0; line-height: 1.5; flex: 1; }
.sugg-example-box {
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px;
    padding: 0.6rem 0.9rem; margin-top: 0.7rem; font-size: 0.82rem;
    color: #8888bb; font-style: italic; line-height: 1.5;
}
.sugg-example-box::before { content: '💬 '; font-style: normal; }

/* EXPANDABLE DIMENSION CARDS */
.dim-card {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    margin-bottom: 0.6rem;
    overflow: hidden;
    transition: border-color 0.25s, box-shadow 0.25s;
}
.dim-card:hover {
    border-color: rgba(255,77,109,0.25);
    box-shadow: 0 4px 24px rgba(255,77,109,0.06);
}
.dim-card-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0.85rem 1rem 0.4rem;
    cursor: pointer; user-select: none;
}
.dim-left { display: flex; align-items: center; gap: 10px; }
.dim-icon { font-size: 1.15rem; }
.dim-name { color: #c8c8e0; font-size: 0.88rem; font-weight: 600; margin-bottom: 2px; }
.dim-stars { font-size: 0.8rem; letter-spacing: 1px; }
.dim-right { display: flex; align-items: center; gap: 10px; }
.dim-grade-tag {
    font-size: 0.68rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
    padding: 2px 8px; border-radius: 6px;
}
.dim-score-num {
    font-family: 'Syne', sans-serif; font-size: 1.3rem; font-weight: 800; min-width: 36px; text-align: right;
}
.dim-chevron {
    color: #444460; font-size: 1.2rem; font-weight: 300; transition: transform 0.25s; display: inline-block;
}
.dim-chevron.open { transform: rotate(90deg); color: #ff4d6d; }
.dim-track {
    height: 4px; background: rgba(255,255,255,0.05); margin: 0 1rem 0;
    border-radius: 4px; overflow: hidden;
}
.dim-fill { height: 100%; border-radius: 4px; transition: width 0.8s cubic-bezier(0.16,1,0.3,1); }
.dim-body {
    display: none;
    padding: 0.8rem 1rem 1rem;
    border-top: 1px solid rgba(255,255,255,0.05);
    animation: fadeSlide 0.2s ease;
}
.dim-body.open { display: block; }
@keyframes fadeSlide { from{opacity:0;transform:translateY(-6px)} to{opacity:1;transform:translateY(0)} }
.dim-ai-verdict {
    background: rgba(255,77,109,0.05); border: 1px solid rgba(255,77,109,0.12);
    border-radius: 10px; padding: 0.7rem 0.9rem; margin-bottom: 0.6rem;
}
.dim-verdict-label {
    font-size: 0.68rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
    color: #ff4d6d; margin-bottom: 0.35rem;
}
.dim-verdict-text { font-size: 0.84rem; color: #c0c0d8; line-height: 1.55; }
.dim-what-it-means {
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px; padding: 0.7rem 0.9rem;
}
.dim-means-label {
    font-size: 0.68rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
    color: #555570; margin-bottom: 0.35rem;
}
.dim-means-text { font-size: 0.82rem; color: #666688; line-height: 1.55; }
</style>

<script>
function toggleDim(key) {
    const body = document.getElementById('body-' + key);
    const chev = document.getElementById('chev-' + key);
    if (!body || !chev) return;
    const isOpen = body.classList.contains('open');
    body.classList.toggle('open', !isOpen);
    chev.classList.toggle('open', !isOpen);
}
function toggleSugg(key) {
    const body = document.getElementById('sbody-' + key);
    const chev = document.getElementById('schev-' + key);
    if (!body || !chev) return;
    const isOpen = body.classList.contains('open');
    body.classList.toggle('open', !isOpen);
    chev.classList.toggle('open', !isOpen);
}
</script>
""", unsafe_allow_html=True)

# ============================================================================
# API CONFIG
# ============================================================================
DEEPGRAM_API_KEY   = os.getenv("7f0f9f23ffcd19f0652f103047a3799bd6b85945", "")
OPENROUTER_API_KEY = os.getenv("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", "")
OPENAI_API_KEY     = os.getenv("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", "")
CSV_PATH           = "evaluations_history.csv"

COMPLIANCE_KEYWORDS = [
    "refund","lawsuit","legal action","sue","complaint","fraud","scam","cancel",
    "unacceptable","terrible","horrible","never again","speak to manager",
    "supervisor","escalate","data breach","privacy","discrimination","harassment"
]

# ============================================================================
# SESSION STATE
# ============================================================================
if "history" not in st.session_state:
    st.session_state.history = []
if "rag_result" not in st.session_state:
    st.session_state.rag_result = None
if "rag_transcript" not in st.session_state:
    st.session_state.rag_transcript = None
if "alert_config" not in st.session_state:
    st.session_state.alert_config = {
        "email_enabled": False, "smtp_host": "", "smtp_port": 587,
        "smtp_user": "", "smtp_password": "", "from_addr": "", "to_addrs_str": "",
        "slack_enabled": False, "slack_webhook_url": "",
        "teams_enabled": False, "teams_webhook_url": "",
    }
if "alert_thresholds" not in st.session_state:
    st.session_state.alert_thresholds = {
        "score_below": 10, "escalation_high": True, "any_violation": True,
        "critical_keywords": ["lawsuit", "legal action", "fraud", "data breach", "discrimination", "harassment"],
        "negative_low_score": True,
    }
if "last_alert_result" not in st.session_state:
    st.session_state.last_alert_result = None

# ============================================================================
# HELPERS
# ============================================================================
def load_history_from_csv():
    if os.path.exists(CSV_PATH):
        try: return pd.read_csv(CSV_PATH)
        except: pass
    return pd.DataFrame()

def save_to_csv(result):
    row = {
        "timestamp": result.get("timestamp"), "filename": result.get("filename"),
        "greeting_quality": result.get("scores",{}).get("greeting_quality",0),
        "empathy": result.get("scores",{}).get("empathy",0),
        "problem_understanding": result.get("scores",{}).get("problem_understanding",0),
        "resolution_clarity": result.get("scores",{}).get("resolution_clarity",0),
        "professionalism": result.get("scores",{}).get("professionalism",0),
        "total_score": result.get("total_score",0),
        "customer_sentiment": result.get("customer_sentiment",""),
        "escalation_risk": result.get("escalation_risk",""),
    }
    df_new = pd.DataFrame([row])
    if os.path.exists(CSV_PATH):
        df_combined = pd.concat([pd.read_csv(CSV_PATH), df_new], ignore_index=True)
    else:
        df_combined = df_new
    df_combined.to_csv(CSV_PATH, index=False)
    return df_combined

def detect_compliance_keywords(text):
    t = text.lower()
    return [kw for kw in COMPLIANCE_KEYWORDS if kw in t]

def score_color(v):
    return "#34d399" if v >= 4 else ("#fbbf24" if v >= 3 else "#f87171")

def grade(total):
    pct = int((total/25)*100)
    g = "A" if pct>=90 else ("B" if pct>=75 else ("C" if pct>=60 else ("D" if pct>=50 else "F")))
    return g, pct

# ============================================================================
# TRANSCRIPTION
# ============================================================================
def transcribe_with_deepgram(audio_bytes, content_type="audio/wav"):
    params = {"model":"nova-2","smart_format":"true","punctuate":"true","diarize":"true","language":"en-US"}
    headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}", "Content-Type": content_type}
    resp = requests.post("https://api.deepgram.com/v1/listen", headers=headers, params=params, data=audio_bytes, timeout=120)
    resp.raise_for_status()
    return resp.json()["results"]["channels"][0]["alternatives"][0]["transcript"]

def mock_transcription(filename):
    return f"""[Demo Transcript — {filename}]

Agent: Thank you for calling TechSupport Pro, this is Sarah speaking. How can I assist you today?

Customer: Hi Sarah. I've been having issues with my internet connection for the past three days. It keeps dropping every hour and it's really impacting my work from home.

Agent: I completely understand how disruptive that must be, especially when you're working from home. I sincerely apologize for the inconvenience. Let me pull up your account right away — could I get your account number?

Customer: It's 548-221-XY.

Agent: Thank you. I can see your account here, Mr. Johnson. I'm running a diagnostic on your line now. While that processes — have you tried restarting your router?

Customer: Yes, multiple times. It only helps for a few minutes before dropping again.

Agent: I see. The diagnostic is showing signal instability on your line. This points to either a hardware fault in the router or an issue at the junction box outside. Given the repeated drops, I'd like to escalate this to our field engineering team and get a technician out to you.

Customer: Will there be a charge for that visit?

Agent: Absolutely not — since this is a confirmed service issue on our end, the technician visit is completely covered. I'm scheduling it for tomorrow between 10 AM and 2 PM. You'll get a confirmation SMS within the hour.

Customer: Perfect, thank you for resolving this so quickly, Sarah.

Agent: My pleasure! Is there anything else I can help with today?

Customer: No, that's everything. Thanks again.

Agent: Wonderful. Have a great rest of your day, and we'll have this fully resolved for you tomorrow. Goodbye!"""

def extract_and_transcribe(uploaded_file):
    file_ext = Path(uploaded_file.name).suffix.lower()
    file_bytes = uploaded_file.read()
    AUDIO_EXTS = {".mp3",".wav",".ogg",".flac",".aac",".m4a",".webm",".opus"}
    VIDEO_EXTS = {".mp4",".mov",".avi",".mkv",".wmv",".mpeg",".mpg"}
    ct_map = {".mp3":"audio/mpeg",".wav":"audio/wav",".ogg":"audio/ogg",".flac":"audio/flac",
              ".aac":"audio/aac",".m4a":"audio/m4a",".webm":"audio/webm",".opus":"audio/opus"}
    with st.spinner("🎙️ Transcribing audio via Deepgram..."):
        if file_ext in AUDIO_EXTS:
            if DEEPGRAM_API_KEY:
                try: return transcribe_with_deepgram(file_bytes, ct_map.get(file_ext,"audio/wav"))
                except Exception as e: st.warning(f"Deepgram: {e} — using demo transcript.")
            return mock_transcription(uploaded_file.name)
        elif file_ext in VIDEO_EXTS:
            try:
                from moviepy.editor import VideoFileClip
                with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp:
                    tmp.write(file_bytes); tmp_path = tmp.name
                wav_path = tmp_path.replace(file_ext, ".wav")
                clip = VideoFileClip(tmp_path)
                clip.audio.write_audiofile(wav_path, verbose=False, logger=None)
                clip.close()
                with open(wav_path,"rb") as wf: wav_bytes = wf.read()
                os.unlink(tmp_path); os.unlink(wav_path)
                if DEEPGRAM_API_KEY:
                    try: return transcribe_with_deepgram(wav_bytes,"audio/wav")
                    except Exception as e: st.warning(f"Deepgram: {e} — using demo transcript.")
                return mock_transcription(uploaded_file.name)
            except ImportError:
                st.error("moviepy not installed. Run: pip install moviepy")
                return mock_transcription(uploaded_file.name)
            except Exception as e:
                st.warning(f"Video processing: {e} — using demo transcript.")
                return mock_transcription(uploaded_file.name)
        else:
            st.error(f"Unsupported format: {file_ext}"); return None

# ============================================================================
# LLM EVALUATION
# ============================================================================
EVAL_PROMPT = """You are a senior customer support quality auditor with 15 years of experience coaching call center agents. Analyze the transcript carefully and return ONLY valid JSON — no markdown, no explanation, no preamble.

Score each dimension 0–5:
- greeting_quality: Warmth, professionalism, proper self-introduction, brand representation
- empathy: Acknowledging feelings, validating frustration, genuine human connection
- problem_understanding: Active listening, probing questions, correct issue diagnosis
- resolution_clarity: Clear solution, actionable next steps, timelines, no ambiguity
- professionalism: Language quality, composure, avoidance of negative language, brand voice

For improvement_suggestions, return an array of objects — each with:
- "category": one of ["Greeting & Opening", "Empathy & Rapport", "Problem Diagnosis", "Resolution & Closing", "Language & Tone", "Compliance", "Process"]
- "priority": "High", "Medium", or "Low"
- "title": short action title (max 8 words)
- "issue": one sentence describing what went wrong or could be better
- "action": one concrete sentence the agent should do differently next time
- "example": a short example phrase or script the agent could use (in quotes)
- "dimension": which score dimension this maps to (or "general")

Return exactly this JSON:
{
  "scores": {
    "greeting_quality": <int 0-5>,
    "empathy": <int 0-5>,
    "problem_understanding": <int 0-5>,
    "resolution_clarity": <int 0-5>,
    "professionalism": <int 0-5>
  },
  "score_descriptions": {
    "greeting_quality": "<one sentence>",
    "empathy": "<one sentence>",
    "problem_understanding": "<one sentence>",
    "resolution_clarity": "<one sentence>",
    "professionalism": "<one sentence>"
  },
  "total_score": <int 0-25>,
  "customer_sentiment": "<Positive|Neutral|Negative>",
  "escalation_risk": "<Low|Medium|High>",
  "call_summary": "<2-sentence overall summary of the call>",
  "agent_strengths": ["<strength1>", "<strength2>", "<strength3>"],
  "compliance_violations": ["<violation1>"],
  "improvement_suggestions": [
    {
      "category": "<category>",
      "priority": "<High|Medium|Low>",
      "title": "<short title>",
      "issue": "<what went wrong>",
      "action": "<what to do differently>",
      "example": "<example phrase>",
      "dimension": "<dimension or general>"
    }
  ]
}

Transcript:
"""

def evaluate_with_openrouter(transcript):
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
        json={"model":"openai/gpt-4o-mini",
              "messages":[{"role":"system","content":"You are a senior customer support quality auditor. Respond only with valid JSON, no markdown."},
                          {"role":"user","content":EVAL_PROMPT+transcript}],
              "temperature":0.2,"max_tokens":1800},
        timeout=60
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"].strip()
    content = content.replace("```json","").replace("```","").strip()
    return json.loads(content)

def mock_evaluation(transcript):
    import random; random.seed(len(transcript))
    scores = {k: random.randint(3,5) for k in ["greeting_quality","empathy","problem_understanding","resolution_clarity","professionalism"]}
    total = sum(scores.values())
    return {
        "scores": scores,
        "score_descriptions": {
            "greeting_quality":"Agent introduced themselves clearly with a warm, professional tone.",
            "empathy":"Agent acknowledged customer frustration and expressed genuine understanding.",
            "problem_understanding":"Agent correctly identified the root cause through targeted questions.",
            "resolution_clarity":"Solution and next steps were communicated clearly and concisely.",
            "professionalism":"Tone remained consistently courteous and professional throughout.",
        },
        "total_score": total,
        "customer_sentiment": "Positive" if total>=20 else ("Neutral" if total>=13 else "Negative"),
        "escalation_risk": "Low" if total>=20 else ("Medium" if total>=13 else "High"),
        "call_summary": "The agent handled a connectivity complaint, ran a diagnostic, and scheduled a free technician visit. The customer expressed satisfaction with the resolution provided.",
        "agent_strengths": [
            "Proactively ran a line diagnostic without being asked",
            "Clearly communicated no-charge policy for the technician visit",
            "Maintained a calm, empathetic tone throughout the interaction",
        ],
        "compliance_violations": [],
        "improvement_suggestions": [
            {
                "category": "Greeting & Opening",
                "priority": "Medium",
                "title": "Use customer name earlier in the call",
                "issue": "The agent did not address the customer by name until mid-call, missing an early personalization opportunity.",
                "action": "After verifying the account, immediately use the customer's name to make the interaction feel more personal and build rapport faster.",
                "example": '"Thank you, Mr. Johnson — I can see your account right here. Let me take a look at what\'s going on for you."',
                "dimension": "greeting_quality"
            },
            {
                "category": "Resolution & Closing",
                "priority": "High",
                "title": "Summarize resolution before closing",
                "issue": "The agent closed the call without recapping the agreed solution, leaving room for the customer to be unclear on next steps.",
                "action": "Before saying goodbye, always summarize what was agreed: the action taken, the timeline, and what the customer should expect.",
                "example": '"Just to recap — I\'ve scheduled a free technician visit for tomorrow between 10 AM and 2 PM, and you\'ll receive a confirmation SMS shortly. Does that all sound good?"',
                "dimension": "resolution_clarity"
            },
            {
                "category": "Empathy & Rapport",
                "priority": "Medium",
                "title": "Acknowledge business impact of the issue",
                "issue": "The customer mentioned the outage was affecting their work-from-home setup, but the agent did not specifically acknowledge this business impact.",
                "action": "When a customer mentions the issue affects their work or livelihood, explicitly validate that impact before moving to troubleshooting.",
                "example": '"That\'s completely understandable — when your internet is unreliable during work hours, it affects your whole day. Let\'s get this resolved as a priority."',
                "dimension": "empathy"
            },
            {
                "category": "Process",
                "priority": "Low",
                "title": "Offer self-service resources for future",
                "issue": "No self-service or proactive resources were offered, which could help the customer avoid a future call for a similar issue.",
                "action": "At the end of the call, mention any app, portal, or status page the customer can check themselves before calling support.",
                "example": '"Also, you can check our network status page at any time at support.techpro.com — it shows outages in your area in real time."',
                "dimension": "general"
            },
        ],
    }

def run_evaluation(transcript):
    if OPENROUTER_API_KEY:
        try: return evaluate_with_openrouter(transcript)
        except Exception as e: st.warning(f"LLM error: {e} — using demo scores.")
    return mock_evaluation(transcript)

# ============================================================================
# REPORT
# ============================================================================
def build_report(result, transcript):
    scores=result.get("scores",{}); descs=result.get("score_descriptions",{})
    g_ltr, g_pct = grade(result.get("total_score",0))
    lines = ["="*66, "        CALLIQ — CUSTOMER SUPPORT QUALITY AUDIT REPORT", "="*66,
             f"File            : {result.get('filename','')}",
             f"Timestamp       : {result.get('timestamp','')}",
             f"Total Score     : {result.get('total_score',0)} / 25",
             f"Grade           : {g_ltr}  ({g_pct}%)",
             f"Sentiment       : {result.get('customer_sentiment','')}",
             f"Escalation Risk : {result.get('escalation_risk','')}",
             ""]
    summary = result.get("call_summary","")
    if summary: lines += ["── CALL SUMMARY "+"─"*50, f"  {summary}", ""]
    strengths = result.get("agent_strengths",[])
    if strengths: lines += ["── AGENT STRENGTHS "+"─"*47]+[f"  ✓ {s}" for s in strengths]+[""]
    lines += ["── DIMENSION SCORES "+"─"*46]
    for k,lbl in [("greeting_quality","Greeting Quality"),("empathy","Empathy"),
                  ("problem_understanding","Problem Understanding"),
                  ("resolution_clarity","Resolution Clarity"),("professionalism","Professionalism")]:
        lines.append(f"  {lbl:<26}: {scores.get(k,0)}/5  — {descs.get(k,'')}")
    viols=result.get("compliance_violations",[])
    if viols: lines+=["","── COMPLIANCE VIOLATIONS "+"─"*41]+[f"  • {v}" for v in viols]
    kws=result.get("compliance_keywords",[])
    if kws: lines+=["","── COMPLIANCE KEYWORDS DETECTED "+"─"*34]+[f"  • {k}" for k in kws]
    suggs=result.get("improvement_suggestions",[])
    if suggs:
        lines+=["","── IMPROVEMENT SUGGESTIONS "+"─"*39]
        for i,s in enumerate(suggs):
            if isinstance(s, dict):
                pri = s.get("priority","")
                lines += [
                    f"",
                    f"  [{i+1}] {s.get('title','')}  [{pri} Priority]  [{s.get('category','')}]",
                    f"      Issue  : {s.get('issue','')}",
                    f"      Action : {s.get('action','')}",
                    f"      Example: {s.get('example','')}",
                ]
            else:
                lines.append(f"  {i+1}. {s}")
    lines+=["","── TRANSCRIPT "+"─"*51, transcript,"","="*66]
    return "\n".join(lines)

# ============================================================================
# CHARTS
# ============================================================================
def make_radar(scores):
    labels=["Greeting","Empathy","Problem\nUnderstanding","Resolution\nClarity","Professionalism"]
    vals=[scores.get(k,0) for k in ["greeting_quality","empathy","problem_understanding","resolution_clarity","professionalism"]]
    N=len(labels); angles=np.linspace(0,2*np.pi,N,endpoint=False).tolist()+[0]; vals_p=vals+vals[:1]
    fig,ax=plt.subplots(figsize=(4.5,4.5),subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("#08080f"); ax.set_facecolor("#08080f")
    ax.plot(angles,vals_p,"o-",lw=2.5,color="#ff4d6d",zorder=3)
    ax.fill(angles,vals_p,alpha=0.18,color="#ff4d6d")
    for angle,val in zip(angles[:-1],vals):
        c=score_color(val); ax.scatter([angle],[val],s=70,color=c,zorder=5,edgecolors="#08080f",linewidth=1.5)
    ax.set_xticks(angles[:-1]); ax.set_xticklabels(labels,color="#8888aa",size=8)
    ax.set_ylim(0,5); ax.set_yticks([1,2,3,4,5]); ax.set_yticklabels(["1","2","3","4","5"],color="#333350",size=7)
    ax.grid(color="#1a1a2e",lw=0.8); ax.spines["polar"].set_color("#1a1a2e")
    plt.tight_layout(pad=0.5); return fig

def make_bar(scores):
    labels=["Greeting","Empathy","Problem\nUnderst.","Resolution","Professional"]
    vals=[scores.get(k,0) for k in ["greeting_quality","empathy","problem_understanding","resolution_clarity","professionalism"]]
    colors=[score_color(v) for v in vals]
    fig,ax=plt.subplots(figsize=(6,3))
    fig.patch.set_facecolor("#08080f"); ax.set_facecolor("#08080f")
    bars=ax.bar(labels,vals,color=colors,width=0.55,zorder=2,edgecolor="#08080f",linewidth=1.5,alpha=0.9)
    for bar,val in zip(bars,vals):
        ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+0.08,str(val),ha="center",va="bottom",color="#e0e0f0",fontsize=10,fontweight="bold")
    ax.set_ylim(0,6); ax.set_yticks([0,1,2,3,4,5]); ax.tick_params(axis="y",colors="#555570",labelsize=8)
    ax.tick_params(axis="x",colors="#8888aa",labelsize=8)
    ax.axhline(3,color="#333350",lw=1,linestyle="--",zorder=1,alpha=0.5)
    for sp in ax.spines.values(): sp.set_color("#1a1a2e")
    ax.grid(axis="y",color="#1a1a2e",lw=0.8); plt.tight_layout(pad=0.5); return fig

def make_trend(df):
    fig,ax=plt.subplots(figsize=(10,3.5))
    fig.patch.set_facecolor("#08080f"); ax.set_facecolor("#08080f")
    x=np.arange(len(df))
    ax.fill_between(x,df["total_score"],alpha=0.08,color="#ff4d6d")
    ax.plot(x,df["total_score"],lw=2.5,color="#ff4d6d",zorder=3,marker="o",markersize=6,markerfacecolor="#ff4d6d",markeredgecolor="#08080f",markeredgewidth=1.5)
    dim_cfg=[("greeting_quality","#34d399"),("empathy","#60a5fa"),("problem_understanding","#fbbf24"),("resolution_clarity","#a78bfa"),("professionalism","#f87171")]
    for col,color in dim_cfg:
        if col in df.columns: ax.plot(x,df[col],lw=1,color=color,alpha=0.5,linestyle="--")
    ax.set_xticks(x)
    ax.set_xticklabels([str(n)[:18] for n in df.get("filename",range(len(df)))],rotation=25,ha="right",color="#555570",fontsize=8)
    ax.set_yticks(range(0,26,5)); ax.set_ylim(0,27); ax.tick_params(axis="y",colors="#555570",labelsize=8)
    ax.set_ylabel("Score",color="#555570",fontsize=9)
    for sp in ax.spines.values(): sp.set_color("#1a1a2e")
    ax.grid(axis="y",color="#1a1a2e",lw=0.8,linestyle="--")
    plt.tight_layout(pad=0.5); return fig

# ============================================================================
# HERO
# ============================================================================
df_all = load_history_from_csv()
avg_score = f"{df_all['total_score'].mean():.1f}" if not df_all.empty and "total_score" in df_all.columns else "—"
best_score = f"{int(df_all['total_score'].max())}" if not df_all.empty and "total_score" in df_all.columns else "—"
total_calls = len(df_all) if not df_all.empty else 0

st.markdown(f"""
<div class="hero-wrap">
  <div class="hero-grid"></div>
  <div class="hero-content">
    <div class="hero-badge">🎯 AI Quality Intelligence</div>
    <div class="hero-title">Call<span>IQ</span></div>
    <div class="hero-sub">Evaluate customer support interactions with AI-powered scoring across 5 performance dimensions. Upload a transcript, audio, or video to get started.</div>
    <div class="hero-stats">
      <div><div class="hero-stat-num">{total_calls}</div><div class="hero-stat-lbl">Calls Analyzed</div></div>
      <div><div class="hero-stat-num">{avg_score}</div><div class="hero-stat-lbl">Avg Score / 25</div></div>
      <div><div class="hero-stat-num">{best_score}</div><div class="hero-stat-lbl">Best Score</div></div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# TABS
# ============================================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["  🎧  Analyze  ", "  📈  History & Trends  ", "  🔍  Policy RAG Audit  ", "  🔔  Alerts & Reports  ", "  ℹ️  About  "])

# ===========================================================================
# TAB 1
# ===========================================================================
with tab1:
    col_left, col_right = st.columns([1, 1.3], gap="large")

    with col_left:
        st.markdown('<div class="sec-label">Upload Recording</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "Drop a file or click to browse",
            type=["txt","mp4","mp3","wav","m4a","ogg","flac","aac","mov","avi","mkv","mpeg","mpg"],
            label_visibility="collapsed"
        )
        st.markdown('<div style="text-align:center;color:#333350;font-size:0.75rem;margin-top:0.5rem">Supported: .txt · .mp4 · .mpeg · .mp3 · .wav · .m4a · .ogg · .flac · .mov · .avi</div>', unsafe_allow_html=True)

        if uploaded:
            fsize = uploaded.size/1024
            funit = "KB" if fsize<1024 else "MB"
            fsize_d = fsize if fsize<1024 else fsize/1024
            icon = "📄" if uploaded.name.endswith(".txt") else ("🎵" if any(uploaded.name.endswith(x) for x in [".mp3",".wav",".m4a",".ogg",".flac"]) else "🎬")
            st.markdown(f"""
<div class="glass-card" style="margin-top:1rem">
  <div style="display:flex;align-items:center;gap:12px">
    <div style="font-size:2rem">{icon}</div>
    <div>
      <div style="color:#e0e0f0;font-weight:600;font-size:0.9rem">{uploaded.name}</div>
      <div style="color:#555570;font-size:0.75rem">{fsize_d:.1f} {funit} · {Path(uploaded.name).suffix.upper()[1:]}</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)
            if uploaded.size > 50*1024*1024:
                st.warning("⚠️ File exceeds 50 MB — processing may take longer.")

        st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
        analyze_btn = st.button("⚡  Analyze Call", disabled=not uploaded)

    with col_right:
        st.markdown('<div class="sec-label">Scoring Dimensions</div>', unsafe_allow_html=True)
        for icon, name, desc in [
            ("👋","Greeting Quality","Warmth, professionalism, proper introduction"),
            ("❤️","Empathy","Acknowledging feelings, genuine care"),
            ("🔍","Problem Understanding","Correctly identifying and clarifying issues"),
            ("✅","Resolution Clarity","Clear explanation of solution and next steps"),
            ("💼","Professionalism","Language, tone, and courtesy throughout"),
        ]:
            st.markdown(f"""
<div class="glass-card" style="margin-bottom:0.5rem;padding:0.9rem 1.1rem">
  <div style="display:flex;align-items:center;gap:10px">
    <span style="font-size:1.1rem">{icon}</span>
    <div>
      <div style="color:#c8c8e0;font-size:0.85rem;font-weight:600">{name}</div>
      <div style="color:#444460;font-size:0.75rem">{desc}</div>
    </div>
    <div style="margin-left:auto;color:#333350;font-family:'Syne',sans-serif;font-size:0.8rem;font-weight:700">0–5</div>
  </div>
</div>""", unsafe_allow_html=True)

    # PIPELINE
    if uploaded and analyze_btn:
        st.markdown("<hr>", unsafe_allow_html=True)
        transcript = None
        if uploaded.name.endswith(".txt"):
            transcript = uploaded.read().decode("utf-8", errors="replace")
            st.success(f"✅ Transcript loaded — {len(transcript):,} characters")
        else:
            transcript = extract_and_transcribe(uploaded)
            if transcript: st.success(f"✅ Audio transcribed — {len(transcript):,} characters")

        if transcript:
            st.markdown('<div class="sec-label" style="margin-top:1.5rem">Transcript Preview</div>', unsafe_allow_html=True)
            preview = transcript[:1800] + ("…" if len(transcript)>1800 else "")
            st.markdown(f'<div class="transcript-box">{preview}</div>', unsafe_allow_html=True)

            detected_kw = detect_compliance_keywords(transcript)

            with st.spinner("🤖 AI evaluating call quality..."):
                try: result = run_evaluation(transcript)
                except Exception as e:
                    st.error(f"Evaluation error: {e}"); result = mock_evaluation(transcript)

            result["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result["filename"]  = uploaded.name
            result["transcript"] = transcript
            result["compliance_keywords"] = detected_kw
            st.session_state.history.append(result)
            save_to_csv(result)

            scores=result["scores"]; total=result["total_score"]; descs=result.get("score_descriptions",{})
            sent=result.get("customer_sentiment","Neutral"); escal=result.get("escalation_risk","Medium")
            viols=result.get("compliance_violations",[]); suggs=result.get("improvement_suggestions",[])
            g_ltr,g_pct=grade(total)

            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown('<div class="sec-label">Evaluation Results</div>', unsafe_allow_html=True)

            mc1,mc2,mc3,mc4,mc5=st.columns(5)
            with mc1:
                st.markdown(f'<div class="metric-card"><div class="metric-lbl">Total Score</div><div class="metric-val metric-accent">{total}</div><div class="metric-sub">out of 25</div></div>', unsafe_allow_html=True)
            with mc2:
                st.markdown(f'<div class="metric-card"><div class="metric-lbl">Grade</div><div class="grade-circle"><span class="grade-letter">{g_ltr}</span></div><div class="metric-sub">{g_pct}%</div></div>', unsafe_allow_html=True)
            with mc3:
                sc=sent.lower()
                st.markdown(f'<div class="metric-card"><div class="metric-lbl">Sentiment</div><div style="margin:0.7rem 0"><span class="pill pill-{sc}"><span class="pill-dot"></span>{sent}</span></div></div>', unsafe_allow_html=True)
            with mc4:
                ec=escal.lower()
                st.markdown(f'<div class="metric-card"><div class="metric-lbl">Escalation Risk</div><div style="margin:0.7rem 0"><span class="pill pill-{ec}"><span class="pill-dot"></span>{escal}</span></div></div>', unsafe_allow_html=True)
            with mc5:
                vc="#f87171" if viols else "#34d399"
                vt="detected" if viols else "all clear"
                st.markdown(f'<div class="metric-card"><div class="metric-lbl">Violations</div><div class="metric-val" style="color:{vc}">{len(viols)}</div><div class="metric-sub">{vt}</div></div>', unsafe_allow_html=True)

            st.markdown("<div style='margin-top:1.5rem'></div>", unsafe_allow_html=True)

            col_scores, col_charts = st.columns([1.1,1], gap="large")
            with col_scores:
                st.markdown('<div class="sec-label">Dimension Breakdown</div>', unsafe_allow_html=True)
                dim_details = {
                    "greeting_quality":      ("👋","Greeting Quality","How well did the agent open the call? Includes self-introduction, tone warmth, and setting a professional first impression."),
                    "empathy":               ("❤️","Empathy","Did the agent acknowledge the customer's feelings? Looks for empathy phrases, validation of frustration, and genuine human connection."),
                    "problem_understanding": ("🔍","Problem Understanding","Did the agent correctly identify and clarify the core issue? Checks for active listening, probing questions, and accurate diagnosis."),
                    "resolution_clarity":    ("✅","Resolution Clarity","Was the solution communicated clearly? Evaluates whether next steps, timelines, and outcomes were explained without ambiguity."),
                    "professionalism":       ("💼","Professionalism","Overall language quality, avoidance of negative language, composure under pressure, and adherence to professional communication norms."),
                }
                for key,(icon,label,detail) in dim_details.items():
                    v=scores.get(key,0); d=descs.get(key,"")
                    color=score_color(v); pct=int((v/5)*100)
                    star_filled = "★"*v; star_empty = "☆"*(5-v)
                    grade_tag = "Excellent" if v==5 else ("Good" if v==4 else ("Fair" if v==3 else ("Weak" if v==2 else "Poor")))
                    grade_color = color
                    st.markdown(f"""
<div class="dim-card" id="dim-{key}">
  <div class="dim-card-header" onclick="toggleDim('{key}')">
    <div class="dim-left">
      <span class="dim-icon">{icon}</span>
      <div>
        <div class="dim-name">{label}</div>
        <div class="dim-stars"><span style="color:{color}">{star_filled}</span><span style="color:#2a2a44">{star_empty}</span></div>
      </div>
    </div>
    <div class="dim-right">
      <span class="dim-grade-tag" style="background:rgba(255,255,255,0.04);border:1px solid {grade_color}30;color:{grade_color}">{grade_tag}</span>
      <span class="dim-score-num" style="color:{color}">{v}<span style="font-size:0.75rem;color:#444460">/5</span></span>
      <span class="dim-chevron" id="chev-{key}">›</span>
    </div>
  </div>
  <div class="dim-track" style="margin:0.6rem 0.2rem">
    <div class="dim-fill" style="width:{pct}%;background:linear-gradient(90deg,{color},{color}88)"></div>
  </div>
  <div class="dim-body" id="body-{key}">
    <div class="dim-ai-verdict">
      <div class="dim-verdict-label">🤖 AI Verdict</div>
      <div class="dim-verdict-text">{d}</div>
    </div>
    <div class="dim-what-it-means">
      <div class="dim-means-label">📋 What we measure</div>
      <div class="dim-means-text">{detail}</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

            with col_charts:
                st.markdown('<div class="sec-label">Visual Analysis</div>', unsafe_allow_html=True)
                ct1,ct2=st.tabs(["Radar","Bar"])
                with ct1:
                    fig_r=make_radar(scores); st.pyplot(fig_r); plt.close(fig_r)
                with ct2:
                    fig_b=make_bar(scores); st.pyplot(fig_b); plt.close(fig_b)

            st.markdown("<div style='margin-top:1.5rem'></div>", unsafe_allow_html=True)

            # ── CALL SUMMARY + STRENGTHS row ──
            summary_txt = result.get("call_summary","")
            strengths   = result.get("agent_strengths",[])
            if summary_txt or strengths:
                col_summ, col_str = st.columns(2, gap="large")
                with col_summ:
                    if summary_txt:
                        st.markdown('<div class="sec-label">Call Summary</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="call-summary-box"><div class="call-summary-label">📋 Overview</div><div class="call-summary-text">{summary_txt}</div></div>', unsafe_allow_html=True)
                with col_str:
                    if strengths:
                        st.markdown('<div class="sec-label">Agent Strengths</div>', unsafe_allow_html=True)
                        strength_html = "".join([f'<div class="strength-item"><div class="strength-dot"></div><div class="strength-text">{s}</div></div>' for s in strengths])
                        st.markdown(f'<div class="glass-card" style="padding:0.8rem 1.2rem">{strength_html}</div>', unsafe_allow_html=True)

            # ── COMPLIANCE ──
            st.markdown("<div style='margin-top:1.2rem'></div>", unsafe_allow_html=True)
            cc, ckw = st.columns(2, gap="large")
            with cc:
                st.markdown('<div class="sec-label">Compliance Violations</div>', unsafe_allow_html=True)
                if viols:
                    for v in viols:
                        st.markdown(f'<div class="violation-item"><span class="item-icon icon-v">!</span>{v}</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="suggestion-item"><span class="item-icon icon-s">✓</span>No compliance violations detected in this call.</div>', unsafe_allow_html=True)
            with ckw:
                st.markdown('<div class="sec-label">Compliance Keywords</div>', unsafe_allow_html=True)
                if detected_kw:
                    st.markdown("".join([f'<span class="kw-chip">{k}</span>' for k in detected_kw]), unsafe_allow_html=True)
                else:
                    st.markdown('<div class="suggestion-item"><span class="item-icon icon-s">✓</span>No sensitive keywords found.</div>', unsafe_allow_html=True)

            # ── IMPROVEMENT SUGGESTIONS ──
            st.markdown("<div style='margin-top:1.5rem'></div>", unsafe_allow_html=True)
            st.markdown('<div class="sec-label">Improvement Suggestions</div>', unsafe_allow_html=True)

            # Priority filter
            pri_filter = st.radio("Filter by priority:", ["All","🔴 High","🟡 Medium","🟢 Low"], horizontal=True, label_visibility="collapsed")
            pri_map = {"All": None, "🔴 High": "High", "🟡 Medium": "Medium", "🟢 Low": "Low"}
            selected_pri = pri_map[pri_filter]

            high_suggs   = [s for s in suggs if isinstance(s,dict) and s.get("priority")=="High"]
            medium_suggs = [s for s in suggs if isinstance(s,dict) and s.get("priority")=="Medium"]
            low_suggs    = [s for s in suggs if isinstance(s,dict) and s.get("priority")=="Low"]
            plain_suggs  = [s for s in suggs if isinstance(s,str)]

            # Stats row
            if any(isinstance(s,dict) for s in suggs):
                sc1,sc2,sc3,sc4 = st.columns(4)
                with sc1: st.metric("Total Suggestions", len([s for s in suggs if isinstance(s,dict)]))
                with sc2: st.metric("🔴 High Priority", len(high_suggs))
                with sc3: st.metric("🟡 Medium Priority", len(medium_suggs))
                with sc4: st.metric("🟢 Low Priority", len(low_suggs))

            st.markdown("<div style='margin-top:0.8rem'></div>", unsafe_allow_html=True)

            def render_sugg_card(s, idx):
                pri   = s.get("priority","Medium")
                cat   = s.get("category","General")
                title = s.get("title","")
                issue = s.get("issue","")
                action= s.get("action","")
                example=s.get("example","")
                dim   = s.get("dimension","general")
                sid   = f"s{idx}"
                return f"""
<div class="sugg-card">
  <div class="sugg-header" onclick="toggleSugg('{sid}')">
    <div class="sugg-priority-dot priority-{pri}"></div>
    <div class="sugg-title">{title}</div>
    <div class="sugg-meta">
      <span class="sugg-cat-tag">{cat}</span>
      <span class="sugg-pri-tag pri-{pri}">{pri}</span>
      <span class="sugg-chevron" id="schev-{sid}">›</span>
    </div>
  </div>
  <div class="sugg-body" id="sbody-{sid}">
    <div class="sugg-row">
      <div class="sugg-row-icon">⚠️</div>
      <div class="sugg-row-label">Issue</div>
      <div class="sugg-row-text">{issue}</div>
    </div>
    <div class="sugg-row">
      <div class="sugg-row-icon">✅</div>
      <div class="sugg-row-label">Action</div>
      <div class="sugg-row-text">{action}</div>
    </div>
    {'<div class="sugg-example-box">' + example + '</div>' if example else ''}
  </div>
</div>"""

            shown = 0
            for i, s in enumerate(suggs):
                if isinstance(s, dict):
                    if selected_pri is None or s.get("priority") == selected_pri:
                        st.markdown(render_sugg_card(s, i), unsafe_allow_html=True)
                        shown += 1
                else:
                    st.markdown(f'<div class="suggestion-item"><span class="item-icon icon-s">{i+1}</span>{s}</div>', unsafe_allow_html=True)
                    shown += 1

            if shown == 0:
                st.markdown('<div style="color:#444460;font-size:0.85rem;padding:1rem 0">No suggestions match this filter.</div>', unsafe_allow_html=True)

            st.markdown("<div style='margin-top:1.5rem'></div>", unsafe_allow_html=True)
            cj,cd=st.columns(2,gap="large")
            with cj:
                with st.expander("🔧 Raw Evaluation JSON"):
                    st.json({k:v for k,v in result.items() if k!="transcript"})
            with cd:
                stem = Path(uploaded.name).stem
                ts_s = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                st.markdown("<div style='padding-top:0.3rem'></div>", unsafe_allow_html=True)
                st.download_button(
                    "⬇️  Download Audit Report (.txt)",
                    data=build_report(result, transcript),
                    file_name=f"calliq_report_{stem}_{ts_s}.txt",
                    mime="text/plain",
                )
                st.markdown("<div style='margin-top:0.5rem'></div>", unsafe_allow_html=True)
                if REPORTS_AVAILABLE:
                    try:
                        st.download_button("⬇️  Download Audit Report (.pdf)",
                            data=build_pdf_report(result, transcript),
                            file_name=f"calliq_report_{stem}_{ts_s}.pdf",
                            mime="application/pdf")
                    except Exception as _e:
                        st.caption(f"PDF unavailable: {_e}")
                    st.markdown("<div style='margin-top:0.5rem'></div>", unsafe_allow_html=True)
                    try:
                        st.download_button("⬇️  Download Audit Report (.xlsx)",
                            data=build_excel_report(result, transcript),
                            file_name=f"calliq_report_{stem}_{ts_s}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    except Exception as _e:
                        st.caption(f"Excel unavailable: {_e}")

            # ── Auto-alert dispatch ──────────────────────────────────────────
            if ALERTS_AVAILABLE:
                _triggered = evaluate_triggers(result, st.session_state.alert_thresholds)
                if _triggered:
                    st.session_state.last_alert_result = {"alerts": _triggered, "result": result}
                    _crit = any(a["severity"] == "critical" for a in _triggered)
                    st.warning(f"{'🔴' if _crit else '🟡'} **{len(_triggered)} compliance alert(s) triggered** — see the Alerts & Reports tab.")
                    _cfg = dict(st.session_state.alert_config)
                    _cfg["to_addrs"] = [e.strip() for e in _cfg.get("to_addrs_str","").split(",") if e.strip()]
                    if _cfg.get("email_enabled") or _cfg.get("slack_enabled") or _cfg.get("teams_enabled"):
                        dispatch_alerts(result, _cfg, st.session_state.alert_thresholds)

    elif not uploaded:
        st.markdown("""
<div style="text-align:center;padding:4rem 2rem;color:#333350">
  <div style="font-size:3.5rem;margin-bottom:1rem;opacity:0.4">🎧</div>
  <div style="font-family:'Syne',sans-serif;font-size:1.1rem;color:#444460;font-weight:600">Upload a file to begin analysis</div>
  <div style="font-size:0.82rem;margin-top:0.5rem;color:#2a2a44">Transcripts (.txt) · Audio (.mp3 .wav .m4a .ogg .flac) · Video (.mp4 .mov .avi)</div>
</div>""", unsafe_allow_html=True)

# ===========================================================================
# TAB 2
# ===========================================================================
with tab2:
    df_hist=load_history_from_csv()
    if not df_hist.empty and "total_score" in df_hist.columns:
        st.markdown('<div class="sec-label">Performance Overview</div>', unsafe_allow_html=True)
        s1,s2,s3,s4,s5=st.columns(5)
        with s1: st.metric("Calls Analyzed",len(df_hist))
        with s2: st.metric("Average Score",f"{df_hist['total_score'].mean():.1f}/25")
        with s3: st.metric("Best Score",f"{int(df_hist['total_score'].max())}/25")
        with s4: st.metric("Worst Score",f"{int(df_hist['total_score'].min())}/25")
        with s5:
            pos=int((df_hist.get("customer_sentiment","")=="Positive").sum()) if "customer_sentiment" in df_hist else 0
            st.metric("Positive Calls",f"{pos}/{len(df_hist)}")

        st.markdown("<div style='margin-top:1.5rem'></div>", unsafe_allow_html=True)
        st.markdown('<div class="sec-label">Score Trend</div>', unsafe_allow_html=True)
        fig_t=make_trend(df_hist); st.pyplot(fig_t); plt.close(fig_t)

        st.markdown("<div style='margin-top:1.5rem'></div>", unsafe_allow_html=True)
        st.markdown('<div class="sec-label">Evaluation History</div>', unsafe_allow_html=True)
        display_cols=[c for c in ["timestamp","filename","total_score","customer_sentiment","escalation_risk"] if c in df_hist.columns]
        st.dataframe(df_hist[display_cols], hide_index=True)

        st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
        st.download_button("⬇️  Export History CSV",data=df_hist.to_csv(index=False).encode(),file_name="calliq_history.csv",mime="text/csv")
    else:
        st.markdown("""
<div style="text-align:center;padding:4rem 2rem">
  <div style="font-size:3rem;opacity:0.3;margin-bottom:1rem">📊</div>
  <div style="font-family:'Syne',sans-serif;color:#444460;font-size:1rem;font-weight:600">No data yet</div>
  <div style="color:#2a2a44;font-size:0.82rem;margin-top:0.4rem">Analyze some calls to see performance trends here.</div>
</div>""", unsafe_allow_html=True)

# ===========================================================================
# TAB 3 — POLICY RAG AUDIT
# ===========================================================================
with tab3:
    if not RAG_AVAILABLE:
        st.error("RAG engine not found. Make sure `rag_engine.py` is in the same directory as `app.py`.")
    else:
        ensure_sample_policies()
        idx_stats = get_index_stats()

        r_left, r_right = st.columns([1, 1.4], gap="large")

        # ── Left: Policy library & index management ──────────────────────────
        with r_left:
            st.markdown('<div class="sec-label">Policy Library</div>', unsafe_allow_html=True)

            # Index status badge
            if idx_stats["indexed"]:
                st.markdown(f'<div class="rag-index-badge">● Index ready &nbsp;·&nbsp; {idx_stats["chunks"]} chunks &nbsp;·&nbsp; {idx_stats["store_type"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="rag-index-badge-off">● Index not built — click Build Index below</div>', unsafe_allow_html=True)

            st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)

            # Upload new policy doc
            st.markdown('<div class="sec-label">Upload Policy Document</div>', unsafe_allow_html=True)
            uploaded_policy = st.file_uploader(
                "Add a .txt, .md, or .pdf policy file",
                type=["txt", "md", "pdf"],
                key="policy_upload",
                label_visibility="collapsed",
            )
            if uploaded_policy:
                save_path = POLICY_DOCS_DIR / uploaded_policy.name
                save_path.write_bytes(uploaded_policy.read())
                st.success(f"✅ Saved: {uploaded_policy.name}")

            st.markdown("<div style='margin-top:0.8rem'></div>", unsafe_allow_html=True)
            build_btn = st.button("🔧  Build / Rebuild Index", key="build_index")

            if build_btn:
                with st.spinner("Chunking and embedding policy documents..."):
                    ok, msg = ingest_policy_docs(
                        openai_key=OPENAI_API_KEY,
                        openrouter_key=OPENROUTER_API_KEY,
                        force_rebuild=True,
                    )
                st.success(f"✅ {msg}") if ok else st.error(f"❌ {msg}")
                idx_stats = get_index_stats()
                st.rerun()

            st.markdown("<div style='margin-top:1.2rem'></div>", unsafe_allow_html=True)
            st.markdown('<div class="sec-label">Loaded Documents</div>', unsafe_allow_html=True)

            docs = list_policy_docs()
            for doc in docs:
                st.markdown(f"""
<div class="rag-policy-card">
  <div class="rag-policy-name">📄 {doc['name']}</div>
  <div class="rag-policy-meta">{doc['size_kb']} KB · {doc['lines']} lines</div>
  <div class="rag-policy-preview">{doc['preview']}...</div>
</div>""", unsafe_allow_html=True)

        # ── Right: RAG audit panel ────────────────────────────────────────────
        with r_right:
            st.markdown('<div class="sec-label">RAG-Powered Policy Audit</div>', unsafe_allow_html=True)

            # Transcript source: from last analysis or manual paste
            last_results = st.session_state.history
            transcript_options = ["Paste transcript manually"] + [
                f"{r.get('filename','call')} — {r.get('timestamp','')}"
                for r in reversed(last_results[-5:])
            ]
            selected_src = st.selectbox("Transcript source:", transcript_options, key="rag_src")

            if selected_src == "Paste transcript manually":
                rag_transcript_input = st.text_area(
                    "Paste transcript here:",
                    height=180,
                    placeholder="Paste a call transcript to audit against your policy documents...",
                    label_visibility="collapsed",
                    key="rag_manual",
                )
                rag_eval = {}
            else:
                idx_choice = transcript_options.index(selected_src) - 1
                chosen = list(reversed(last_results[-5:]))[idx_choice]
                rag_transcript_input = chosen.get("transcript", "")
                rag_eval = chosen
                if rag_transcript_input:
                    st.markdown(f'<div class="transcript-box" style="max-height:160px">{rag_transcript_input[:600]}…</div>', unsafe_allow_html=True)

            st.markdown("<div style='margin-top:0.8rem'></div>", unsafe_allow_html=True)
            run_rag_btn = st.button("🔍  Run Policy Audit", disabled=not rag_transcript_input, key="run_rag")

            if run_rag_btn and rag_transcript_input:
                if not idx_stats["indexed"]:
                    with st.spinner("Building index first..."):
                        ok, msg = ingest_policy_docs(
                            openai_key=OPENAI_API_KEY,
                            openrouter_key=OPENROUTER_API_KEY,
                        )
                    if not ok:
                        st.error(f"Could not build index: {msg}")
                        st.stop()

                with st.spinner("🔍 Retrieving relevant policy chunks and auditing..."):
                    rag_res = rag_audit(
                        transcript=rag_transcript_input,
                        evaluation_result=rag_eval,
                        openai_key=OPENAI_API_KEY,
                        openrouter_key=OPENROUTER_API_KEY,
                        openrouter_or_openai_key_for_llm=OPENROUTER_API_KEY or OPENAI_API_KEY,
                    )
                st.session_state.rag_result = rag_res
                st.session_state.rag_transcript = rag_transcript_input

            # ── Display RAG results ──
            rag_res = st.session_state.rag_result
            if rag_res:
                st.markdown("<hr>", unsafe_allow_html=True)
                st.markdown('<div class="sec-label">Audit Results</div>', unsafe_allow_html=True)

                # Summary banner
                rag_summary = rag_res.get("rag_summary", "")
                if rag_summary:
                    st.markdown(f"""
<div class="rag-coaching-box">
  <div class="rag-coaching-label">📋 Policy Compliance Verdict</div>
  <div class="rag-coaching-text">{rag_summary}</div>
</div>""", unsafe_allow_html=True)

                ra_c1, ra_c2 = st.columns(2, gap="large")

                with ra_c1:
                    # Policy violations
                    violations = rag_res.get("policy_violations", [])
                    st.markdown('<div class="sec-label">Policy Violations</div>', unsafe_allow_html=True)
                    if violations:
                        for v in violations:
                            st.markdown(f'<div class="rag-violation-item"><span class="item-icon icon-v">!</span>{v}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="rag-compliant-item"><span class="item-icon icon-s">✓</span>No policy violations detected.</div>', unsafe_allow_html=True)

                with ra_c2:
                    # Compliant items
                    compliant = rag_res.get("policy_compliant_items", [])
                    st.markdown('<div class="sec-label">Policy-Compliant Actions</div>', unsafe_allow_html=True)
                    if compliant:
                        for c in compliant:
                            st.markdown(f'<div class="rag-compliant-item"><span class="item-icon icon-s">✓</span>{c}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div style="color:#444460;font-size:0.85rem">No specific compliant items identified.</div>', unsafe_allow_html=True)

                # Contextual coaching
                coaching = rag_res.get("contextual_coaching", "")
                if coaching:
                    st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
                    st.markdown('<div class="sec-label">Policy-Grounded Coaching</div>', unsafe_allow_html=True)
                    st.markdown(f"""
<div class="rag-coaching-box">
  <div class="rag-coaching-label">🎓 Coaching Feedback</div>
  <div class="rag-coaching-text">{coaching}</div>
</div>""", unsafe_allow_html=True)

                # Policy references
                refs = rag_res.get("policy_references", [])
                if refs:
                    st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
                    st.markdown('<div class="sec-label">Matched Policy References</div>', unsafe_allow_html=True)
                    for ref in refs:
                        st.markdown(f"""
<div class="rag-chunk-card">
  <div class="rag-chunk-source">📑 {ref.get('source','')}</div>
  <div class="rag-chunk-text">"{ref.get('excerpt','')}"</div>
  <div class="rag-chunk-score" style="margin-top:0.4rem">{ref.get('relevance','')}</div>
</div>""", unsafe_allow_html=True)

                # Retrieved raw chunks (collapsible)
                chunks = rag_res.get("retrieved_chunks", [])
                if chunks:
                    with st.expander(f"🔎 View {len(chunks)} retrieved policy chunks"):
                        for chunk in chunks:
                            score_pct = int(chunk.get("score", 0) * 100)
                            st.markdown(f"""
<div class="rag-chunk-card">
  <div class="rag-chunk-source">{chunk.get('source','')} · chunk {chunk.get('chunk',0)}</div>
  <div class="rag-chunk-score">Relevance score: {score_pct}%</div>
  <div class="rag-chunk-text">{chunk.get('text','')[:300]}…</div>
</div>""", unsafe_allow_html=True)

            elif not rag_res:
                st.markdown("""
<div style="text-align:center;padding:3rem 1rem;color:#333350">
  <div style="font-size:2.5rem;opacity:0.3;margin-bottom:0.8rem">🔍</div>
  <div style="font-family:'Syne',sans-serif;font-size:0.95rem;color:#444460;font-weight:600">Select a transcript and run the policy audit</div>
  <div style="font-size:0.78rem;margin-top:0.4rem;color:#2a2a44">Findings will be grounded in your uploaded policy documents</div>
</div>""", unsafe_allow_html=True)

# ===========================================================================
# TAB 4
# ===========================================================================
# ===========================================================================
# TAB 4 — ALERTS & REPORTS
# ===========================================================================
with tab4:
    if not ALERTS_AVAILABLE:
        st.error("alerts.py not found. Place it in the same folder as app.py and restart.")
    else:
        al_left, al_right = st.columns([1, 1.2], gap="large")

        with al_left:
            st.markdown('<div class="sec-label">Alert Thresholds</div>', unsafe_allow_html=True)
            thr = st.session_state.alert_thresholds
            thr["score_below"]        = st.slider("Trigger when score is below", 0, 25, int(thr.get("score_below", 10)))
            thr["escalation_high"]    = st.checkbox("Alert on High escalation risk",    value=thr.get("escalation_high", True))
            thr["any_violation"]      = st.checkbox("Alert on any compliance violation", value=thr.get("any_violation", True))
            thr["negative_low_score"] = st.checkbox("Alert on Negative sentiment + score < 15", value=thr.get("negative_low_score", True))
            kw_str = st.text_input("Critical keywords (comma-separated)",
                value=", ".join(thr.get("critical_keywords", [])),
                help="These keywords always trigger a critical alert.")
            thr["critical_keywords"] = [k.strip() for k in kw_str.split(",") if k.strip()]
            st.session_state.alert_thresholds = thr

            st.markdown("<div style='margin-top:1.2rem'></div>", unsafe_allow_html=True)
            st.markdown('<div class="sec-label">Notification Channels</div>', unsafe_allow_html=True)
            cfg = st.session_state.alert_config

            with st.expander("📧 Email (SMTP)"):
                cfg["email_enabled"] = st.checkbox("Enable email alerts", value=cfg.get("email_enabled", False), key="em_en")
                cfg["smtp_host"]     = st.text_input("SMTP Host",     value=cfg.get("smtp_host",""),     placeholder="smtp.gmail.com",        key="em_h")
                cfg["smtp_port"]     = st.number_input("SMTP Port",   value=int(cfg.get("smtp_port",587)), min_value=1, max_value=65535,       key="em_p")
                cfg["smtp_user"]     = st.text_input("SMTP Username", value=cfg.get("smtp_user",""),     placeholder="you@gmail.com",         key="em_u")
                cfg["smtp_password"] = st.text_input("SMTP Password", value=cfg.get("smtp_password",""), type="password",                    key="em_pw")
                cfg["from_addr"]     = st.text_input("From Address",  value=cfg.get("from_addr",""),     placeholder="calliq@company.com",    key="em_fr")
                cfg["to_addrs_str"]  = st.text_input("To (comma-separated)", value=cfg.get("to_addrs_str",""), placeholder="manager@company.com", key="em_to")
                st.caption("💡 Gmail: use an App Password, not your account password.")

            with st.expander("💬 Slack"):
                cfg["slack_enabled"]     = st.checkbox("Enable Slack alerts", value=cfg.get("slack_enabled", False), key="sl_en")
                cfg["slack_webhook_url"] = st.text_input("Webhook URL", value=cfg.get("slack_webhook_url",""),
                    placeholder="https://hooks.slack.com/services/...", type="password", key="sl_wh")
                st.caption("💡 Slack → Apps → Incoming Webhooks → Add.")

            with st.expander("🔵 Microsoft Teams"):
                cfg["teams_enabled"]     = st.checkbox("Enable Teams alerts", value=cfg.get("teams_enabled", False), key="te_en")
                cfg["teams_webhook_url"] = st.text_input("Webhook URL", value=cfg.get("teams_webhook_url",""),
                    placeholder="https://outlook.office.com/webhook/...", type="password", key="te_wh")
                st.caption("💡 Teams channel → Connectors → Incoming Webhook.")

            st.session_state.alert_config = cfg

            st.markdown("<div style='margin-top:0.8rem'></div>", unsafe_allow_html=True)
            if st.button("🔔  Send Test Alert", key="test_alert"):
                _test_res = {
                    "total_score": 6, "escalation_risk": "High",
                    "customer_sentiment": "Negative",
                    "compliance_violations": ["Agent failed to verify customer identity"],
                    "compliance_keywords": ["lawsuit", "fraud"],
                    "filename": "test_call.m4a",
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "scores": {k: 1 for k in ["greeting_quality","empathy","problem_understanding","resolution_clarity","professionalism"]},
                }
                _test_cfg = dict(cfg)
                _test_cfg["to_addrs"] = [e.strip() for e in cfg.get("to_addrs_str","").split(",") if e.strip()]
                _r = dispatch_alerts(_test_res, _test_cfg, thr)
                if _r["alerts"]:
                    st.success(f"✅ {len(_r['alerts'])} test alert(s) triggered.")
                    for ch, res in _r["channels"].items():
                        st.caption(f"{'✅' if res['success'] else '❌'} {ch}: {res['message']}")
                    if not _r["channels"]:
                        st.info("No channels enabled yet — configure Email, Slack, or Teams above.")
                else:
                    st.info("No thresholds triggered by test data.")

        with al_right:
            st.markdown('<div class="sec-label">Recent Alerts</div>', unsafe_allow_html=True)
            last = st.session_state.last_alert_result
            if last:
                st.markdown(f'<div style="font-size:0.75rem;color:#555570;margin-bottom:0.6rem">From last analysis: <b style="color:#a0a0c0">{last["result"].get("filename","")}</b></div>', unsafe_allow_html=True)
                for a in last["alerts"]:
                    cls  = "alert-card-critical" if a["severity"]=="critical" else "alert-card-warning"
                    bcls = "alert-badge-critical" if a["severity"]=="critical" else "alert-badge-warning"
                    st.markdown(f"""
<div class="{cls}">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:0.3rem">
    <div class="alert-title">{a['title']}</div>
    <span class="{bcls}">{a['severity'].upper()}</span>
  </div>
  <div class="alert-detail">{a['detail']}</div>
  <div class="alert-meta">{a.get('timestamp','')} · {a.get('filename','')}</div>
</div>""", unsafe_allow_html=True)
            else:
                st.markdown('<div style="color:#444460;font-size:0.82rem;margin-bottom:1rem">No alerts from the current session yet. Analyze a call to see results here.</div>', unsafe_allow_html=True)

            st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
            st.markdown('<div class="sec-label">Alert History Log</div>', unsafe_allow_html=True)
            _log = load_alert_log()
            if _log:
                for _entry in reversed(_log[-15:]):
                    _cls  = "alert-card-critical" if _entry.get("severity")=="critical" else "alert-card-warning"
                    _bcls = "alert-badge-critical" if _entry.get("severity")=="critical" else "alert-badge-warning"
                    st.markdown(f"""
<div class="{_cls}">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:0.25rem">
    <div class="alert-title" style="font-size:0.82rem">{_entry.get('title','')}</div>
    <span class="{_bcls}">{_entry.get('severity','').upper()}</span>
  </div>
  <div class="alert-detail">{_entry.get('detail','')}</div>
  <div class="alert-meta">{_entry.get('logged_at','')} · {_entry.get('filename','')}</div>
</div>""", unsafe_allow_html=True)
                st.markdown("<div style='margin-top:0.8rem'></div>", unsafe_allow_html=True)
                st.download_button("⬇️  Export Alert Log (.json)",
                    data=json.dumps(_log, indent=2).encode(),
                    file_name=f"calliq_alerts_{datetime.datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json")
            else:
                st.markdown('<div style="color:#444460;font-size:0.82rem">No alerts logged yet.</div>', unsafe_allow_html=True)

            st.markdown("<div style='margin-top:1.2rem'></div>", unsafe_allow_html=True)
            st.markdown('<div class="sec-label">Export Last Report</div>', unsafe_allow_html=True)
            if st.session_state.history:
                _lr   = st.session_state.history[-1]
                _ltx  = _lr.get("transcript", "")
                _stem = Path(_lr.get("filename", "report")).stem
                _ts   = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                _e1, _e2, _e3 = st.columns(3)
                with _e1:
                    st.download_button("⬇️ .txt",
                        data=build_report(_lr, _ltx),
                        file_name=f"calliq_{_stem}_{_ts}.txt",
                        mime="text/plain", key="exp_txt2")
                with _e2:
                    if REPORTS_AVAILABLE:
                        try:
                            st.download_button("⬇️ .pdf",
                                data=build_pdf_report(_lr, _ltx),
                                file_name=f"calliq_{_stem}_{_ts}.pdf",
                                mime="application/pdf", key="exp_pdf2")
                        except Exception as _e:
                            st.caption(f"PDF: {_e}")
                with _e3:
                    if REPORTS_AVAILABLE:
                        try:
                            st.download_button("⬇️ .xlsx",
                                data=build_excel_report(_lr, _ltx),
                                file_name=f"calliq_{_stem}_{_ts}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="exp_xl2")
                        except Exception as _e:
                            st.caption(f"Excel: {_e}")
            else:
                st.markdown('<div style="color:#444460;font-size:0.82rem">Analyze a call first to enable report export.</div>', unsafe_allow_html=True)

# ===========================================================================
# TAB 5 — ABOUT
# ===========================================================================
with tab5:
    c1,c2=st.columns(2,gap="large")
    with c1:
        st.markdown('<div class="sec-label">How It Works</div>', unsafe_allow_html=True)
        for num,title,desc in [
            ("01","Upload","Drop a .txt transcript or audio/video file"),
            ("02","Transcribe","Audio extracted via moviepy → transcribed by Deepgram nova-2"),
            ("03","Evaluate","Transcript analyzed by GPT-4o-mini via OpenRouter"),
            ("04","Score","5-dimension scores + sentiment, escalation, compliance"),
            ("05","Export","Download a full audit report or export history as CSV"),
        ]:
            st.markdown(f"""
<div class="glass-card" style="margin-bottom:0.6rem;padding:1rem 1.2rem">
  <div style="display:flex;align-items:center;gap:12px">
    <div style="font-family:'Syne',sans-serif;font-size:1.2rem;font-weight:800;color:#ff4d6d;min-width:28px">{num}</div>
    <div><div style="color:#d0d0e8;font-weight:600;font-size:0.88rem">{title}</div><div style="color:#555570;font-size:0.78rem">{desc}</div></div>
  </div>
</div>""", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="sec-label">API Configuration</div>', unsafe_allow_html=True)
        for env,name,purpose,url in [
            ("DEEPGRAM_API_KEY","Deepgram","Speech-to-text transcription","deepgram.com"),
            ("OPENROUTER_API_KEY","OpenRouter","LLM evaluation (GPT-4o-mini)","openrouter.ai"),
            ("OPENAI_API_KEY","OpenAI","Direct LLM fallback","platform.openai.com"),
        ]:
            st.markdown(f"""
<div class="glass-card" style="margin-bottom:0.6rem;padding:1rem 1.2rem">
  <div style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      <div style="color:#d0d0e8;font-weight:600;font-size:0.88rem">{name}</div>
      <div style="color:#555570;font-size:0.75rem">{purpose}</div>
      <code style="color:#ff4d6d;font-size:0.72rem;background:rgba(255,77,109,0.08);padding:2px 6px;border-radius:4px">{env}</code>
    </div>
    <div style="color:#333350;font-size:0.72rem">{url}</div>
  </div>
</div>""", unsafe_allow_html=True)

        st.markdown('<div class="sec-label" style="margin-top:1.5rem">Scoring Guide</div>', unsafe_allow_html=True)
        for score,label,note,color in [
            ("0–1","Poor","Critical improvement needed","#f87171"),
            ("2–3","Needs Work","Below standard expectations","#fbbf24"),
            ("4","Good","Meets professional standards","#60a5fa"),
            ("5","Excellent","Exceeds all expectations","#34d399"),
        ]:
            st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;padding:0.5rem 0;border-bottom:1px solid rgba(255,255,255,0.04)">
  <div style="font-family:'Syne',sans-serif;font-weight:700;color:{color};min-width:30px;font-size:0.9rem">{score}</div>
  <div style="color:#c0c0d8;font-weight:600;font-size:0.85rem;min-width:90px">{label}</div>
  <div style="color:#555570;font-size:0.78rem">{note}</div>
</div>""", unsafe_allow_html=True)
