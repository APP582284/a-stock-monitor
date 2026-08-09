"""
A股实时资金流向监控看板
技术栈：Streamlit + AKShare + Plotly
数据源：东方财富（通过AKShare封装）
⚠️ 仅供个人学习研究，不构成任何投资建议
"""

import streamlit as st
import akshare as ak
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time
import traceback

# ======================== 页面配置 ========================
st.set_page_config(
    page_title="A股资金流向监控",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ======================== 自定义样式（暗色金融主题） ========================
st.markdown("""
<style>
    /* 全局背景 */
    .stApp {
        background-color: #0e1117;
        color: #c9d1d9;
    }
    /* 指标卡片 */
    div[data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 15px;
    }
    div[data-testid="stMetricLabel"] {
        color: #8b949e !important;
        font-size: 0.85rem !important;
    }
    div[data-testid="stMetricValue"] {
        color: #e6edf3 !important;
        font-size: 1.6rem !important;
    }
    /* 表格样式 */
    .dataframe {
        font-size: 0.85rem;
    }
    /* 标题样式 */
    h1, h2, h3 {
        color: #e6edf3 !important;
    }
    /* 侧边栏 */
    section[data-testid="stSidebar"] {
        background-color: #0d1117;
        border-right: 1px solid #30363d;
    }
    /* 涨红跌绿标签 */
    .tag-up {
        background-color: rgba(234, 57, 67, 0.15);
        color: #ea3943;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    .tag-down {
        background-color: rgba(22, 199, 132, 0.15);
        color: #16c784;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ======================== 数据获取函数 ========================

@st.cache_data(ttl=60, show_spinner=False)
def get_index_data():
    """获取大盘指数实时数据"""
    try:
        df = ak.stock_zh_index_spot_em()
        # 筛选核心指数
        target_codes = ["000001", "399001", "399006", "000300", "000016", "000905"]
        target_names = ["上证指数", "深证成指", "创业板指", "沪深300", "上证50", "中证500"]
        df_filtered = df[df["代码"].isin(target_codes)].copy()
        return df_filtered
    except Exception as e:
        st.error(f"指数数据获取失败: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def get_sector_fund_flow(indicator="今日"):
    """获取板块资金流向排名"""
    try:
        df = ak.stock_sector_fund_flow_rank(indicator=indicator, sector_type="行业资金流")
        return df
    except Exception as e:
        st.error(f"板块资金流数据获取失败: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def get_concept_fund_flow(indicator="今日"):
    """获取概念板块资金流向排名"""
    try:
        df = ak.stock_sector_fund_flow_rank(indicator=indicator, sector_type="概念资金流")
        return df
    except Exception as e:
        st.error(f"概念资金流数据获取失败: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def get_stock_fund_flow(indicator="今日"):
    """获取个股资金流向排名"""
    try:
        df = ak.stock_individual_fund_flow_rank(indicator=indicator)
        return df
    except Exception as e:
        st.error(f"个股资金流数据获取失败: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def get_market_fund_flow():
    """获取大盘历史资金流向"""
    try:
        df = ak.stock_market_fund_flow()
        return df
    except Exception as e:
        st.error(f"大盘资金流历史数据获取失败: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def get_all_stocks():
    """获取全市场A股实时行情"""
    try:
        df = ak.stock_zh_a_spot_em()
        return df
    except Exception as e:
        st.error(f"全市场行情获取失败: {e}")
        return pd.DataFrame()


# ======================== 辅助函数 ========================

def format_amount(value):
    """金额格式化：自动转为亿/万"""
    try:
        val = float(value)
        abs_val = abs(val)
        if abs_val >= 1e8:
            return f"{val / 1e8:.2f}亿"
        elif abs_val >= 1e4:
            return f"{val / 1e4:.2f}万"
        else:
            return f"{val:.2f}"
    except (ValueError, TypeError):
        return str(value)


def colorize_value(val):
    """涨跌颜色标记"""
    try:
        v = float(val)
        if v > 0:
            return f'<span style="color:#ea3943;font-weight:bold">+{v:.2f}%</span>'
        elif v < 0:
            return f'<span style="color:#16c784;font-weight:bold">{v:.2f}%</span>'
        else:
            return f'<span style="color:#8b949e">{v:.2f}%</span>'
    except (ValueError, TypeError):
        return str(val)


# ======================== 侧边栏 ========================

with st.sidebar:
    st.markdown("## ⚙️ 控制面板")

    # 自动刷新
    auto_refresh = st.toggle("🔄 自动刷新", value=True)
    if auto_refresh:
        refresh_interval = st.slider("刷新间隔（秒）", 30, 300, 60, step=30)
    else:
        refresh_interval = None

    st.divider()

    # 板块类型选择
    board_type = st.radio(
        "板块类型",
        ["行业资金流", "概念资金流"],
        horizontal=True,
    )

    # 统计周期
    period = st.selectbox("统计周期", ["今日", "5日", "10日"], index=0)

    # 显示数量
    top_n = st.slider("显示TOP数量", 5, 20, 10)

    st.divider()
    st.markdown("### 📌 快速导航")
    st.page_link("#📊-大盘概览", label="大盘概览", icon="📊")
    st.page_link("#🔥-板块资金流向", label="板块资金流向", icon="🔥")
    st.page_link("#🚀-个股资金异动", label="个股资金异动", icon="🚀")
    st.page_link("#📉-大盘资金趋势", label="大盘资金趋势", icon="📉")

    st.divider()
    st.caption(f"⏰ 数据源：东方财富 | AKShare")
    st.caption("⚠️ 仅供学习研究，不构成投资建议")


# ======================== 主页面 ========================

# 标题栏
st.markdown("# 📈 A股实时资金流向监控")
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.markdown(f"<p style='color:#8b949e;font-size:0.9rem'>最后更新：{now}</p>", unsafe_allow_html=True)

# ---------- 大盘概览 ----------
st.markdown("## 📊 大盘概览")

index_df = get_index_data()

if not index_df.empty:
    cols = st.columns(len(index_df))
    for i, (_, row) in enumerate(index_df.iterrows()):
        name = row.get("名称", "")
        price = row.get("最新价", 0)
        change_pct = row.get("涨跌幅", 0)
        change_amt = row.get("涨跌额", 0)
        delta_color = "normal"
        try:
            if float(change_pct) < 0:
                delta_color = "inverse"  # 绿色表示下跌
        except (ValueError, TypeError):
            pass
        with cols[i]:
            try:
                st.metric(
                    label=name,
                    value=f"{float(price):.2f}",
                    delta=f"{float(change_pct):.2f}%",
                    delta_color=delta_color,
                )
            except (ValueError, TypeError):
                st.metric(label=name, value=str(price), delta=str(change_pct))
else:
    st.warning("指数数据暂未获取，请检查网络连接或稍后刷新")

st.divider()

# ---------- 板块资金流向 ----------
st.markdown("## 🔥 板块资金流向")

# 根据侧边栏选择获取数据
if board_type == "行业资金流":
    sector_df = get_sector_fund_flow(indicator=period)
else:
    sector_df = get_concept_fund_flow(indicator=period)

if not sector_df.empty:
    # 确定列名前缀
    prefix = period if period != "今日" else "今日"

    # 找到主力净流入列
    flow_col = None
    flow_pct_col = None
    change_col = None
    name_col = None

    for col in sector_df.columns:
        if "主力净流入" in col and "净额" in col and "净占比" not in col:
            flow_col = col
        elif "主力净流入" in col and "净占比" in col:
            flow_pct_col = col
        elif "涨跌幅" in col:
            change_col = col
        elif col in ["板块名称", "名称"]:
            name_col = col

    if name_col is None:
        # 尝试用第二列作为名称列
        name_col = sector_df.columns[1] if len(sector_df.columns) > 1 else sector_df.columns[0]

    if flow_col:
        # 确保数值列为数字类型
        sector_df[flow_col] = pd.to_numeric(sector_df[flow_col], errors="coerce")
        if flow_pct_col:
            sector_df[flow_pct_col] = pd.to_numeric(sector_df[flow_pct_col], errors="coerce")
        if change_col:
            sector_df[change_col] = pd.to_numeric(sector_df[change_col], errors="coerce")

        # 排序
        sector_sorted = sector_df.sort_values(by=flow_col, ascending=False).reset_index(drop=True)

        # ---- 资金流入/流出 TOP N ----
        col_in, col_out = st.columns(2)

        with col_in:
            st.markdown(f"#### 💰 资金流入 TOP{top_n}")
            top_in = sector_sorted.head(top_n)
            display_in = top_in[[name_col]].copy()
            if change_col:
                display_in["涨跌幅"] = top_in[change_col].apply(lambda x: f"{float(x):.2f}%" if pd.notna(x) else "-")
            display_in["主力净流入"] = top_in[flow_col].apply(format_amount)
            if flow_pct_col:
                display_in["净占比"] = top_in[flow_pct_col].apply(lambda x: f"{float(x):.2f}%" if pd.notna(x) else "-")
            st.dataframe(display_in, use_container_width=True, hide_index=True)

        with col_out:
            st.markdown(f"#### 💧 资金流出 TOP{top_n}")
            top_out = sector_sorted.tail(top_n).iloc[::-1]
            display_out = top_out[[name_col]].copy()
            if change_col:
                display_out["涨跌幅"] = top_out[change_col].apply(lambda x: f"{float(x):.2f}%" if pd.notna(x) else "-")
            display_out["主力净流出"] = top_out[flow_col].apply(lambda x: format_amount(abs(float(x))) if pd.notna(x) else "-")
            if flow_pct_col:
                display_out["净占比"] = top_out[flow_pct_col].apply(lambda x: f"{float(x):.2f}%" if pd.notna(x) else "-")
            st.dataframe(display_out, use_container_width=True, hide_index=True)

        # ---- 板块资金流向可视化 ----
        st.markdown("#### 📊 资金流向分布图")

        # 取流入流出各前10做对比图
        top_compare = pd.concat([sector_sorted.head(10), sector_sorted.tail(10)])
        if name_col in top_compare.columns and flow_col in top_compare.columns:
            fig = px.bar(
                top_compare,
                x=name_col,
                y=flow_col,
                color=flow_col,
                color_continuous_scale=["#16c784", "#30363d", "#ea3943"],
                title=f"{period} {board_type} 主力净流入/流出对比",
                labels={flow_col: "主力净流入（元）", name_col: "板块"},
                height=450,
            )
            fig.update_layout(
                plot_bgcolor="#0e1117",
                paper_bgcolor="#0e1117",
                font_color="#c9d1d9",
                xaxis_tickangle=-45,
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

        # ---- 热力图 ----
        st.markdown("#### 🗺️ 板块热力图")
        heatmap_data = sector_sorted[[name_col, flow_col]].copy()
        heatmap_data["abs_flow"] = heatmap_data[flow_col].abs()
        heatmap_data = heatmap_data.dropna()

        if not heatmap_data.empty and len(heatmap_data) > 0:
            fig_heatmap = px.treemap(
                heatmap_data.head(50),
                path=[name_col],
                values="abs_flow",
                color=flow_col,
                color_continuous_scale=["#16c784", "#1a1a2e", "#ea3943"],
                title=f"{board_type}资金热力图（面积=资金绝对值，颜色=流入/流出）",
                height=500,
            )
            fig_heatmap.update_layout(
                plot_bgcolor="#0e1117",
                paper_bgcolor="#0e1117",
                font_color="#c9d1d9",
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)

else:
    st.warning("板块资金流向数据暂未获取，可能非交易时段或接口维护中")

st.divider()

# ---------- 个股资金异动 ----------
st.markdown("## 🚀 个股资金异动")

stock_df = get_stock_fund_flow(indicator=period)

if not stock_df.empty:
    # 找到主力净流入列
    s_flow_col = None
    s_flow_pct_col = None
    for col in stock_df.columns:
        if "主力净流入" in col and "净额" in col and "净占比" not in col:
            s_flow_col = col
        elif "主力净流入" in col and "净占比" in col:
            s_flow_pct_col = col

    if s_flow_col:
        stock_df[s_flow_col] = pd.to_numeric(stock_df[s_flow_col], errors="coerce")
        stock_sorted = stock_df.sort_values(by=s_flow_col, ascending=False).reset_index(drop=True)

        col_s_in, col_s_out = st.columns(2)

        with col_s_in:
            st.markdown(f"#### 🔴 主力净流入 TOP{top_n}")
            top_stocks_in = stock_sorted.head(top_n)
            display_s_in = top_stocks_in[["代码", "名称"]].copy() if "代码" in top_stocks_in.columns else top_stocks_in[["名称"]].copy()
            if "最新价" in top_stocks_in.columns:
                display_s_in["最新价"] = top_stocks_in["最新价"].apply(lambda x: f"{float(x):.2f}" if pd.notna(x) else "-")
            if "今日涨跌幅" in top_stocks_in.columns:
                display_s_in["涨跌幅"] = top_stocks_in["今日涨跌幅"].apply(lambda x: f"{float(x):.2f}%" if pd.notna(x) else "-")
            display_s_in["主力净流入"] = top_stocks_in[s_flow_col].apply(format_amount)
            if s_flow_pct_col:
                display_s_in["净占比"] = top_stocks_in[s_flow_pct_col].apply(lambda x: f"{float(x):.2f}%" if pd.notna(x) else "-")
            st.dataframe(display_s_in, use_container_width=True, hide_index=True)

        with col_s_out:
            st.markdown(f"#### 🟢 主力净流出 TOP{top_n}")
            top_stocks_out = stock_sorted.tail(top_n).iloc[::-1]
            display_s_out = top_stocks_out[["代码", "名称"]].copy() if "代码" in top_stocks_out.columns else top_stocks_out[["名称"]].copy()
            if "最新价" in top_stocks_out.columns:
                display_s_out["最新价"] = top_stocks_out["最新价"].apply(lambda x: f"{float(x):.2f}" if pd.notna(x) else "-")
            if "今日涨跌幅" in top_stocks_out.columns:
                display_s_out["涨跌幅"] = top_stocks_out["今日涨跌幅"].apply(lambda x: f"{float(x):.2f}%" if pd.notna(x) else "-")
            display_s_out["主力净流出"] = top_stocks_out[s_flow_col].apply(lambda x: format_amount(abs(float(x))) if pd.notna(x) else "-")
            if s_flow_pct_col:
                display_s_out["净占比"] = top_stocks_out[s_flow_pct_col].apply(lambda x: f"{float(x):.2f}%" if pd.notna(x) else "-")
            st.dataframe(display_s_out, use_container_width=True, hide_index=True)

        # ---- 个股资金流向柱状图 ----
        st.markdown("#### 📊 个股资金净流入/流出对比")
        top_stock_compare = pd.concat([stock_sorted.head(10), stock_sorted.tail(10)])
        label_col = "名称" if "名称" in top_stock_compare.columns else top_stock_compare.columns[1]
        fig_stock = px.bar(
            top_stock_compare,
            x=label_col,
            y=s_flow_col,
            color=s_flow_col,
            color_continuous_scale=["#16c784", "#30363d", "#ea3943"],
            title=f"{period} 个股主力净流入/流出对比",
            labels={s_flow_col: "主力净流入（元）", label_col: "股票"},
            height=400,
        )
        fig_stock.update_layout(
            plot_bgcolor="#0e11

