import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from utils.db import run_query as run, safe_float
from utils.theme import inject_css, hero, section

st.set_page_config(page_title="Supply Chain Network", layout="wide", page_icon="🔗")
inject_css()

hero("SUPPLY CHAIN NETWORK", "Visual graph of Supplier → Plant → Customer relationships")

# -- load data -----------------------------------------------------------------
suppliers = run(
    "SELECT SUPPLIER_ID, SUPPLIER_NAME, REGION, COUNTRY FROM CHAINTRUTH_DB.RAW.SUPPLIERS"
)
plants = run(
    "SELECT PLANT_ID, PLANT_NAME, REGION, COUNTRY FROM CHAINTRUTH_DB.RAW.PLANTS"
)
customers = run(
    "SELECT CUSTOMER_ID, CUSTOMER_NAME, SEGMENT FROM CHAINTRUTH_DB.RAW.CUSTOMERS"
)

# supplier-plant links from orders (ORDERS has both SUPPLIER_ID and PLANT_ID)
sup_plant = run(
    "SELECT DISTINCT o.SUPPLIER_ID, o.PLANT_ID "
    "FROM CHAINTRUTH_DB.RAW.ORDERS o"
)

# plant-customer links from orders
plant_cust = run(
    "SELECT DISTINCT o.PLANT_ID, o.CUSTOMER_ID "
    "FROM CHAINTRUTH_DB.RAW.ORDERS o"
)

# -- sidebar filters -----------------------------------------------------------
st.sidebar.header("Network Filters")
sel_regions = st.sidebar.multiselect(
    "Supplier Region", sorted(suppliers["REGION"].unique().tolist())
)
sel_segments = st.sidebar.multiselect(
    "Customer Segment", sorted(customers["SEGMENT"].unique().tolist())
)

# filter suppliers
if sel_regions:
    suppliers = suppliers[suppliers["REGION"].isin(sel_regions)]
    sup_plant = sup_plant[sup_plant["SUPPLIER_ID"].isin(suppliers["SUPPLIER_ID"])]

# filter customers
if sel_segments:
    customers = customers[customers["SEGMENT"].isin(sel_segments)]
    plant_cust = plant_cust[plant_cust["CUSTOMER_ID"].isin(customers["CUSTOMER_ID"])]

# limit to keep graph readable
max_suppliers = 20
max_customers = 20
suppliers = suppliers.head(max_suppliers)
customers = customers.head(max_customers)
sup_plant = sup_plant[sup_plant["SUPPLIER_ID"].isin(suppliers["SUPPLIER_ID"])]
plant_cust = plant_cust[plant_cust["CUSTOMER_ID"].isin(customers["CUSTOMER_ID"])]

# =============================================================================
# BUILD NETWORK GRAPH
# =============================================================================
section("Network Topology")

# Assign positions: suppliers left, plants center, customers right
node_ids = {}
node_x, node_y = [], []
node_text, node_color, node_size = [], [], []

# Suppliers (left column)
for i, (_, s) in enumerate(suppliers.iterrows()):
    nid = f"S_{s['SUPPLIER_ID']}"
    node_ids[nid] = len(node_ids)
    node_x.append(0)
    node_y.append(i / max(len(suppliers) - 1, 1))
    node_text.append(f"{s['SUPPLIER_NAME']}<br>{s['REGION']}")
    node_color.append("#2563EB")
    node_size.append(14)

# Plants (center column)
for i, (_, p) in enumerate(plants.iterrows()):
    nid = f"P_{p['PLANT_ID']}"
    node_ids[nid] = len(node_ids)
    node_x.append(0.5)
    node_y.append(i / max(len(plants) - 1, 1))
    node_text.append(f"{p['PLANT_NAME']}<br>{p['REGION']}")
    node_color.append("#10B981")
    node_size.append(18)

# Customers (right column)
for i, (_, c) in enumerate(customers.iterrows()):
    nid = f"C_{c['CUSTOMER_ID']}"
    node_ids[nid] = len(node_ids)
    node_x.append(1)
    node_y.append(i / max(len(customers) - 1, 1))
    node_text.append(f"{c['CUSTOMER_NAME']}<br>{c['SEGMENT']}")
    node_color.append("#F59E0B")
    node_size.append(12)

# Build edges
edge_x, edge_y = [], []

for _, row in sup_plant.iterrows():
    src = node_ids.get(f"S_{row['SUPPLIER_ID']}")
    tgt = node_ids.get(f"P_{row['PLANT_ID']}")
    if src is not None and tgt is not None:
        edge_x += [node_x[src], node_x[tgt], None]
        edge_y += [node_y[src], node_y[tgt], None]

for _, row in plant_cust.iterrows():
    src = node_ids.get(f"P_{row['PLANT_ID']}")
    tgt = node_ids.get(f"C_{row['CUSTOMER_ID']}")
    if src is not None and tgt is not None:
        edge_x += [node_x[src], node_x[tgt], None]
        edge_y += [node_y[src], node_y[tgt], None]

# Create figure
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=edge_x, y=edge_y, mode="lines",
    line=dict(width=0.5, color="#CBD5E1"),
    hoverinfo="none",
))

fig.add_trace(go.Scatter(
    x=node_x, y=node_y, mode="markers+text",
    marker=dict(size=node_size, color=node_color, line=dict(width=1, color="white")),
    text=[t.split("<br>")[0] for t in node_text],
    textposition="middle right",
    textfont=dict(size=8),
    hovertext=node_text,
    hoverinfo="text",
))

fig.update_layout(
    title="Supplier → Plant → Customer Network",
    showlegend=False,
    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.1, 1.15]),
    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    height=700,
    plot_bgcolor="white",
    annotations=[
        dict(x=0, y=1.08, text="<b>SUPPLIERS</b>", showarrow=False, font=dict(size=14, color="#2563EB"), xref="x", yref="y"),
        dict(x=0.5, y=1.08, text="<b>PLANTS</b>", showarrow=False, font=dict(size=14, color="#10B981"), xref="x", yref="y"),
        dict(x=1, y=1.08, text="<b>CUSTOMERS</b>", showarrow=False, font=dict(size=14, color="#F59E0B"), xref="x", yref="y"),
    ],
)

st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# NETWORK STATS
# =============================================================================
section("Network Statistics")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Suppliers Shown", len(suppliers))
c2.metric("Plants", len(plants))
c3.metric("Customers Shown", len(customers))
c4.metric("Connections", len(sup_plant) + len(plant_cust))

st.markdown("---")
st.caption(
    f"Showing top {max_suppliers} suppliers and {max_customers} customers. "
    f"Use sidebar filters to focus on specific regions or segments."
)
