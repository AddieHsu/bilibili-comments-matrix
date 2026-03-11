import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os

try:
    from get_comments import scrape_bilibili_comments
    from data_pipeline import clean_scraped_data
    from llm_engine import extract_intelligence
except ImportError as e:
    st.error(f"缺少核心执行模块。详细报错: {e}")
    st.stop()

# --- 1. 视窗与状态初始化及物理探针 ---
st.set_page_config(page_title="情报分析矩阵", layout="wide", initial_sidebar_state="expanded")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# 目录扫描器：废弃低效排除法，启用绝对后缀锚定
archive_files = [
    f for f in os.listdir(CURRENT_DIR) 
    if f.endswith('_intelligence.json')
]

if 'raw_file_path' not in st.session_state:
    st.session_state.raw_file_path = None
if 'cleaned_file_path' not in st.session_state:
    st.session_state.cleaned_file_path = None
if 'intelligence_file_path' not in st.session_state:
    st.session_state.intelligence_file_path = None
if 'active_dim' not in st.session_state:
    st.session_state.active_dim = None
if 'active_sent' not in st.session_state:
    st.session_state.active_sent = None

# 默认探针：捕获并挂载物理时间戳最新的归档矩阵
if not st.session_state.intelligence_file_path and archive_files:
    latest_archive = max(archive_files, key=lambda f: os.path.getmtime(os.path.join(CURRENT_DIR, f)))
    st.session_state.intelligence_file_path = os.path.join(CURRENT_DIR, latest_archive)

# --- 2. 深度定制光学与材质覆写 (CSS Injection) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Noto+Sans+SC:wght@400;500;700&display=swap');
    
    :root {
        --bg-base: #09090B;
        --bg-sidebar: rgba(28, 28, 35, 0.85);
        --bg-card: rgba(30, 30, 35, 0.6);
        --bg-input: #1A1A1E;
        --bg-input-focus: #222228;
        --text-primary: #E2E8F0;
        --text-secondary: #A0AEC0;
        --text-metric: #F4D03F;
        --accent-core: #9D4EDD;
        --accent-hover: rgba(157, 78, 221, 0.2);
        --border-subtle: rgba(255, 255, 255, 0.08);
        --shadow-glow: rgba(157, 78, 221, 0.2);
        --gradient-primary: linear-gradient(135deg, #9D4EDD 0%, #7B2CBF 100%);
        --gradient-radial: radial-gradient(circle at 15% 50%, rgba(157, 78, 221, 0.08), transparent 40%), radial-gradient(circle at 85% 30%, rgba(244, 208, 63, 0.05), transparent 40%);
    }

    @media (prefers-color-scheme: light) {
        :root {
            --bg-base: #F4F4F5;
            --bg-sidebar: rgba(255, 255, 255, 0.85);
            --bg-card: rgba(255, 255, 255, 0.95);
            --bg-input: #FFFFFF;
            --bg-input-focus: #FAFAFA;
            --text-primary: #18181B;
            --text-secondary: #52525B;
            --text-metric: #D97706; 
            --accent-core: #7B2CBF;
            --accent-hover: rgba(123, 44, 191, 0.1);
            --border-subtle: rgba(0, 0, 0, 0.08);
            --shadow-glow: rgba(123, 44, 191, 0.15);
            --gradient-primary: linear-gradient(135deg, #7B2CBF 0%, #5A189A 100%);
            --gradient-radial: radial-gradient(circle at 15% 50%, rgba(123, 44, 191, 0.05), transparent 40%), radial-gradient(circle at 85% 30%, rgba(217, 119, 6, 0.03), transparent 40%);
        }
    }

    html, body, [class*="css"], [class*="st-"], h1, h2, h3, h4, h5, h6, p, span, div {
        font-family: 'Noto Sans SC', -apple-system, sans-serif !important;
        color: var(--text-primary) !important;
    }

    .stApp {
        background-color: var(--bg-base) !important;
        background-image: var(--gradient-radial) !important;
        transition: background-color 0.3s ease;
    }

    [data-testid="stSidebar"] {
        background-color: var(--bg-sidebar) !important;
        backdrop-filter: blur(24px) !important;
        -webkit-backdrop-filter: blur(24px) !important;
        border-right: 1px solid var(--border-subtle) !important;
    }

    [data-testid="stMetric"] {
        background: var(--bg-card) !important;
        backdrop-filter: blur(12px);
        border: 1px solid var(--border-subtle) !important;
        border-radius: 12px;
        padding: 24px 20px;
        box-shadow: 0 8px 32px 0 rgba(0,0,0,0.1);
        transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275), border-color 0.3s ease, box-shadow 0.3s ease;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-6px);
        border-color: var(--accent-core) !important;
        box-shadow: 0 12px 40px 0 var(--shadow-glow);
    }
    
    [data-testid="stMetricValue"] { 
        color: var(--text-metric) !important; 
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 2.4rem !important; 
        font-weight: 700 !important; 
    }
    
    [data-testid="stMetricLabel"] * { color: var(--text-secondary) !important; }

    .stTextInput > div > div > input, .stTextArea > div > div > textarea, [data-testid="stFileUploadDropzone"] {
        border-radius: 8px;
        background-color: var(--bg-input) !important;
        border: 1px solid var(--border-subtle) !important;
        color: var(--text-primary) !important;
        transition: all 0.3s ease;
    }
    .stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus, [data-testid="stFileUploadDropzone"]:hover {
        border-color: var(--accent-core) !important;
        box-shadow: 0 0 0 1px var(--accent-core) !important;
        background-color: var(--bg-input-focus) !important;
    }
    
    .stButton > button {
        background: var(--accent-hover) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 8px;
        color: var(--text-primary) !important;
        transition: all 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
    }
    .stButton > button:hover {
        border-color: var(--accent-core) !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 15px var(--shadow-glow);
    }

    .stButton > button[kind="primary"] {
        background: var(--gradient-primary) !important;
        border: none !important;
        color: #FFFFFF !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) scale(1.02);
        box-shadow: 0 0 20px var(--shadow-glow) !important;
    }

    [data-testid*="ollapse"] *,
    [data-testid*="Sidebar"] button *,
    button[kind*="header"] *,
    span.material-symbols-rounded,
    div.material-symbols-rounded,
    .material-symbols-rounded,
    .material-icons {
        font-family: "Material Symbols Rounded", "Material Icons" !important;
        font-feature-settings: "liga" 1 !important;
        -webkit-font-feature-settings: "liga" 1 !important;
        color: var(--text-secondary) !important;
        letter-spacing: normal !important;
        text-transform: none !important;
        white-space: nowrap !important;
        word-wrap: normal !important;
        -webkit-font-smoothing: antialiased !important;
    }

    .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 95%; }
    div[data-testid="stSidebarHeader"] { padding-bottom: 0rem; }
</style>
""", unsafe_allow_html=True)

# --- 3. 调度枢纽 (侧边栏) ---
with st.sidebar:
    st.title("调度枢纽")
    
    st.subheader("本地矩阵挂载")
    if archive_files:
        selected_archive = st.selectbox("选择历史数据", archive_files)
        if st.button("强制渲染选中矩阵", use_container_width=True):
            st.session_state.intelligence_file_path = os.path.join(CURRENT_DIR, selected_archive)
            st.session_state.raw_file_path = None
            st.session_state.cleaned_file_path = None
    else:
        st.info("本地无可用归档，请启动摄入管道。")
        
    st.markdown("---")
    
    st.subheader("阶段 I: 数据抓取")
    bvid_input = st.text_input("目标 BVID", value="BV15aABzdEG2")
    if st.button("执行抓取 (中断请按右上角 Stop)", use_container_width=True):
        with st.spinner("提取网络拓扑..."):
            path = scrape_bilibili_comments(bvid_input)
            if path and os.path.exists(path):
                st.session_state.raw_file_path = path
                st.session_state.cleaned_file_path = None
                st.session_state.intelligence_file_path = None
            else:
                st.error("网络管道异常")
                
    if st.session_state.raw_file_path:
        st.success(f"数据已抓取: {os.path.basename(st.session_state.raw_file_path)}")

    st.markdown("---")
    
    st.subheader("阶段 II: 数据预清洗")
    # 旁路注入接口
    uploaded_raw = st.file_uploader("注入本地原始载荷 (.json/.csv)", type=['json', 'csv'], key="up_raw")
    if uploaded_raw:
        temp_raw_path = f"injected_{uploaded_raw.name}"
        with open(temp_raw_path, "wb") as f:
            f.write(uploaded_raw.getbuffer())
        st.session_state.raw_file_path = temp_raw_path
        st.session_state.cleaned_file_path = None
        st.session_state.intelligence_file_path = None
        st.info("已劫持原始管道。")

    clean_disabled = st.session_state.raw_file_path is None
    if st.button("执行预清洗 (中断请按右上角 Stop)", disabled=clean_disabled, use_container_width=True):
        with st.spinner("数据清洗中..."):
            cleaned_path = clean_scraped_data(st.session_state.raw_file_path)
            if cleaned_path and os.path.exists(cleaned_path):
                st.session_state.cleaned_file_path = cleaned_path
                st.session_state.intelligence_file_path = None
            else:
                st.error("清洗管道异常")
                
    if st.session_state.cleaned_file_path:
        st.success(f"数据已清洗: {os.path.basename(st.session_state.cleaned_file_path)}")

    st.markdown("---")
    
    st.subheader("阶段 III: LLM编译")
    # 旁路注入接口
    uploaded_clean = st.file_uploader("注入本地提纯载荷 (.json/.csv)", type=['json', 'csv'], key="up_clean")
    if uploaded_clean:
        temp_clean_path = f"injected_{uploaded_clean.name}"
        with open(temp_clean_path, "wb") as f:
            f.write(uploaded_clean.getbuffer())
        st.session_state.cleaned_file_path = temp_clean_path
        st.session_state.intelligence_file_path = None
        st.info("已劫持提纯管道。")

    default_prompt = """重要‼️: 在此预填System Prompt"""
    
    system_prompt_input = st.text_area("覆写 System Prompt", value=default_prompt, height=250)
    llm_disabled = st.session_state.cleaned_file_path is None
    
    if st.button("触发LLM (中断请按右上角 Stop)", disabled=llm_disabled, type="primary", use_container_width=True):
        with st.spinner("处理中..."):
            final_path = extract_intelligence(st.session_state.cleaned_file_path, system_prompt_input)
            if final_path and os.path.exists(final_path):
                st.session_state.intelligence_file_path = final_path
            else:
                st.error("认知结构错误")
                
    if st.session_state.intelligence_file_path:
        st.success("结构化矩阵建立完毕")

# --- 4. 表现层主视窗 ---
st.title("产品舆情矩阵视图")

if not st.session_state.intelligence_file_path:
    st.info("系统待机中。请通过左侧调度枢纽建立物理通信管道。")
    st.stop()

# 数据渲染层
try:
    with open(st.session_state.intelligence_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
except Exception as e:
    st.error(f"渲染层读取异常: {e}")
    st.stop()
    
if df.empty:
    st.warning("提取数据池为空。")
    st.stop()

df_valid = df[~df['Dimension'].str.contains("无价值噪音", na=False)]

# 顶层指标
st.markdown("### 全局洞察概览")
col1, col2, col3 = st.columns(3)
col1.metric("有效情报样本量", len(df_valid))
negative_ratio = (len(df_valid[df_valid['Sentiment'] == '负向']) / len(df_valid) * 100) if len(df_valid) > 0 else 0
col2.metric("负面极性率", f"{negative_ratio:.1f}%")
col3.metric("高频实体", df_valid['Entity'].value_counts().idxmax() if not df_valid.empty else "N/A")

st.markdown("---")

col_header_1, col_header_2 = st.columns([4, 1])
with col_header_1:
    st.markdown("### 动态交叉过滤矩阵")
with col_header_2:
    if st.session_state.active_dim or st.session_state.active_sent:
        if st.button("解除拓扑锁定", key="reset_matrix", use_container_width=True):
            st.session_state.active_dim = None
            st.session_state.active_sent = None
            st.rerun()

col_left, col_right = st.columns(2)

df_left = df_valid if not st.session_state.active_sent else df_valid[df_valid['Sentiment'] == st.session_state.active_sent]
df_right = df_valid if not st.session_state.active_dim else df_valid[df_valid['Dimension'] == st.session_state.active_dim]

with col_left:
    st.markdown(f"#### 维度分布 {'[锚定: ' + st.session_state.active_sent + ']' if st.session_state.active_sent else ''}")
    if not df_left.empty:
        dim_counts = df_left['Dimension'].value_counts().reset_index()
        dim_counts.columns = ['Dimension', 'Count']
        fig_dim = px.bar(dim_counts, x='Count', y='Dimension', color='Dimension', orientation='h')
        fig_dim.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_family="Noto Sans SC")
        
        sel_dim = st.plotly_chart(fig_dim, use_container_width=True, theme="streamlit", on_select="rerun", selection_mode="points", key="dim_chart")
        
        if sel_dim and getattr(sel_dim, 'selection', None) and sel_dim.selection.points:
            pt = sel_dim.selection.points[0]
            pt_data = dict(pt) if isinstance(pt, dict) else pt.__dict__ if hasattr(pt, '__dict__') else {}
            
            clicked_dim = None
            known_dims = set(dim_counts['Dimension'])
            
            for val in pt_data.values():
                if val in known_dims:
                    clicked_dim = val
                    break
                    
            if clicked_dim and st.session_state.active_dim != clicked_dim:
                st.session_state.active_dim = clicked_dim
                st.session_state.active_sent = None 
                st.rerun()

with col_right:
    st.markdown(f"#### 情感极性 {'[锚定: ' + st.session_state.active_dim + ']' if st.session_state.active_dim else ''}")
    if not df_right.empty:
        sent_counts = df_right['Sentiment'].value_counts().reset_index()
        sent_counts.columns = ['Sentiment', 'Count']
        
        fig_sent = px.pie(sent_counts, values='Count', names='Sentiment', hole=0.5,
                          color='Sentiment', color_discrete_map={'正向': '#9D4EDD', '中立': '#8b8b93', '负向': '#F4D03F'})
        fig_sent.update_traces(hoverinfo='label+percent', textinfo='percent', textfont_size=14,
                               marker=dict(line=dict(color='rgba(0,0,0,0)', width=1)))
        fig_sent.update_layout(margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_family="Noto Sans SC")
        
        sel_sent = st.plotly_chart(fig_sent, use_container_width=True, theme="streamlit", on_select="rerun", selection_mode="points", key="sent_chart")
        
        if sel_sent and getattr(sel_sent, 'selection', None) and sel_sent.selection.points:
            pt = sel_sent.selection.points[0]
            pt_data = dict(pt) if isinstance(pt, dict) else pt.__dict__ if hasattr(pt, '__dict__') else {}
            
            clicked_sent = None
            known_sents = set(sent_counts['Sentiment'])
            
            for val in pt_data.values():
                if val in known_sents:
                    clicked_sent = val
                    break
                    
            if clicked_sent and st.session_state.active_sent != clicked_sent:
                st.session_state.active_sent = clicked_sent
                st.session_state.active_dim = None 
                st.rerun()

st.markdown("---")

st.markdown("#### 实体反馈溯源")
if not df_valid.empty:
    df_trace = df_valid
    if st.session_state.active_dim:
        df_trace = df_trace[df_trace['Dimension'] == st.session_state.active_dim]
    if st.session_state.active_sent:
        df_trace = df_trace[df_trace['Sentiment'] == st.session_state.active_sent]
        
    if not df_trace.empty:
        selected_entity = st.selectbox("实体锚定：", df_trace['Entity'].unique())
        filtered_df = df_trace[df_trace['Entity'] == selected_entity]
        st.dataframe(filtered_df[['Dimension', 'Sentiment', 'Summary']], use_container_width=True, hide_index=True)
    else:
        st.info("当前拓扑约束下无匹配实体。")