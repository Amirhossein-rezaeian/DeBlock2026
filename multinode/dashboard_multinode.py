import pandas as pd
import streamlit as st

from network.ledger_network import (
    DEFAULT_SOURCE,
    NODE_NAMES,
    append_pending,
    initialize_nodes,
    status,
    sync_node_from_source,
)


st.set_page_config(
    page_title="Smart City Digital Twin | Multi-node PoC",
    page_icon="🏙️",
    layout="wide",
)

st.title("Smart City Digital Twin")
st.caption("Three-replica hash-chain ledger with local majority voting")

source_path = st.sidebar.text_input(
    "Source SQLite database",
    str(DEFAULT_SOURCE),
)
offline_nodes = st.sidebar.multiselect(
    "Simulate offline nodes",
    NODE_NAMES,
)
st.sidebar.caption("Configured quorum: 2 of 3 replicas")

states = status()
online_valid = sum(
    item["available"]
    and item["valid"]
    and item["node"] not in offline_nodes
    for item in states
)

metrics = st.columns(3)
metrics[0].metric("Configured replicas", len(states))
metrics[1].metric("Valid online replicas", online_valid)
metrics[2].metric("Quorum", "2 / 3")

left, right = st.columns(2)

with left:
    if st.button("Initialize node ledgers", type="primary", use_container_width=True):
        try:
            initialize_nodes(source_path, reset=True)
            st.success("Replica ledgers initialized.")
            st.rerun()
        except Exception as error:
            st.error(str(error))

with right:
    if st.button("Synchronize online replicas", use_container_width=True):
        for name in NODE_NAMES:
            if name not in offline_nodes:
                st.write(name, sync_node_from_source(name, source_path))
        st.rerun()

if st.button("Process pending records by majority vote", use_container_width=True):
    try:
        results = append_pending(source_path, offline=tuple(offline_nodes))

        if not results:
            st.info("No unanchored source records are pending.")

        for result in results:
            if result["accepted"]:
                st.success(
                    f"Record {result['record_id']} accepted in block "
                    f"{result['block_index']} "
                    f"({result['yes_votes']}/{result['required']} votes)."
                )
            else:
                st.error(
                    f"Record {result['record_id']} rejected: "
                    f"{result.get('reason', 'quorum not reached')}"
                )

            if "votes" in result:
                st.json(result["votes"])

        st.rerun()
    except Exception as error:
        st.exception(error)

st.subheader("Replica status")
st.dataframe(
    pd.DataFrame(status()),
    use_container_width=True,
    hide_index=True,
)

st.subheader("Majority-vote configuration")
st.write(
    "Each replica maintains a separate local SQLite copy of the hash-linked "
    "ledger. A proposed block is checked by the available replicas and is "
    "accepted when at least two of the three configured replicas approve it."
)
st.warning(
    "The three replicas are hosted on one machine. This demonstration does "
    "not implement PBFT or Raft and does not establish Byzantine fault "
    "tolerance or production decentralization."
)
