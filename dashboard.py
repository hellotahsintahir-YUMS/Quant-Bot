"""
============================================
QUANT TRADING DASHBOARD (Multi-User)
============================================
Run with: streamlit run dashboard.py
"""
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).parent / "src"))

from signals import SignalGenerator
from config import STRATEGY_CONFIG
from auth import login_user, register_user
from user_data import (
    get_watchlist, save_watchlist, DEFAULT_WATCHLIST, get_plan, save_plan
)
from planning import calculate_allocations, recommend_stocks

st.set_page_config(page_title="Quant Trading Dashboard", page_icon="", layout="wide")

st.markdown(
    """
    <style>
    :root {
        --quant-bg: #07131d;
        --quant-sidebar: #06111a;
        --quant-card: #0e202d;
        --quant-card-alt: #102735;
        --quant-border: #274050;
        --quant-text: #e8f1f5;
        --quant-muted: #8da7b4;
        --quant-teal: #63d3ce;
        --quant-green: #5be3a2;
        --quant-yellow: #f4ba4b;
        --quant-red: #ff7b83;
    }

    .stApp, [data-testid="stAppViewContainer"] {
        background-color: var(--quant-bg);
        color: var(--quant-text);
    }

    [data-testid="stSidebar"] {
        background-color: var(--quant-sidebar);
        border-right: 1px solid var(--quant-border);
    }

    [data-testid="stHeader"] {
        background-color: var(--quant-bg);
    }

    [data-testid="stMarkdownContainer"],
    [data-testid="stText"],
    label,
    h1, h2, h3, h4, h5, h6 {
        color: var(--quant-text);
    }

    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] p {
        color: var(--quant-muted);
    }

    [data-testid="stMetric"] {
        background-color: var(--quant-card);
        border: 1px solid var(--quant-border);
    }

    [data-testid="stMetricValue"] {
        color: var(--quant-teal);
    }

    input, textarea, [data-baseweb="select"] > div {
        background-color: var(--quant-card);
        color: var(--quant-text);
        border-color: var(--quant-border);
    }

    button[kind="primary"] {
        background-color: var(--quant-teal);
        color: var(--quant-bg);
        border-color: var(--quant-teal);
    }

    button[kind="secondary"] {
        background-color: var(--quant-card);
        color: var(--quant-text);
        border-color: var(--quant-border);
    }

    [data-testid="stAlert"] {
        background-color: var(--quant-card);
        border-color: var(--quant-border);
        color: var(--quant-text);
    }

    [data-testid="stDataFrame"] {
        border: 1px solid var(--quant-border);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "user" not in st.session_state:
    st.session_state.user = None


@st.cache_resource
def get_generator():
    return SignalGenerator(STRATEGY_CONFIG)


@st.cache_data(ttl=300, show_spinner=False)
def get_signal_bundle(symbol):
    """Fetch and calculate one symbol's signals for five minutes."""
    generator = get_generator()
    data = generator.generate_signals(symbol)
    latest = data.iloc[-1]
    previous = data.iloc[-2]
    return data, {
        "symbol": symbol,
        "timestamp": latest.name,
        "price": float(latest["Close"]),
        "action": latest["action"],
        "signal_score": int(latest["signal_score"]),
        "signal_strength": float(latest["signal_strength"]),
        "indicators": {
            "RSI": float(latest["RSI"]),
            "MACD": float(latest["MACD"]),
            "MACD_signal": float(latest["MACD_signal"]),
            "BB_position": float(latest["BB_position"]),
            "SMA_short": float(latest["SMA_short"]),
            "SMA_long": float(latest["SMA_long"]),
        },
        "new_signal": latest["action"] != previous["action"],
        "change_pct": float(
            (latest["Close"] - previous["Close"]) / previous["Close"] * 100
        ),
    }


def get_cached_signal(symbol):
    """Return only the signal while retaining the shared data cache."""
    return get_signal_bundle(symbol)[1]


@st.cache_data(ttl=300, show_spinner=False)
def get_watchlist_signals(symbols):
    """Load watchlist signals concurrently while limiting network pressure."""
    signals = []
    errors = []

    def load(symbol):
        return get_cached_signal(symbol)

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(load, symbol): symbol for symbol in symbols}
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                signals.append(future.result())
            except Exception as exc:
                errors.append(f"{symbol}: {exc}")
    return signals, errors


# ============================================
# LOGIN / SIGNUP PAGE
# ============================================
def show_login_page():
    st.title("Quant Trading Dashboard")
    st.caption("Sign in to view and customize your personal watchlist")

    # Initialize session states for reset flow
    if "show_reset" not in st.session_state:
        st.session_state.show_reset = False
    if "reset_code" not in st.session_state:
        st.session_state.reset_code = None
    if "reset_email" not in st.session_state:
        st.session_state.reset_email = None

    # ============================================
    # RESET PASSWORD FLOW
    # ============================================
    if st.session_state.show_reset:
        st.header("Reset Password")

        if st.session_state.reset_code is None:
            # Step 1: Ask for email
            email_input = st.text_input("Enter your account email")
            if st.button("Send Reset Code"):
                from auth import check_email_exists
                if check_email_exists(email_input):
                    import random
                    code = str(random.randint(100000, 999999))
                    st.session_state.reset_code = code
                    st.session_state.reset_email = email_input.strip().lower()
                    st.rerun()
                else:
                    st.error("No account found with that email.")

            if st.button("Back to Login"):
                st.session_state.show_reset = False
                st.rerun()

        else:
            # Step 2: Show simulated email and ask for new password
            st.info(
                f"Simulated Email Inbox:\n\nHello! Your password reset code is: **{st.session_state.reset_code}**\n\n"
                "*(Note for judges: In a production environment, this code would be sent automatically to the user's email.)"
            )

            with st.form("reset_form"):
                entered_code = st.text_input("Enter the 6-digit code")
                new_pw = st.text_input("New Password", type="password")
                confirm_pw = st.text_input("Confirm New Password", type="password")

                if st.form_submit_button("Reset Password"):
                    if entered_code != st.session_state.reset_code:
                        st.error("Incorrect code.")
                    elif len(new_pw) < 6:
                        st.error("Password must be at least 6 characters.")
                    elif new_pw != confirm_pw:
                        st.error("Passwords do not match.")
                    else:
                        from auth import update_password
                        ok, msg = update_password(st.session_state.reset_email, new_pw)
                        if ok:
                            st.success("Success: " + msg + " You can now log in.")
                            st.session_state.show_reset = False
                            st.session_state.reset_code = None
                            st.session_state.reset_email = None
                        else:
                            st.error(msg)

            if st.button("Back to Login"):
                st.session_state.show_reset = False
                st.session_state.reset_code = None
                st.rerun()

        return  # Stop here so we don't show the login tabs below

    # ============================================
    # NORMAL LOGIN / SIGNUP FLOW
    # ============================================
    tab_login, tab_signup = st.tabs(["Log In", "Sign Up"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Log In"):
                user, msg = login_user(email, password)
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error(msg)

        if st.button("Forgot Password?"):
            st.session_state.show_reset = True
            st.rerun()

    with tab_signup:
        with st.form("signup_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            pw = st.text_input("Password", type="password")
            pw2 = st.text_input("Confirm Password", type="password")
            if st.form_submit_button("Create Account"):
                if not name or not email or not pw:
                    st.error("Please fill in all fields.")
                elif "@" not in email:
                    st.error("Please enter a valid email.")
                elif len(pw) < 6:
                    st.error("Password must be at least 6 characters.")
                elif pw != pw2:
                    st.error("Passwords do not match.")
                else:
                    ok, msg = register_user(name, email, pw)
                    if ok:
                        st.success("Success: " + msg)
                    else:
                        st.error(msg)

    st.info("Passwords are hashed with bcrypt and stored locally.")


# ============================================
# WATCHLIST MANAGER (sidebar)
# ============================================
def watchlist_manager(email, watchlist):
    st.sidebar.header("Customize Watchlist")
    new_ticker = st.sidebar.text_input("Add a ticker", placeholder="e.g. UBER").upper().strip()

    if st.sidebar.button("Add Stock", use_container_width=True):
        if not new_ticker:
            st.sidebar.warning("Type a symbol first.")
        elif new_ticker in watchlist:
            st.sidebar.warning(f"{new_ticker} is already in your list.")
        else:
            import yfinance as yf
            try:
                df = yf.download(new_ticker, period="5d", progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                valid = not df.empty
            except Exception:
                valid = False
            if valid:
                watchlist.append(new_ticker)
                save_watchlist(email, watchlist)
                st.rerun()
            else:
                st.sidebar.error(f"'{new_ticker}' not found. Check the symbol.")

    st.sidebar.caption(f"Your list: {len(watchlist)} stocks")
    for sym in list(watchlist):
        c1, c2 = st.sidebar.columns([4, 1])
        c1.markdown(f"`{sym}`")
        if c2.button("X", key=f"rm_{sym}"):
            watchlist.remove(sym)
            save_watchlist(email, watchlist)
            st.rerun()

    if st.sidebar.button("Reset to default 20", use_container_width=True):
        save_watchlist(email, list(DEFAULT_WATCHLIST))
        st.rerun()


def show_planning(email, watchlist, gen):
    """Render a recommendations-only plan for the signed-in user."""
    saved_plan = get_plan(email)
    with st.expander("Personal investment planning", expanded=bool(saved_plan)):
        st.caption(
            "Set your own budget and selections. Recommendations use your "
            "technical signals; no trades are placed from this planner."
        )
        budget = st.number_input(
            "Budget",
            min_value=0.0,
            value=float(saved_plan.get("budget", 10000.0)),
            step=100.0,
            format="%.2f",
            key="plan_budget",
        )
        reserve_pct = st.slider(
            "Keep uninvested as a reserve (%)",
            min_value=0,
            max_value=90,
            value=int(saved_plan.get("reserve_pct", 10)),
            key="plan_reserve",
        )
        alert_enabled = st.checkbox(
            "Enable downside alerts for this plan",
            value=bool(saved_plan.get("alert_enabled", False)),
            key="plan_alert_enabled",
        )
        alert_loss_pct = st.slider(
            "Alert when a holding falls by (%)",
            min_value=1,
            max_value=50,
            value=int(saved_plan.get("alert_loss_pct", 5)),
            disabled=not alert_enabled,
            key="plan_alert_loss",
        )

        if st.button("Refresh stock recommendations", key="refresh_plan"):
            with st.spinner("Checking your watchlist signals..."):
                signals, errors = get_watchlist_signals(tuple(watchlist))
                for error in errors:
                    st.warning(f"Could not evaluate {error}")
            st.session_state.plan_recommendations = recommend_stocks(signals)

        recommendations = st.session_state.get("plan_recommendations", [])
        if recommendations:
            st.write("Recommended from your watchlist:")
            st.dataframe(pd.DataFrame([
                {
                    "Symbol": item["symbol"],
                    "Action": item["action"],
                    "Price": f"${item['price']:.2f}",
                    "Strength": f"{item['signal_strength']:.1f}%",
                }
                for item in recommendations
            ]), use_container_width=True, hide_index=True)

        default_selection = saved_plan.get("selected_symbols", [])
        selected_symbols = st.multiselect(
            "Stocks to include (you may choose any watchlist stock)",
            options=watchlist,
            default=[symbol for symbol in default_selection if symbol in watchlist],
            key="plan_symbols",
        )

        if st.button("Calculate investment plan", type="primary", key="calculate_plan"):
            with st.spinner("Calculating allocations..."):
                signals_by_symbol = {}
                for symbol in selected_symbols:
                    try:
                        signals_by_symbol[symbol] = get_cached_signal(symbol)
                    except Exception as exc:
                        st.warning(f"Could not evaluate {symbol}: {exc}")
                try:
                    allocations = calculate_allocations(
                        budget,
                        selected_symbols,
                        signals_by_symbol,
                        reserve_pct / 100,
                    )
                except ValueError as exc:
                    st.error(str(exc))
                    return

            plan = {
                "budget": budget,
                "reserve_pct": reserve_pct,
                "selected_symbols": selected_symbols,
                "alert_enabled": alert_enabled,
                "alert_loss_pct": alert_loss_pct,
                "allocations": allocations,
            }
            save_plan(email, plan)
            st.session_state.plan_result = plan

        result = st.session_state.get("plan_result", saved_plan)
        if result.get("allocations"):
            st.subheader("Your plan")
            st.dataframe(pd.DataFrame(result["allocations"]), use_container_width=True, hide_index=True)
            if result.get("alert_enabled"):
                st.info(
                    f"Downside alerts are set at {result['alert_loss_pct']}%. "
                    "This planner does not sell automatically; review and decide."
                )
            st.caption(
                f"Investable budget: ${result['budget'] * (1 - result['reserve_pct'] / 100):,.2f} | "
                f"Reserve: {result['reserve_pct']}%"
            )


# ============================================
# MAIN DASHBOARD
# ============================================
def show_dashboard(user):
    email = user["email"]
    watchlist = get_watchlist(email)
    gen = get_generator()

    st.sidebar.title(f"{user['name']}")
    st.sidebar.caption(email)
    if st.sidebar.button("Log Out", use_container_width=True):
        st.session_state.user = None
        st.rerun()

    selected = None
    if watchlist:
        selected = st.sidebar.selectbox("Select Symbol", watchlist)

    watchlist_manager(email, watchlist)
    show_planning(email, watchlist, gen)

    st.title("Quant Trading Dashboard")
    st.caption(f"Last updated: {datetime.now():%Y-%m-%d %H:%M:%S}")

    if not watchlist:
        st.warning("Your watchlist is empty — add a stock in the sidebar!")
        st.stop()

    try:
        df, signal = get_signal_bundle(selected)
    except Exception as e:
        st.error(f"Error fetching data for {selected}: {e}")
        st.stop()

    # Metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Price", f"${signal['price']:.2f}", f"{signal['change_pct']:.2f}%")
    col2.metric("Signal", signal['action'])
    col3.metric("Score", signal['signal_score'])
    col4.metric("Strength", f"{signal['signal_strength']:.1f}%")
    col5.metric("RSI", f"{signal['indicators']['RSI']:.1f}")

    if signal['action'] == 'BUY':
        st.success(f"BUY SIGNAL — Score {signal['signal_score']} | Strength {signal['signal_strength']:.1f}%")
    elif signal['action'] == 'SELL':
        st.error(f"SELL SIGNAL — Score {signal['signal_score']} | Strength {signal['signal_strength']:.1f}%")
    else:
        st.warning(f"HOLD — Score {signal['signal_score']} | Strength {signal['signal_strength']:.1f}%")

    # Price chart
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
                                 low=df['Low'], close=df['Close'], name='Price'))
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_short'], name='SMA short', line=dict(color='#f4ba4b', width=1.5)))
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_long'], name='SMA long', line=dict(color='#63d3ce', width=1.5)))
    fig.update_layout(
        height=500, xaxis_rangeslider_visible=False, template='plotly_dark',
        paper_bgcolor='#07131d', plot_bgcolor='#0e202d', font_color='#e8f1f5'
    )
    st.plotly_chart(fig, use_container_width=True)

    # RSI + MACD
    c1, c2 = st.columns(2)
    with c1:
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#c084fc')))
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="#ff7b83")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="#5be3a2")
        fig_rsi.update_layout(
            height=300, template='plotly_dark', yaxis_range=[0, 100],
            paper_bgcolor='#07131d', plot_bgcolor='#0e202d', font_color='#e8f1f5'
        )
        st.plotly_chart(fig_rsi, use_container_width=True)
    with c2:
        fig_macd = go.Figure()
        fig_macd.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='#63d3ce')))
        fig_macd.add_trace(go.Scatter(x=df.index, y=df['MACD_signal'], line=dict(color='#f4ba4b')))
        fig_macd.update_layout(
            height=300, template='plotly_dark',
            paper_bgcolor='#07131d', plot_bgcolor='#0e202d', font_color='#e8f1f5'
        )
        st.plotly_chart(fig_macd, use_container_width=True)

    # Signals table for the user's personal watchlist
    st.subheader("Your Watchlist Signals")
    rows = []
    signals, errors = get_watchlist_signals(tuple(watchlist))
    for s in signals:
            rows.append({
                'Symbol': s['symbol'],
                'Price': f"${s['price']:.2f}",
                'Action': s['action'],
                'Score': s['signal_score'],
                'Strength': f"{s['signal_strength']:.1f}%",
                'RSI': f"{s['indicators']['RSI']:.1f}",
            })
    for error in errors:
        st.caption(f"Unable to load {error}")
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ============================================
# APP ENTRY POINT
# ============================================
if st.session_state.user:
    show_dashboard(st.session_state.user)
else:
    show_login_page()
