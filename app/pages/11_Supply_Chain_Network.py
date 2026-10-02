import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from utils.db import run_query as run, safe_float
from utils.theme import T
from utils.components import page_header, kpi_card, kpi_grid, section, footer
from utils.charts import apply_light, SERIES

page_header("Supply Chain Network", "Supplier to Plant to Customer flow visualization")

# -- load data -----------------------------------------------------------------
suppliers = run("SELECT SUPPLIER_ID, SUPPLIER_NAME, REGION, COUNTRY FROM CHAINTRUTH_DB.RAW.SUPPLIERS")
plants = run("SELECT PLANT_ID, PLANT_NAME, REGION, COUNTRY FROM CHAINTRUTH_DB.RAW.PLANTS")
customers = run("SELECT CUSTOMER_ID, CUSTOMER_NAME, SEGMENT FROM CHAINTRUTH_DB.RAW.CUSTOMERS")

sup_plant = run("SELECT DISTINCT o.SUPPLIER_ID, o.PLANT_ID FROM CHAINTRUTH_DB.RAW.ORDERS o")
plant_cust = run("SELECT DISTINCT o.PLANT_ID, o.CUSTOMER_ID FROM CHAINTRUTH_DB.RAW.ORDERS o")

# -- sidebar filters -----------------------------------------------------------
st.sidebar.markdown("**Network filters**")
sel_regions = st.sidebar.multiselect("Supplier Region", sorted(suppliers["REGION"].unique().tolist()))
sel_segments = st.sidebar.multiselect("Customer Segment", sorted(customers["SEGMENT"].unique().tolist()))

if sel_regions:
    suppliers = suppliers[suppliers["REGION"].isin(sel_regions)]
    sup_plant = sup_plant[sup_plant["SUPPLIER_ID"].isin(suppliers["SUPPLIER_ID"])]
if sel_segments:
    customers = customers[customers["SEGMENT"].isin(sel_segments)]
    plant_cust = plant_cust[plant_cust["CUSTOMER_ID"].isin(customers["CUSTOMER_ID"])]

max_suppliers = 20
max_customers = 20
suppliers = suppliers.head(max_suppliers)
customers = customers.head(max_customers)
sup_plant = sup_plant[sup_plant["SUPPLIER_ID"].isin(suppliers["SUPPLIER_ID"])]
plant_cust = plant_cust[plant_cust["CUSTOMER_ID"].isin(customers["CUSTOMER_ID"])]

# -- KPIs ----------------------------------------------------------------------
section("Network overview")
kpi_grid([
    kpi_card("Suppliers", str(len(suppliers)), icon_name="factory"),
    kpi_card("Plants", str(len(plants)), icon_name="box"),
    kpi_card("Customers", str(len(customers)), icon_name="search"),
    kpi_card("Connections", str(len(sup_plant) + len(plant_cust)), status="healthy", icon_name="link"),
])

# -- network graph -------------------------------------------------------------
section("Network topology")

node_ids = {}
node_x, node_y = [], []
node_text, node_color, node_size = [], [], []

for i, (_, s) in enumerate(suppliers.iterrows()):
    nid = f"S_{s['SUPPLIER_ID']}"
    node_ids[nid] = len(node_ids)
    node_x.append(0)
    node_y.append(i / max(len(suppliers) - 1, 1))
    node_text.append(f"{s['SUPPLIER_NAME']}<br>{s['REGION']}")
    node_color.append(SERIES[0])
    node_size.append(14)

for i, (_, p) in enumerate(plants.iterrows()):
    nid = f"P_{p['PLANT_ID']}"
    node_ids[nid] = len(node_ids)
    node_x.append(0.5)
    node_y.append(i / max(len(plants) - 1, 1))
    node_text.append(f"{p['PLANT_NAME']}<br>{p['REGION']}")
    node_color.append(SERIES[1])
    node_size.append(20)

for i, (_, c) in enumerate(customers.iterrows()):
    nid = f"C_{c['CUSTOMER_ID']}"
    node_ids[nid] = len(node_ids)
    node_x.append(1)
    node_y.append(i / max(len(customers) - 1, 1))
    node_text.append(f"{c['CUSTOMER_NAME']}<br>{c['SEGMENT']}")
    node_color.append(SERIES[2])
    node_size.append(12)

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

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=edge_x, y=edge_y, mode="lines",
    line=dict(width=0.6, color=T["border"]),
    hoverinfo="none",
))

fig.add_trace(go.Scatter(
    x=node_x, y=node_y, mode="markers+text",
    marker=dict(size=node_size, color=node_color, line=dict(width=1.5, color=T["surface"])),
    text=[t.split("<br>")[0] for t in node_text],
    textposition="middle right",
    textfont=dict(size=8, color=T["text_muted"]),
    hovertext=node_text,
    hoverinfo="text",
))

fig.update_layout(
    showlegend=False,
    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.1, 1.15]),
    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    annotations=[
        dict(x=0, y=1.08, text=f"<b>SUPPLIERS</b> ({len(suppliers)})", showarrow=False,
             font=dict(size=13, color=SERIES[0]), xref="x", yref="y"),
        dict(x=0.5, y=1.08, text=f"<b>PLANTS</b> ({len(plants)})", showarrow=False,
             font=dict(size=13, color=SERIES[1]), xref="x", yref="y"),
        dict(x=1, y=1.08, text=f"<b>CUSTOMERS</b> ({len(customers)})", showarrow=False,
             font=dict(size=13, color=SERIES[2]), xref="x", yref="y"),
    ],
)
apply_light(fig, 700)
st.plotly_chart(fig, use_container_width=True)

st.caption(
    f"Showing top {max_suppliers} suppliers and {max_customers} customers. "
    f"Use sidebar filters to focus on specific regions or segments."
)

footer()
