import sqlite3

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from verify_blockchain import DB_FILE, verify_database


ASSET_ID = "URBAN-001"

st.set_page_config(
    page_title="Smart City Digital Twin",
    page_icon="🏙️",
    layout="wide",
)

st.title("Smart City Digital Twin")
st.caption("Sensor-to-ledger data continuity and verification")

if st.button("Refresh data"):
    st.rerun()

if not DB_FILE.exists():
    st.error(f"Database file not found: {DB_FILE}")
    st.stop()

try:
    with sqlite3.connect(DB_FILE, timeout=10) as db:
        db.execute("PRAGMA busy_timeout = 10000")
        sensor_data = pd.read_sql_query(
            """
            SELECT id, record_id, temperature, time, data_hash
            FROM temperature
            ORDER BY id
            """,
            db,
        )
        block_data = pd.read_sql_query(
            """
            SELECT block_index, db_id, record_id, temperature,
                   record_time, data_hash, previous_hash, block_hash
            FROM blocks
            ORDER BY block_index
            """,
            db,
        )
        verification = verify_database(db)
except sqlite3.Error as error:
    st.error(f"Could not read the database: {error}")
    st.stop()

latest_temperature = None
latest_time = "No reading yet"

if not sensor_data.empty:
    latest_temperature = float(sensor_data.iloc[-1]["temperature"])
    latest_time = str(sensor_data.iloc[-1]["time"])

metric_columns = st.columns(4)
metric_columns[0].metric(
    "Current temperature",
    "--" if latest_temperature is None else f"{latest_temperature:.1f} °C",
)
metric_columns[1].metric("Source records", verification["source_records"])
metric_columns[2].metric("Ledger blocks", verification["total_blocks"])
metric_columns[3].metric("Uniquely referenced", verification["anchored_records"])

st.caption(f"Latest sensor reading: {latest_time}")

st.divider()
st.subheader("Digital Twin Model")

temperature_label = (
    "Waiting for data"
    if latest_temperature is None
    else f"{latest_temperature:.1f} °C"
)

asset_html = f"""
<div style="background:linear-gradient(135deg,#10243a,#183b50);
            border-radius:16px;padding:22px;color:white;
            border:1px solid #31536a;font-family:Arial,sans-serif;">
  <div style="display:flex;justify-content:space-between;align-items:center;
              flex-wrap:wrap;gap:14px;margin-bottom:12px;">
    <div>
      <div style="font-size:12px;color:#9fc4d8;letter-spacing:1.3px;">
        DIGITAL ASSET MODEL
      </div>
      <div style="font-size:23px;font-weight:700;margin-top:5px;">
        Urban Infrastructure · {ASSET_ID}
      </div>
      <div style="font-size:13px;color:#c6dce7;margin-top:4px;">
        Generic urban district and infrastructure representation
      </div>
    </div>
    <div style="background:#164e63;padding:12px 16px;border-radius:12px;min-width:150px;">
      <div style="font-size:11px;color:#bae6fd;">LATEST SENSOR VALUE</div>
      <div style="font-size:26px;font-weight:700;margin-top:3px;">
        {temperature_label}
      </div>
      <div style="font-size:11px;color:#c6dce7;">DHT11 · Temperature</div>
    </div>
  </div>
  <svg viewBox="0 0 900 300" width="100%" role="img"
       aria-label="Conceptual smart city infrastructure model">
    <defs>
      <linearGradient id="building" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0%" stop-color="#b9d7e6"/>
        <stop offset="100%" stop-color="#6f91a5"/>
      </linearGradient>
      <linearGradient id="ground" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0%" stop-color="#24485b"/>
        <stop offset="100%" stop-color="#193849"/>
      </linearGradient>
    </defs>
    <rect x="24" y="226" width="852" height="48" rx="8" fill="url(#ground)"/>
    <rect x="50" y="213" width="800" height="8" rx="4" fill="#53778b"/>
    <g fill="url(#building)">
      <rect x="82" y="104" width="118" height="109" rx="5"/>
      <rect x="225" y="70" width="145" height="143" rx="5"/>
      <rect x="396" y="119" width="112" height="94" rx="5"/>
      <rect x="535" y="88" width="130" height="125" rx="5"/>
      <rect x="690" y="130" width="112" height="83" rx="5"/>
    </g>
    <g fill="#24485b" opacity="0.82">
      <path d="M98 121h18v17H98z M132 121h18v17h-18z M166 121h18v17h-18z
               M98 154h18v17H98z M132 154h18v17h-18z M166 154h18v17h-18z"/>
      <path d="M245 91h20v18h-20z M282 91h20v18h-20z M319 91h20v18h-20z
               M245 125h20v18h-20z M282 125h20v18h-20z M319 125h20v18h-20z
               M245 159h20v18h-20z M282 159h20v18h-20z M319 159h20v18h-20z"/>
      <path d="M412 137h18v16h-18z M446 137h18v16h-18z M480 137h18v16h-18z
               M412 169h18v16h-18z M446 169h18v16h-18z M480 169h18v16h-18z"/>
      <path d="M553 107h18v17h-18z M588 107h18v17h-18z M623 107h18v17h-18z
               M553 141h18v17h-18z M588 141h18v17h-18z M623 141h18v17h-18z
               M553 175h18v17h-18z M588 175h18v17h-18z M623 175h18v17h-18z"/>
      <path d="M706 146h18v16h-18z M741 146h18v16h-18z M776 146h18v16h-18z
               M706 178h18v16h-18z M741 178h18v16h-18z M776 178h18v16h-18z"/>
    </g>
    <rect x="24" y="238" width="852" height="22" rx="4" fill="#304f60"/>
    <path d="M50 249 H850" stroke="#dbe8ee" stroke-width="2"
          stroke-dasharray="24 18" opacity="0.85"/>
    <path d="M110 285 H790" stroke="#38bdf8" stroke-width="3"
          stroke-linecap="round" opacity="0.9"/>
    <path d="M285 285 V272 M450 285 V272 M615 285 V272"
          stroke="#38bdf8" stroke-width="2"/>
    <circle cx="285" cy="285" r="6" fill="#67e8f9"/>
    <circle cx="450" cy="285" r="6" fill="#67e8f9"/>
    <circle cx="615" cy="285" r="6" fill="#67e8f9"/>
    <circle cx="450" cy="35" r="12" fill="#fbbf24" stroke="#fff7cc" stroke-width="3"/>
    <path d="M450 49 V61" stroke="#fbbf24" stroke-width="2"/>
    <rect x="365" y="61" width="170" height="27" rx="7" fill="#0f766e"/>
    <text x="450" y="79" text-anchor="middle" fill="white" font-size="12">
      Room sensor data input
    </text>
  </svg>
  <div style="display:flex;gap:18px;flex-wrap:wrap;font-size:13px;color:#d5e7ef;margin-top:8px;">
    <span>Asset ID: {ASSET_ID}</span>
    <span>Device: NodeMCU ESP8266</span>
    <span>Sensor: DHT11</span>
    <span>Variable: Temperature</span>
  </div>
  <div style="font-size:12px;color:#a9c4d2;margin-top:12px;">
    Conceptual urban district model — not a surveyed or instrumented city asset.
  </div>
</div>
"""

components.html(asset_html, height=420, scrolling=False)
st.info(
    "The DHT11 measures room-environment temperature. The reading is mapped "
    "to a generic urban demonstration asset and is not a municipal measurement."
)

st.divider()
st.subheader("Blockchain Verification")

integrity = verification["integrity"]
coverage = verification["coverage"]

if integrity == "VALID" and coverage == "COMPLETE":
    st.success("Ledger integrity is valid and source-record coverage is complete.")
elif integrity == "VALID":
    st.warning(
        "The existing ledger is valid, but the source-record set is not fully covered."
    )
else:
    st.error("One or more ledger or source-record integrity checks failed.")

status_columns = st.columns(4)
status_columns[0].metric("Integrity", integrity)
status_columns[1].metric("Coverage", coverage)
status_columns[2].metric("Uniquely referenced", verification["anchored_records"])
status_columns[3].metric("Pending", verification["pending_records"])

if verification["problems"]:
    with st.expander("Verification diagnostics"):
        for problem in verification["problems"]:
            st.write(problem)

st.divider()
st.subheader("Temperature History")

if sensor_data.empty:
    st.info("No sensor readings are available.")
else:
    chart_data = sensor_data.set_index("id")[["temperature"]]
    chart_data = chart_data.rename(columns={"temperature": "Temperature (°C)"})
    st.line_chart(chart_data, height=300)

st.divider()
st.subheader("Sensor Records")

if sensor_data.empty:
    st.info("No sensor records are available.")
else:
    display_sensor_data = sensor_data.sort_values("id", ascending=False).rename(
        columns={
            "id": "Database ID",
            "record_id": "Sensor Record",
            "temperature": "Temperature (°C)",
            "time": "Received At",
            "data_hash": "SHA-256 Data Hash",
        }
    )
    st.dataframe(
        display_sensor_data,
        use_container_width=True,
        hide_index=True,
    )

st.divider()
st.subheader("Blockchain Blocks")

if block_data.empty:
    st.info("No ledger blocks are available.")
else:
    display_blocks = block_data.sort_values(
        "block_index", ascending=False
    ).rename(
        columns={
            "block_index": "Block",
            "db_id": "Source Database ID",
            "record_id": "Sensor Record",
            "temperature": "Temperature (°C)",
            "record_time": "Recorded At",
            "data_hash": "Sensor Data Hash",
            "previous_hash": "Previous Hash",
            "block_hash": "Block Hash",
        }
    )
    st.dataframe(
        display_blocks,
        use_container_width=True,
        hide_index=True,
    )
