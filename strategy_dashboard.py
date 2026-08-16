import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import datetime, timezone


# ============================================================
# SETTINGS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

STARTING_CAPITAL = 10000.0

V1_FILE = BASE_DIR / "bull_low_vol_paper_log.csv"
V2_FILE = BASE_DIR / "v2_live_paper_history.csv"
V3_FILE = BASE_DIR / "v3_live_paper_history.csv"

V3_TRADES_FILE = BASE_DIR / "v3_live_trades.csv"


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="Crypto Strategy Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# SIMPLE MOBILE-FRIENDLY CSS
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    h1 {
        margin-bottom: 0.1rem;
    }

    div[data-testid="stMetric"] {
        border: 1px solid rgba(120,120,120,0.20);
        padding: 16px;
        border-radius: 12px;
    }

    div[data-testid="stMetricValue"] {
        font-size: 2rem;
    }

    @media (max-width: 768px) {

        .block-container {
            padding-left: 0.8rem;
            padding-right: 0.8rem;
            padding-top: 1rem;
        }

        div[data-testid="stMetricValue"] {
            font-size: 1.5rem;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================

def read_csv_safe(path):

    if not path.exists():
        return pd.DataFrame()

    try:
        return pd.read_csv(path)

    except Exception:
        return pd.DataFrame()


def parse_timestamp(value):

    return pd.to_datetime(
        value,
        utc=True,
        format="mixed",
        errors="coerce",
    )


def numeric(series):

    return pd.to_numeric(
        series,
        errors="coerce",
    )


def money(value):

    if value is None or pd.isna(value):
        return "—"

    return f"${value:,.2f}"


def pct(value):

    if value is None or pd.isna(value):
        return "—"

    return f"{value:.2%}"


def short_time(value):

    value = parse_timestamp(value)

    if pd.isna(value):
        return "Unknown"

    return value.strftime(
        "%b %d, %Y %H:%M UTC"
    )


def find_equity(
    df,
    starting_capital=10000.0,
):

    if len(df) == 0:
        return None


    # --------------------------------------------------------
    # First try actual equity / capital columns
    # --------------------------------------------------------

    candidates = [
        "equity",
        "paper_equity",
        "portfolio_equity",
        "portfolio_value",
        "capital",
        "ending_capital",
    ]


    for col in candidates:

        if col in df.columns:

            values = numeric(
                df[col]
            ).dropna()

            if len(values):

                return float(
                    values.iloc[-1]
                )


    # --------------------------------------------------------
    # Fallback for V1:
    # reconstruct from recorded P&L / fees if possible.
    # --------------------------------------------------------

    reconstruction_cols = [
        "price_pnl",
        "funding_pnl",
        "fees",
    ]


    if any(
        col in df.columns
        for col in reconstruction_cols
    ):

        pnl = 0.0


        if "price_pnl" in df.columns:

            pnl += numeric(
                df["price_pnl"]
            ).fillna(0).sum()


        if "funding_pnl" in df.columns:

            pnl += numeric(
                df["funding_pnl"]
            ).fillna(0).sum()


        if "fees" in df.columns:

            pnl -= numeric(
                df["fees"]
            ).fillna(0).sum()


        return (
            starting_capital
            + pnl
        )


    return None


def strategy_return(equity):

    if equity is None:
        return None

    return (
        equity
        / STARTING_CAPITAL
        - 1
    )


def max_drawdown_from_equity(df):

    if (
        len(df) == 0
        or "equity" not in df.columns
    ):
        return None


    curve = numeric(
        df["equity"]
    ).dropna()


    if len(curve) < 2:
        return 0.0


    peak = (
        curve.cummax()
    )


    drawdown = (
        curve
        / peak
        - 1
    )


    return float(
        drawdown.min()
    )


def latest_timestamp(df):

    if (
        len(df) == 0
        or "timestamp" not in df.columns
    ):
        return None


    values = (
        df["timestamp"]
        .map(parse_timestamp)
        .dropna()
    )


    if len(values) == 0:
        return None


    return values.iloc[-1]


def status_icon(status):

    text = str(
        status
    ).upper()


    if (
        "LONG" in text
        or "BULL" in text
        or "ACTIVE" in text
    ):
        return "🟢"


    if (
        "SHORT" in text
        or "BEAR" in text
    ):
        return "🔴"


    return "⚪"


# ============================================================
# LOAD
# ============================================================

v1 = read_csv_safe(
    V1_FILE
)

v2 = read_csv_safe(
    V2_FILE
)

v3 = read_csv_safe(
    V3_FILE
)

v3_trades = read_csv_safe(
    V3_TRADES_FILE
)


# ============================================================
# SORT CHRONOLOGICALLY
# ============================================================

for frame in [
    v1,
    v2,
    v3,
]:

    if (
        len(frame)
        and "timestamp" in frame.columns
    ):

        frame["timestamp"] = pd.to_datetime(
            frame["timestamp"],
            utc=True,
            format="mixed",
            errors="coerce",
        )

        frame.sort_values(
            "timestamp",
            inplace=True,
        )


# ============================================================
# V1 SUMMARY
# ============================================================

v1_equity = find_equity(
    v1
)

v1_return = strategy_return(
    v1_equity
)

v1_time = latest_timestamp(
    v1
)

v1_status = "UNKNOWN"
v1_exposure = None


if len(v1):

    latest = v1.iloc[-1]


    if "regime" in v1.columns:

        regime = str(
            latest["regime"]
        )


        if regime in [
            "BULL_LOW_VOL",
            "BULL",
        ]:

            v1_status = "LONG"

        else:

            v1_status = "RISK OFF"


    elif "position" in v1.columns:

        v1_status = str(
            latest["position"]
        )


    if "exposure" in v1.columns:

        v1_exposure = abs(
            float(
                pd.to_numeric(
                    latest["exposure"],
                    errors="coerce",
                )
            )
        )


    elif "position" in v1.columns:

        position_value = pd.to_numeric(
            latest["position"],
            errors="coerce",
        )


        if pd.notna(
            position_value
        ):

            v1_exposure = abs(
                float(
                    position_value
                )
            )


# ============================================================
# V2 SUMMARY
# ============================================================

v2_equity = find_equity(
    v2
)

v2_return = strategy_return(
    v2_equity
)

v2_time = latest_timestamp(
    v2
)

v2_status = "UNKNOWN"
v2_exposure = None


if len(v2):

    latest = v2.iloc[-1]


    if "direction" in v2.columns:

        v2_status = str(
            latest["direction"]
        )


    if "current_weight" in v2.columns:

        value = pd.to_numeric(
            latest["current_weight"],
            errors="coerce",
        )


        if pd.notna(value):

            v2_exposure = abs(
                float(value)
            )


# ============================================================
# V3 SUMMARY
# ============================================================

v3_equity = find_equity(
    v3
)

v3_return = strategy_return(
    v3_equity
)

v3_time = latest_timestamp(
    v3
)

v3_status = "WAITING"
v3_exposure = None


if len(v3):

    latest = v3.iloc[-1]


    if "gross_exposure" in v3.columns:

        value = pd.to_numeric(
            latest["gross_exposure"],
            errors="coerce",
        )


        if pd.notna(value):

            v3_exposure = float(
                value
            )


    if "active_positions" in v3.columns:

        active = pd.to_numeric(
            latest["active_positions"],
            errors="coerce",
        )


        if (
            pd.notna(active)
            and active > 0
        ):

            v3_status = (
                f"{int(active)} ACTIVE"
            )


# ============================================================
# HEADER
# ============================================================

left, right = st.columns(
    [4, 1]
)


with left:

    st.title(
        "📈 Crypto Strategy Dashboard"
    )

    st.caption(
        "Forward paper trading • V1 / V2 / V3"
    )


with right:

    if st.button(
        "↻ Refresh",
        use_container_width=True,
    ):

        st.rerun()


# ============================================================
# LAST UPDATED
# ============================================================

all_times = [
    t
    for t in [
        v1_time,
        v2_time,
        v3_time,
    ]
    if t is not None
    and pd.notna(t)
]


if all_times:

    latest_data_time = max(
        all_times
    )


    st.caption(
        "Latest strategy data: "
        + short_time(
            latest_data_time
        )
    )


# ============================================================
# STRATEGY CARDS
# ============================================================

st.divider()


c1, c2, c3 = st.columns(
    3
)


def strategy_card(
    container,
    name,
    subtitle,
    equity,
    ret,
    status,
    exposure,
    timestamp,
):

    with container:

        st.subheader(
            name
        )

        st.caption(
            subtitle
        )

        st.metric(
            "Paper Equity",
            money(
                equity
            ),
            pct(
                ret
            ),
        )


        st.write(
            f"{status_icon(status)} "
            f"**{status}**"
        )


        if exposure is not None:

            st.write(
                f"Exposure: "
                f"**{pct(exposure)}**"
            )

        else:

            st.write(
                "Exposure: **—**"
            )


        st.caption(
            short_time(
                timestamp
            )
        )


strategy_card(
    c1,
    "V1 — Regime",
    "When should we participate?",
    v1_equity,
    v1_return,
    v1_status,
    v1_exposure,
    v1_time,
)


strategy_card(
    c2,
    "V2 — Volatility Scaled",
    "Direction + how much risk?",
    v2_equity,
    v2_return,
    v2_status,
    v2_exposure,
    v2_time,
)


strategy_card(
    c3,
    "V3 — Short Squeeze",
    "Has a rare event occurred?",
    v3_equity,
    v3_return,
    v3_status,
    v3_exposure,
    v3_time,
)


# ============================================================
# COMBINED PORTFOLIO
# ============================================================

valid_equities = [
    x
    for x in [
        v1_equity,
        v2_equity,
        v3_equity,
    ]
    if x is not None
]


combined_equity = (
    sum(valid_equities)
    if valid_equities
    else None
)


combined_start = (
    STARTING_CAPITAL
    * len(
        valid_equities
    )
)


combined_return = (
    combined_equity
    / combined_start
    - 1
    if (
        combined_equity is not None
        and combined_start > 0
    )
    else None
)


st.divider()

st.header(
    "Combined Paper Portfolio"
)


a, b, c, d = st.columns(
    4
)


a.metric(
    "Total Equity",
    money(
        combined_equity
    ),
)


b.metric(
    "Combined Return",
    pct(
        combined_return
    ),
)


active_count = sum(
    [
        int(
            v1_exposure is not None
            and v1_exposure > 0
        ),
        int(
            v2_exposure is not None
            and v2_exposure > 0
        ),
        int(
            v3_exposure is not None
            and v3_exposure > 0
        ),
    ]
)


c.metric(
    "Strategies Active",
    f"{active_count}/3",
)


average_exposure = (
    sum(
        [
            v1_exposure or 0,
            v2_exposure or 0,
            v3_exposure or 0,
        ]
    )
    / 3
)


d.metric(
    "Avg Strategy Exposure",
    pct(
        average_exposure
    ),
)


# ============================================================
# EQUITY CURVES
# ============================================================

st.divider()

st.header(
    "Forward Equity"
)


equity_frames = []


def add_equity_frame(
    frame,
    strategy,
):

    if (
        len(frame) == 0
        or "timestamp" not in frame.columns
        or "equity" not in frame.columns
    ):
        return


    temp = frame[
        [
            "timestamp",
            "equity",
        ]
    ].copy()


    temp["equity"] = numeric(
        temp["equity"]
    )


    temp["strategy"] = (
        strategy
    )


    equity_frames.append(
        temp
    )


add_equity_frame(
    v1,
    "V1"
)

add_equity_frame(
    v2,
    "V2"
)

add_equity_frame(
    v3,
    "V3"
)


if equity_frames:

    equity_df = pd.concat(
        equity_frames,
        ignore_index=True,
    )


    equity_df = (
        equity_df
        .dropna(
            subset=[
                "timestamp",
                "equity",
            ]
        )
    )


    pivot = (
        equity_df
        .pivot_table(
            index="timestamp",
            columns="strategy",
            values="equity",
            aggfunc="last",
        )
        .sort_index()
    )


    st.line_chart(
        pivot,
        height=400,
    )


else:

    st.info(
        "Equity curves will appear once "
        "forward equity history accumulates."
    )


# ============================================================
# RISK / HEALTH
# ============================================================

st.divider()

st.header(
    "Risk & Health"
)


r1, r2, r3 = st.columns(
    3
)


r1.metric(
    "V1 Forward Drawdown",
    pct(
        max_drawdown_from_equity(
            v1
        )
    ),
)


r2.metric(
    "V2 Forward Drawdown",
    pct(
        max_drawdown_from_equity(
            v2
        )
    ),
)


r3.metric(
    "V3 Forward Drawdown",
    pct(
        max_drawdown_from_equity(
            v3
        )
    ),
)


# ============================================================
# RECENT ACTIVITY
# ============================================================

st.divider()

st.header(
    "Recent Activity"
)


tab1, tab2, tab3 = st.tabs(
    [
        "V1",
        "V2",
        "V3",
    ]
)


with tab1:

    if len(v1):

        st.dataframe(
            v1.tail(10),
            width="stretch",
            hide_index=True,
        )

    else:

        st.info(
            "No V1 history found."
        )


with tab2:

    if len(v2):

        st.dataframe(
            v2.tail(10),
            width="stretch",
            hide_index=True,
        )

    else:

        st.info(
            "No V2 history found."
        )


with tab3:

    if len(v3):

        st.dataframe(
            v3.tail(10),
            width="stretch",
            hide_index=True,
        )


    if len(v3_trades):

        st.subheader(
            "Recent V3 Trades"
        )

        st.dataframe(
            v3_trades.tail(10),
            width="stretch",
            hide_index=True,
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Paper trading only • "
    "Strategies frozen for forward validation • "
    f"Dashboard viewed {datetime.now(timezone.utc).strftime('%b %d, %Y %H:%M UTC')}"
)