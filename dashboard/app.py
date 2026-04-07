"""
AI Hedge Fund Simulator — Streamlit Dashboard
Phase 6: Fund Manager Command Center
Run with: streamlit run dashboard/app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pickle
import os
import sys
import warnings
from datetime import datetime, timedelta
from dotenv import load_dotenv

warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────
# PAGE CONFIG — must be the first Streamlit call
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI Hedge Fund",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# PATH SETUP
# Ensures imports work whether you run from project root or dashboard/
# ─────────────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# ─────────────────────────────────────────────
# PROJECT IMPORTS
# ─────────────────────────────────────────────
from config import TABLES, MODEL_VERSION   # MODEL_VERSION added below
from data.db import get_engine

# ─────────────────────────────────────────────
# MODEL VERSION — update this when you retrain
# Must match the date suffix in your saved model filenames
# e.g. xgboost_v2_20260405.pkl → VERSION = '20260405'
# ─────────────────────────────────────────────
MODEL_VERSION = "20260405"   # ← change this after each retraining session

MODEL_DIR = os.path.join(PROJECT_ROOT, "models")

# ─────────────────────────────────────────────
# CUSTOM CSS — dark finance theme
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #0e1117; }

    /* Metric cards */
    div[data-testid="metric-container"] {
        background: #1a1d27;
        border: 1px solid #2d3748;
        border-radius: 8px;
        padding: 16px;
    }

    /* BUY card */
    .buy-card {
        background: linear-gradient(135deg, #0d2b1a, #0a3d1f);
        border: 1px solid #22c55e;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .buy-card h3 { color: #22c55e; margin: 0 0 4px 0; font-size: 1.1rem; }

    /* SELL card */
    .sell-card {
        background: linear-gradient(135deg, #2b0d0d, #3d0a0a);
        border: 1px solid #ef4444;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .sell-card h3 { color: #ef4444; margin: 0 0 4px 0; font-size: 1.1rem; }

    /* HOLD card */
    .hold-card {
        background: linear-gradient(135deg, #1a1a0d, #2b2a08);
        border: 1px solid #eab308;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .hold-card h3 { color: #eab308; margin: 0 0 4px 0; font-size: 1.1rem; }

    /* Metric values inside cards */
    .card-metric { color: #e2e8f0; font-size: 0.85rem; margin: 2px 0; }
    .card-highlight { color: #94a3b8; font-size: 0.8rem; }

    /* Section headers */
    .section-header {
        color: #7dd3fc;
        font-size: 1.3rem;
        font-weight: 700;
        border-bottom: 1px solid #2d3748;
        padding-bottom: 6px;
        margin-bottom: 16px;
    }

    /* Regime badge */
    .regime-bull   { background:#064e3b; color:#34d399; padding:4px 12px;
                     border-radius:20px; font-size:0.85rem; font-weight:600; }
    .regime-bear   { background:#450a0a; color:#f87171; padding:4px 12px;
                     border-radius:20px; font-size:0.85rem; font-weight:600; }
    .regime-crisis { background:#422006; color:#fb923c; padding:4px 12px;
                     border-radius:20px; font-size:0.85rem; font-weight:600; }
    .regime-side   { background:#1e1b4b; color:#a5b4fc; padding:4px 12px;
                     border-radius:20px; font-size:0.85rem; font-weight:600; }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# SECTION 1 — MODEL & DATA LOADING
# All loading is cached so Streamlit doesn't reload on every click
# ═══════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner="Loading AI models...")
def load_models(version: str):
    """
    Loads all saved model files from models/saved/.
    Cached at resource level — survives across reruns.
    Returns a dict of model objects.
    """
    import joblib
    import tensorflow as tf

    paths = {
        "xgb":          os.path.join(MODEL_DIR, f"xgboost_v2_{version}.pkl"),
        "lgb":          os.path.join(MODEL_DIR, f"lightgbm_v2_{version}.pkl"),
        "lstm":         os.path.join(MODEL_DIR, f"lstm_v2_{version}.keras"),
        "hmm":          os.path.join(MODEL_DIR, "hmm_model.pkl"),
        "hmm_scaler":   os.path.join(MODEL_DIR, "hmm_scaler.pkl"),
        "feature_cols": os.path.join(MODEL_DIR, "feature_cols.pkl"),
        "sector_map":   os.path.join(MODEL_DIR, "sector_map.pkl"),
        "regime_hist":  os.path.join(MODEL_DIR, "regime_history.pkl"),
    }

    models = {}
    missing = []

    for key, path in paths.items():
        if not os.path.exists(path):
            missing.append(path)
            continue
        if key == "lstm":
            models[key] = tf.keras.models.load_model(path)
        elif key in ("xgb", "lgb", "hmm", "hmm_scaler", "sector_map",
                     "feature_cols", "regime_hist"):
            with open(path, "rb") as f:
                models[key] = pickle.load(f)

    if missing:
        st.error(f"Missing model files:\n" + "\n".join(missing))
        st.stop()

    return models


@st.cache_data(ttl=3600, show_spinner="Loading market data from MySQL...")
def load_features_from_db() -> pd.DataFrame:
    """
    Loads features_master from MySQL.
    TTL = 1 hour — refreshes every hour automatically.
    """
    engine = get_engine()
    df = pd.read_sql(f"SELECT * FROM {TABLES['features']}", engine)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values(['Ticker', 'Date']).reset_index(drop=True)
    return df


@st.cache_data(ttl=3600, show_spinner="Loading OHLCV data...")
def load_ohlcv_from_db() -> pd.DataFrame:
    """Loads raw OHLCV for current price lookups."""
    engine = get_engine()
    df = pd.read_sql(
        f"SELECT Ticker, Date, Close, Volume FROM {TABLES['ohlcv']}",
        engine
    )
    df['Date'] = pd.to_datetime(df['Date'])
    return df


# ═══════════════════════════════════════════════════════════════
# SECTION 2 — SIGNAL GENERATION
# Runs inference using all 3 models, combines into ensemble signal
# ═══════════════════════════════════════════════════════════════

# Regime weights — same as your ensemble notebook
# Format: {regime_label: {model: weight}}
REGIME_WEIGHTS = {
    "Bull":     {"xgb": 0.45, "lgb": 0.35, "lstm": 0.20},
    "Bear":     {"xgb": 0.40, "lgb": 0.40, "lstm": 0.20},
    "Elevated": {"xgb": 0.35, "lgb": 0.35, "lstm": 0.30},
    "Sideways": {"xgb": 0.40, "lgb": 0.40, "lstm": 0.20},
}
REGIME_LABELS = {0: "Bull", 1: "Bear", 2: "Elevated", 3: "Sideways"}
TOP_N    = 10   # top % flagged as BUY
BOTTOM_N = 10   # bottom % flagged as SELL
LOOKBACK = 60   # LSTM sequence length


def detect_regime(models: dict, df: pd.DataFrame, latest_date) -> str:
    """Runs HMM on latest features to detect current market regime."""
    
    # Check exactly how many features the scaler expects
    n_expected = models['hmm_scaler'].n_features_in_
    
    # Try these candidates in order until we find enough
    hmm_candidates = [
        'Nifty_Return', 'India_VIX', 'Return_5d', 'Return_21d',
        'Volatility_20d', 'Return_1d', 'RSI_14', 'MACD'
    ]
    
    available = [c for c in hmm_candidates if c in df.columns]
    
    # If we can't match exactly what the scaler expects, fall back safely
    if len(available) < n_expected:
        return "Sideways"
    
    # Use exactly the number of features the scaler was trained on
    use_cols = available[:n_expected]
    
    recent = df[df['Date'] == latest_date][use_cols].dropna()
    if recent.empty:
        return "Sideways"
    
    try:
        X = models['hmm_scaler'].transform(recent.mean().values.reshape(1, -1))
        regime_id = int(models['hmm'].predict(X)[0])
        return REGIME_LABELS.get(regime_id, "Sideways")
    except Exception:
        return "Sideways"
def generate_signals(_models_key: str, _df_hash: int) -> pd.DataFrame:
    """
    Runs ensemble inference on the latest available date.
    Arguments use underscore prefix — Streamlit skips hashing them.
    _models_key / _df_hash are sentinel values used to bust cache when
    models or data change.

    Returns DataFrame with one row per stock, columns:
        Ticker, Signal_Score, Signal, XGB_Score, LGB_Score, LSTM_Score,
        Close, ATR_14, ATR_pct, Sector
    """
    models = load_models(MODEL_VERSION)
    df     = load_features_from_db()

    feature_cols = models['feature_cols']
    sector_map   = models['sector_map']

    latest_date = df['Date'].max()
    latest_df   = df[df['Date'] == latest_date].copy()

    # ── XGBoost scores ──────────────────────────────────────────
    X_latest = latest_df[feature_cols].fillna(0)
    xgb_scores = models['xgb'].predict(X_latest)

    # ── LightGBM scores ─────────────────────────────────────────
    lgb_scores = models['lgb'].predict(X_latest)

    # ── LSTM scores (batched — all stocks at once) ───────────────
    tickers = latest_df['Ticker'].values
    lstm_scores = []

    for ticker in tickers:
        stock_hist = (
            df[df['Ticker'] == ticker]
            .sort_values('Date')
            .tail(LOOKBACK)[feature_cols]
            .fillna(0)
            .values
        )
        if len(stock_hist) < LOOKBACK:
            pad = np.zeros((LOOKBACK - len(stock_hist), len(feature_cols)))
            stock_hist = np.vstack([pad, stock_hist])
        lstm_scores.append(stock_hist)

    lstm_input  = np.array(lstm_scores)           # (n_stocks, 60, n_features)
    lstm_preds  = models['lstm'].predict(lstm_input, verbose=0).flatten()

    # ── Detect regime & get weights ─────────────────────────────
    regime      = detect_regime(models, df, latest_date)
    weights     = REGIME_WEIGHTS.get(regime, REGIME_WEIGHTS["Sideways"])

    # ── Normalise each model's scores to [0,1] before combining ─
    def norm(arr):
        mn, mx = arr.min(), arr.max()
        return (arr - mn) / (mx - mn + 1e-9)

    ensemble_scores = (
        weights['xgb']  * norm(xgb_scores) +
        weights['lgb']  * norm(lgb_scores) +
        weights['lstm'] * norm(lstm_preds)
    )

    # ── Build signals DataFrame ──────────────────────────────────
    signals = latest_df[['Ticker', 'Close', 'ATR_14']].copy()
    signals['XGB_Score']    = xgb_scores
    signals['LGB_Score']    = lgb_scores
    signals['LSTM_Score']   = lstm_preds
    signals['Signal_Score'] = ensemble_scores
    signals['ATR_pct']      = signals['ATR_14'] / signals['Close'].replace(0, np.nan)
    signals['Sector']       = signals['Ticker'].map(sector_map).fillna('Unknown')
    signals['Latest_Date']  = latest_date
    signals['Regime']       = regime

    # ── Classify as BUY / SELL / HOLD ───────────────────────────
    n       = len(signals)
    top_cut = np.percentile(ensemble_scores, 100 - TOP_N)
    bot_cut = np.percentile(ensemble_scores, BOTTOM_N)

    signals['Signal'] = 'HOLD'
    signals.loc[signals['Signal_Score'] >= top_cut, 'Signal'] = 'BUY'
    signals.loc[signals['Signal_Score'] <= bot_cut, 'Signal'] = 'SELL'

    return signals.reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════
# SECTION 3 — PORTFOLIO OPTIMIZER
# Normalized ATR fix applied here (ATR/Close instead of raw ATR)
# ═══════════════════════════════════════════════════════════════

def optimize_portfolio(signals: pd.DataFrame, capital_inr: float) -> pd.DataFrame:
    """
    Risk-parity portfolio allocation across BUY stocks.
    Uses normalized ATR (ATR_14 / Close) as the risk proxy so that
    high-priced and low-priced stocks are treated equally.

    Returns DataFrame with columns:
        Ticker, Signal_Score, Close, Sector, ATR_pct,
        Weight, Allocated_INR, Shares
    """
    buy_stocks = signals[signals['Signal'] == 'BUY'].copy()

    if buy_stocks.empty:
        return pd.DataFrame()

    # ── Normalized ATR risk proxy (the fix for IDFCFIRSTB over-weighting) ──
    risk_proxy = buy_stocks['ATR_pct'].fillna(buy_stocks['ATR_pct'].median())
    risk_proxy = risk_proxy.replace(0, risk_proxy.median())   # avoid div/0

    # Risk parity: weight ∝ 1 / risk
    inv_risk   = 1.0 / risk_proxy
    weights    = inv_risk / inv_risk.sum()

    buy_stocks = buy_stocks.copy()
    buy_stocks['Weight']        = weights.values
    buy_stocks['Allocated_INR'] = buy_stocks['Weight'] * capital_inr
    buy_stocks['Shares']        = (
        buy_stocks['Allocated_INR'] / buy_stocks['Close']
    ).astype(int)

    # Drop stocks where capital is too small to buy even 1 share
    buy_stocks = buy_stocks[buy_stocks['Shares'] >= 1]

    # Recalculate actual allocated after integer rounding
    buy_stocks['Actual_INR'] = buy_stocks['Shares'] * buy_stocks['Close']

    return buy_stocks.sort_values('Signal_Score', ascending=False).reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════
# SECTION 4 — BACKTEST METRICS
# Computes portfolio-level performance metrics from signals history
# ═══════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600, show_spinner="Computing performance metrics...")
def compute_backtest_metrics(_df_hash: int) -> dict:
    """
    Runs the backtest engine on features_master to compute
    Sharpe, Drawdown, CAGR, Win Rate, Alpha, Beta.
    Uses NEXT-day returns (no lookahead bias).
    """
    models = load_models(MODEL_VERSION)
    df     = load_features_from_db()

    feature_cols = models['feature_cols']
    dates        = sorted(df['Date'].unique())

    portfolio_returns = []

    for i, date in enumerate(dates[:-1]):   # skip last day (no next-day return)
        next_date = dates[i + 1]
        day_df    = df[df['Date'] == date].copy()

        if day_df.empty:
            continue

        X = day_df[feature_cols].fillna(0)
        xgb_s = models['xgb'].predict(X)
        lgb_s = models['lgb'].predict(X)

        # Use simplified XGB+LGB only for backtest speed (LSTM is slow to loop)
        combined = 0.5 * xgb_s + 0.5 * lgb_s

        n       = len(day_df)
        top_cut = np.percentile(combined, 100 - TOP_N)
        bot_cut = np.percentile(combined, BOTTOM_N)

        buy_mask  = combined >= top_cut
        sell_mask = combined <= bot_cut

        # Next-day returns for long (BUY) and short (SELL) legs
        next_df = df[df['Date'] == next_date].set_index('Ticker')

        longs  = day_df[buy_mask]['Ticker'].values
        shorts = day_df[sell_mask]['Ticker'].values

        long_rets  = []
        short_rets = []

        for t in longs:
            if t in next_df.index and 'Return_1d' in next_df.columns:
                r = next_df.loc[t, 'Return_1d']
                if pd.notna(r):
                    long_rets.append(r)

        for t in shorts:
            if t in next_df.index and 'Return_1d' in next_df.columns:
                r = next_df.loc[t, 'Return_1d']
                if pd.notna(r):
                    short_rets.append(-r)   # short = inverted return

        # Equal-weight average of long + short legs
        all_rets = long_rets + short_rets
        if all_rets:
            portfolio_returns.append({
                'Date':   date,
                'Return': np.mean(all_rets),
            })

    if not portfolio_returns:
        return {}

    ret_df = pd.DataFrame(portfolio_returns).set_index('Date')
    ret_df = ret_df.sort_index()

    # ── Transaction costs: 0.1% per trade (brokerage + slippage) ──
    ret_df['Return'] = ret_df['Return'] - 0.001

    # ── Cumulative equity curve ──────────────────────────────────
    ret_df['Cumulative'] = (1 + ret_df['Return']).cumprod()

    # ── Drawdown ─────────────────────────────────────────────────
    rolling_max = ret_df['Cumulative'].cummax()
    drawdown    = (ret_df['Cumulative'] - rolling_max) / rolling_max
    max_dd      = drawdown.min()

    # ── Sharpe (annualized, risk-free = 6.5% for India) ──────────
    rf_daily   = 0.065 / 252
    excess     = ret_df['Return'] - rf_daily
    sharpe     = (excess.mean() / excess.std()) * np.sqrt(252) if excess.std() > 0 else 0

    # ── Sortino ──────────────────────────────────────────────────
    downside   = excess[excess < 0].std()
    sortino    = (excess.mean() / downside) * np.sqrt(252) if downside > 0 else 0

    # ── CAGR ─────────────────────────────────────────────────────
    n_years   = len(ret_df) / 252
    final_val = ret_df['Cumulative'].iloc[-1]
    cagr      = (final_val ** (1 / n_years) - 1) if n_years > 0 else 0

    # ── Win Rate ─────────────────────────────────────────────────
    win_rate  = (ret_df['Return'] > 0).mean()

    # ── Nifty benchmark (use Nifty_Return column if available) ───
    nifty_col = 'Nifty_Return'
    nifty_cagr = None
    alpha      = None
    beta_val   = None

    if nifty_col in df.columns:
        nifty_daily = (
            df.groupby('Date')[nifty_col]
            .mean()
            .reindex(ret_df.index)
            .fillna(0)
        )
        nifty_cum  = (1 + nifty_daily).cumprod()
        nifty_cagr = (nifty_cum.iloc[-1] ** (1 / n_years) - 1) if n_years > 0 else 0
        alpha      = cagr - nifty_cagr

        cov_matrix = np.cov(ret_df['Return'].values, nifty_daily.values)
        beta_val   = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] != 0 else 1.0

    # ── Annual volatility ─────────────────────────────────────────
    annual_vol = ret_df['Return'].std() * np.sqrt(252)

    return {
        "cagr":        cagr,
        "sharpe":      sharpe,
        "sortino":     sortino,
        "max_dd":      max_dd,
        "win_rate":    win_rate,
        "annual_vol":  annual_vol,
        "nifty_cagr":  nifty_cagr,
        "alpha":       alpha,
        "beta":        beta_val,
        "ret_df":      ret_df,
        "drawdown":    drawdown,
        "n_days":      len(ret_df),
    }


# ═══════════════════════════════════════════════════════════════
# SECTION 5 — SIDEBAR
# ═══════════════════════════════════════════════════════════════

def render_sidebar() -> float:
    """
    Renders the sidebar. Returns the capital amount entered by the user.
    Capital input lives in sidebar so it's always accessible.
    """
    with st.sidebar:
        st.markdown("## 🏦 AI Hedge Fund")
        st.markdown("*Indian Equity Markets — Nifty 100*")
        st.divider()

        # ── Capital input ──────────────────────────────────────
        st.markdown("### 💰 Fund Capital")
        capital_lakhs = st.number_input(
            "Enter capital (₹ Lakhs)",
            min_value=1.0,
            max_value=100000.0,
            value=10.0,
            step=1.0,
            help="1 Lakh = ₹1,00,000"
        )
        capital_inr = capital_lakhs * 100_000

        st.markdown(
            f"<div style='color:#94a3b8; font-size:0.85rem;'>"
            f"= ₹{capital_inr:,.0f}</div>",
            unsafe_allow_html=True
        )
        st.divider()

        # ── Data refresh button ────────────────────────────────
        st.markdown("### 🔄 Data")
        if st.button("Refresh All Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown(
            "<div style='color:#64748b; font-size:0.75rem;'>"
            "Data auto-refreshes every 1 hour</div>",
            unsafe_allow_html=True
        )
        st.divider()

        # ── Model info ─────────────────────────────────────────
        st.markdown("### 🤖 Models")
        st.markdown(
            f"<div style='color:#94a3b8; font-size:0.82rem;'>"
            f"Version: <b style='color:#7dd3fc'>{MODEL_VERSION}</b><br>"
            f"XGBoost ✅ | LightGBM ✅<br>LSTM ✅ | HMM ✅"
            f"</div>",
            unsafe_allow_html=True
        )
        st.divider()

        # ── Disclaimer ─────────────────────────────────────────
        st.markdown(
            "<div style='color:#475569; font-size:0.72rem;'>"
            "⚠️ For educational purposes only. "
            "Not financial advice. Past performance does not "
            "guarantee future results.</div>",
            unsafe_allow_html=True
        )

    return capital_inr


# ═══════════════════════════════════════════════════════════════
# SECTION 6 — PANEL RENDERERS
# Each panel is a separate function — clean and modular
# ═══════════════════════════════════════════════════════════════

def render_panel1_recommendations(signals: pd.DataFrame):
    """Panel 1 — Today's BUY / SELL / HOLD recommendation cards."""

    st.markdown('<div class="section-header">📋 Today\'s Recommendations</div>',
                unsafe_allow_html=True)

    latest_date = signals['Latest_Date'].iloc[0]
    regime      = signals['Regime'].iloc[0]

    # Regime badge
    regime_class = {
        "Bull": "regime-bull", "Bear": "regime-bear",
        "Elevated": "regime-crisis", "Sideways": "regime-side"
    }.get(regime, "regime-side")

    regime_emoji = {
        "Bull": "🐂", "Bear": "🐻",
        "Elevated": "⚡", "Sideways": "↔️"
    }.get(regime, "")

    col_date, col_regime, col_counts = st.columns([2, 1.5, 2.5])

    with col_date:
        st.metric("Signal Date", latest_date.strftime("%d %b %Y"))

    with col_regime:
        st.markdown(
            f"<br><span class='{regime_class}'>"
            f"{regime_emoji} {regime} Market</span>",
            unsafe_allow_html=True
        )

    with col_counts:
        buys  = (signals['Signal'] == 'BUY').sum()
        sells = (signals['Signal'] == 'SELL').sum()
        holds = (signals['Signal'] == 'HOLD').sum()
        st.markdown(
            f"<br><span style='color:#22c55e'>▲ {buys} BUY</span> &nbsp;"
            f"<span style='color:#ef4444'>▼ {sells} SELL</span> &nbsp;"
            f"<span style='color:#eab308'>— {holds} HOLD</span>",
            unsafe_allow_html=True
        )

    st.divider()

    # ── Three columns: BUY | SELL | HOLD ──────────────────────
    col_buy, col_sell, col_hold = st.columns(3)

    buy_stocks  = signals[signals['Signal'] == 'BUY'].sort_values(
        'Signal_Score', ascending=False)
    sell_stocks = signals[signals['Signal'] == 'SELL'].sort_values(
        'Signal_Score', ascending=True)
    hold_stocks = signals[signals['Signal'] == 'HOLD'].sort_values(
        'Signal_Score', ascending=False).head(8)

    with col_buy:
        st.markdown("### 🟢 BUY")
        for _, row in buy_stocks.iterrows():
            confidence = int(row['Signal_Score'] * 100)
            st.markdown(
                f"""<div class="buy-card">
                    <h3>📈 {row['Ticker'].replace('.NS','')}</h3>
                    <p class="card-metric">₹{row['Close']:,.2f} &nbsp;|&nbsp;
                       Sector: {row['Sector']}</p>
                    <p class="card-metric">Confidence: <b style='color:#86efac'>
                       {confidence}%</b></p>
                    <p class="card-highlight">Score: {row['Signal_Score']:.4f}</p>
                </div>""",
                unsafe_allow_html=True
            )

    with col_sell:
        st.markdown("### 🔴 SELL")
        for _, row in sell_stocks.iterrows():
            confidence = int((1 - row['Signal_Score']) * 100)
            st.markdown(
                f"""<div class="sell-card">
                    <h3>📉 {row['Ticker'].replace('.NS','')}</h3>
                    <p class="card-metric">₹{row['Close']:,.2f} &nbsp;|&nbsp;
                       Sector: {row['Sector']}</p>
                    <p class="card-metric">Confidence: <b style='color:#fca5a5'>
                       {confidence}%</b></p>
                    <p class="card-highlight">Score: {row['Signal_Score']:.4f}</p>
                </div>""",
                unsafe_allow_html=True
            )

    with col_hold:
        st.markdown("### 🟡 HOLD (Top 8)")
        for _, row in hold_stocks.iterrows():
            st.markdown(
                f"""<div class="hold-card">
                    <h3>⏸ {row['Ticker'].replace('.NS','')}</h3>
                    <p class="card-metric">₹{row['Close']:,.2f} &nbsp;|&nbsp;
                       Sector: {row['Sector']}</p>
                    <p class="card-highlight">Score: {row['Signal_Score']:.4f}</p>
                </div>""",
                unsafe_allow_html=True
            )


def render_panel2_portfolio(portfolio: pd.DataFrame, signals: pd.DataFrame, capital_inr: float):
    """Panel 2 — Portfolio Overview: allocation pie, P&L, beta."""

    st.markdown('<div class="section-header">💼 Portfolio Overview</div>',
                unsafe_allow_html=True)

    if portfolio.empty:
        st.warning("No BUY signals today — portfolio is empty.")
        return

    # ── Top KPI row ───────────────────────────────────────────
    deployed    = portfolio['Actual_INR'].sum()
    cash        = capital_inr - deployed
    cash_pct    = cash / capital_inr * 100
    n_positions = len(portfolio)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Capital",    f"₹{capital_inr/1e5:.1f}L")
    c2.metric("Deployed",         f"₹{deployed/1e5:.1f}L",
              delta=f"{deployed/capital_inr*100:.1f}%")
    c3.metric("Cash Reserve",     f"₹{cash/1e5:.1f}L",
              delta=f"{cash_pct:.1f}%")
    c4.metric("Active Positions", str(n_positions))

    st.divider()

    col_alloc, col_sector = st.columns(2)

    # ── Stock allocation pie ──────────────────────────────────
    with col_alloc:
        st.markdown("**Allocation by Stock**")
        fig_alloc = go.Figure(go.Pie(
            labels=[t.replace('.NS', '') for t in portfolio['Ticker']],
            values=portfolio['Actual_INR'].round(0),
            hole=0.45,
            textinfo='label+percent',
            textfont_size=11,
            marker=dict(line=dict(color='#0e1117', width=2)),
        ))
        fig_alloc.update_layout(
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#e2e8f0',
            height=320,
            margin=dict(t=10, b=10, l=10, r=10),
        )
        st.plotly_chart(fig_alloc, use_container_width=True)

    # ── Sector allocation pie ─────────────────────────────────
    with col_sector:
        st.markdown("**Allocation by Sector**")
        sector_alloc = (
            portfolio.groupby('Sector')['Actual_INR']
            .sum()
            .reset_index()
        )
        fig_sector = go.Figure(go.Pie(
            labels=sector_alloc['Sector'],
            values=sector_alloc['Actual_INR'].round(0),
            hole=0.45,
            textinfo='label+percent',
            textfont_size=11,
            marker=dict(line=dict(color='#0e1117', width=2)),
        ))
        fig_sector.update_layout(
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#e2e8f0',
            height=320,
            margin=dict(t=10, b=10, l=10, r=10),
        )
        st.plotly_chart(fig_sector, use_container_width=True)

    st.divider()

    # ── Holdings table ────────────────────────────────────────
    st.markdown("**Holdings Detail**")
    display_cols = {
        'Ticker':       'Ticker',
        'Sector':       'Sector',
        'Signal_Score': 'AI Score',
        'Close':        'Price (₹)',
        'Shares':       'Shares',
        'Actual_INR':   'Value (₹)',
        'Weight':       'Weight %',
    }

    disp_df = portfolio[list(display_cols.keys())].rename(columns=display_cols).copy()
    disp_df['Ticker']    = disp_df['Ticker'].str.replace('.NS', '', regex=False)
    disp_df['AI Score']  = disp_df['AI Score'].round(4)
    disp_df['Price (₹)'] = disp_df['Price (₹)'].map('₹{:,.2f}'.format)
    disp_df['Value (₹)'] = disp_df['Value (₹)'].map('₹{:,.0f}'.format)
    disp_df['Weight %']  = (disp_df['Weight %'] * 100).map('{:.1f}%'.format)

    st.dataframe(disp_df, use_container_width=True, hide_index=True)


def render_panel3_metrics(metrics: dict):
    """Panel 3 — Performance Metrics: Sharpe, CAGR, Drawdown, Win Rate, etc."""

    st.markdown('<div class="section-header">📊 Performance Metrics</div>',
                unsafe_allow_html=True)

    if not metrics:
        st.warning("Backtest data not available.")
        return

    # ── Row 1: Core metrics ────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)

    cagr_pct = metrics['cagr'] * 100
    nifty_pct = metrics['nifty_cagr'] * 100 if metrics.get('nifty_cagr') else None

    c1.metric(
        "CAGR",
        f"{cagr_pct:.1f}%",
        delta=f"vs Nifty {nifty_pct:.1f}%" if nifty_pct else None,
    )
    c2.metric("Sharpe Ratio",  f"{metrics['sharpe']:.2f}")
    c3.metric("Max Drawdown",  f"{metrics['max_dd']*100:.1f}%")
    c4.metric("Win Rate",      f"{metrics['win_rate']*100:.1f}%")

    # ── Row 2: Secondary metrics ──────────────────────────────
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Sortino Ratio", f"{metrics['sortino']:.2f}")
    c6.metric("Annual Vol",    f"{metrics['annual_vol']*100:.1f}%")

    if metrics.get('alpha') is not None:
        c7.metric("Alpha",     f"{metrics['alpha']*100:.1f}%")
    if metrics.get('beta') is not None:
        c8.metric("Beta",      f"{metrics['beta']:.2f}")

    st.divider()

    # ── Data quality note ─────────────────────────────────────
    st.markdown(
        f"<div style='color:#64748b; font-size:0.8rem;'>"
        f"ℹ️ Backtest covers {metrics['n_days']} trading days. "
        f"Numbers are inflated due to in-sample overlap on 2-year dataset. "
        f"True out-of-sample performance will be lower. "
        f"Resolve by scaling to 10-year Bhavcopy data.</div>",
        unsafe_allow_html=True
    )


def render_panel4_charts(metrics: dict):
    """Panel 4 — Financial Charts: equity curve, drawdown, rolling Sharpe."""

    st.markdown('<div class="section-header">📈 Financial Charts</div>',
                unsafe_allow_html=True)

    if not metrics or 'ret_df' not in metrics:
        st.warning("Chart data not available.")
        return

    ret_df   = metrics['ret_df']
    drawdown = metrics['drawdown']

    # ── Chart 1: Equity Curve ─────────────────────────────────
    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(
        x=ret_df.index, y=ret_df['Cumulative'],
        name='AI Portfolio', line=dict(color='#22c55e', width=2),
        fill='tozeroy', fillcolor='rgba(34,197,94,0.08)',
    ))

    # Add Nifty benchmark if available
    df_raw = load_features_from_db()
    if 'Nifty_Return' in df_raw.columns:
        nifty_daily = (
            df_raw.groupby('Date')['Nifty_Return']
            .mean()
            .reindex(ret_df.index)
            .fillna(0)
        )
        nifty_cum = (1 + nifty_daily).cumprod()
        fig_eq.add_trace(go.Scatter(
            x=nifty_cum.index, y=nifty_cum.values,
            name='Nifty 50', line=dict(color='#f59e0b', width=1.5, dash='dash'),
        ))

    fig_eq.update_layout(
        title='Portfolio Equity Curve vs Nifty 50',
        xaxis_title='Date', yaxis_title='Portfolio Value (₹1 = start)',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font_color='#e2e8f0', height=350,
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        xaxis=dict(gridcolor='#1e293b'), yaxis=dict(gridcolor='#1e293b'),
    )
    st.plotly_chart(fig_eq, use_container_width=True)

    # ── Chart 2: Drawdown ─────────────────────────────────────
    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(
        x=drawdown.index, y=drawdown.values * 100,
        name='Drawdown %', line=dict(color='#ef4444', width=1.5),
        fill='tozeroy', fillcolor='rgba(239,68,68,0.12)',
    ))
    fig_dd.update_layout(
        title='Portfolio Drawdown',
        xaxis_title='Date', yaxis_title='Drawdown (%)',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font_color='#e2e8f0', height=260,
        xaxis=dict(gridcolor='#1e293b'), yaxis=dict(gridcolor='#1e293b'),
    )
    st.plotly_chart(fig_dd, use_container_width=True)

    # ── Chart 3: Rolling Sharpe (63-day window) ───────────────
    rf_daily = 0.065 / 252
    excess   = ret_df['Return'] - rf_daily
    roll_sharpe = (
        excess.rolling(63).mean() /
        excess.rolling(63).std()
    ) * np.sqrt(252)

    fig_sh = go.Figure()
    fig_sh.add_trace(go.Scatter(
        x=roll_sharpe.index, y=roll_sharpe.values,
        name='Rolling Sharpe (63d)', line=dict(color='#7dd3fc', width=1.5),
    ))
    fig_sh.add_hline(y=1.0, line_dash='dash', line_color='#64748b',
                     annotation_text='Sharpe = 1.0')
    fig_sh.add_hline(y=0.0, line_dash='dot',  line_color='#ef4444',
                     annotation_text='Break-even')
    fig_sh.update_layout(
        title='Rolling Sharpe Ratio (63-day window)',
        xaxis_title='Date', yaxis_title='Sharpe Ratio',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font_color='#e2e8f0', height=260,
        xaxis=dict(gridcolor='#1e293b'), yaxis=dict(gridcolor='#1e293b'),
    )
    st.plotly_chart(fig_sh, use_container_width=True)


def render_panel5_allocation(portfolio: pd.DataFrame, capital_inr: float):
    """Panel 5 — Capital Allocation: exact ₹ amounts and share counts per BUY."""

    st.markdown('<div class="section-header">💰 Capital Allocation</div>',
                unsafe_allow_html=True)

    if portfolio.empty:
        st.info("No BUY signals to allocate capital to.")
        return

    deployed = portfolio['Actual_INR'].sum()
    cash     = capital_inr - deployed

    # ── Summary row ───────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    c1.metric("Capital Entered",    f"₹{capital_inr/1e5:.2f}L")
    c2.metric("Deployed Across Stocks", f"₹{deployed/1e5:.2f}L",
              delta=f"{deployed/capital_inr*100:.1f}% of capital")
    c3.metric("Cash (Undeployed)",  f"₹{cash/1e5:.2f}L",
              delta=f"-{cash/capital_inr*100:.1f}%", delta_color="inverse")

    st.divider()
    st.markdown("**Exact Allocation — How to Deploy Your Capital**")

    # ── Full allocation table ─────────────────────────────────
    alloc_df = portfolio[[
        'Ticker', 'Sector', 'Close', 'Shares', 'Actual_INR', 'Weight', 'ATR_pct'
    ]].copy()

    alloc_df['Ticker']      = alloc_df['Ticker'].str.replace('.NS', '', regex=False)
    alloc_df['CMP (₹)']     = alloc_df['Close'].map('₹{:,.2f}'.format)
    alloc_df['Shares to Buy'] = alloc_df['Shares'].astype(int)
    alloc_df['Amount (₹)']  = alloc_df['Actual_INR'].map('₹{:,.0f}'.format)
    alloc_df['Portfolio %'] = (alloc_df['Weight'] * 100).map('{:.1f}%'.format)
    alloc_df['Norm. ATR %'] = (alloc_df['ATR_pct'] * 100).map('{:.2f}%'.format)

    display_alloc = alloc_df[[
        'Ticker', 'Sector', 'CMP (₹)', 'Shares to Buy', 'Amount (₹)',
        'Portfolio %', 'Norm. ATR %'
    ]].rename(columns={'Norm. ATR %': 'Risk Proxy (ATR%)'})

    st.dataframe(display_alloc, use_container_width=True, hide_index=True)

    st.markdown(
        "<div style='color:#64748b; font-size:0.8rem; margin-top:8px;'>"
        "ℹ️ Allocation uses Risk Parity (normalized ATR). "
        "Higher ATR% = more volatile stock = smaller allocation. "
        "Shares are integer-rounded; residual cash is kept as buffer."
        "</div>",
        unsafe_allow_html=True
    )


# ═══════════════════════════════════════════════════════════════
# SECTION 7 — MAIN APP
# Wires everything together
# ═══════════════════════════════════════════════════════════════

def main():
    # ── Header ────────────────────────────────────────────────
    st.markdown(
        "<h1 style='color:#7dd3fc; margin-bottom:0'>📈 AI Hedge Fund</h1>"
        "<p style='color:#64748b; margin-top:0'>Indian Equity Markets — "
        "Nifty 100 Universe — AI-Driven Portfolio Management</p>",
        unsafe_allow_html=True
    )

    # ── Sidebar (returns capital) ──────────────────────────────
    capital_inr = render_sidebar()

    # ── Load models (cached) ──────────────────────────────────
    with st.spinner("Initialising AI models..."):
        models = load_models(MODEL_VERSION)

    # ── Generate signals (cached, busts when data changes) ────
    df        = load_features_from_db()
    df_hash   = hash(str(df['Date'].max()) + str(len(df)))
    signals   = generate_signals(MODEL_VERSION, df_hash)

    # ── Portfolio optimization ─────────────────────────────────
    portfolio = optimize_portfolio(signals, capital_inr)

    # ── Backtest metrics (cached) ──────────────────────────────
    metrics = compute_backtest_metrics(df_hash)

    # ── Tabs for all 5 panels ─────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Recommendations",
        "💼 Portfolio",
        "📊 Metrics",
        "📈 Charts",
        "💰 Allocation",
    ])

    with tab1:
        render_panel1_recommendations(signals)

    with tab2:
        render_panel2_portfolio(portfolio, signals, capital_inr)

    with tab3:
        render_panel3_metrics(metrics)

    with tab4:
        render_panel4_charts(metrics)

    with tab5:
        render_panel5_allocation(portfolio, capital_inr)


# ── Entry point ───────────────────────────────────────────────
if __name__ == "__main__":
    main()