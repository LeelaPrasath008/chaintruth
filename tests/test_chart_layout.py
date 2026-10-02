"""Verify finalize_figure enforces layout rules for every chart kind."""
import sys, os, types
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

# Stub streamlit so importing charts.py works without a running server.
st_stub = types.ModuleType("streamlit")
st_stub.markdown = lambda *a, **kw: None
st_stub.plotly_chart = lambda *a, **kw: None
sys.modules.setdefault("streamlit", st_stub)

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import pytest
from utils.charts import finalize_figure, _DEFAULT_HEIGHTS, SERIES

_SAMPLE = pd.DataFrame({"x": [1, 2, 3], "y": [10, 20, 15], "c": ["A", "B", "C"]})


def _make_fig(kind):
    if kind in ("area", "line"):
        return px.line(_SAMPLE, x="x", y="y", title="SHOULD BE REMOVED")
    if kind == "bar":
        return px.bar(_SAMPLE, x="c", y="y", title="SHOULD BE REMOVED")
    if kind in ("donut", "pie"):
        return px.pie(_SAMPLE, names="c", values="y", title="SHOULD BE REMOVED")
    if kind == "scatter":
        return px.scatter(_SAMPLE, x="x", y="y", title="SHOULD BE REMOVED")
    if kind == "heatmap":
        return px.imshow([[1, 2], [3, 4]], title="SHOULD BE REMOVED")
    if kind == "box":
        return px.box(_SAMPLE, x="c", y="y", title="SHOULD BE REMOVED")
    if kind == "gauge":
        return go.Figure(go.Indicator(mode="gauge+number", value=72))
    if kind == "sankey":
        return go.Figure(go.Sankey(
            node=dict(label=["A", "B", "C"]),
            link=dict(source=[0, 0], target=[1, 2], value=[5, 3]),
        ))
    return px.bar(_SAMPLE, x="c", y="y")


@pytest.mark.parametrize("kind", list(_DEFAULT_HEIGHTS.keys()))
def test_title_stripped(kind):
    fig = finalize_figure(_make_fig(kind), kind)
    assert fig.layout.title is None or fig.layout.title.text is None


@pytest.mark.parametrize("kind", list(_DEFAULT_HEIGHTS.keys()))
def test_white_background(kind):
    fig = finalize_figure(_make_fig(kind), kind)
    assert fig.layout.paper_bgcolor == "#FFFFFF"
    assert fig.layout.plot_bgcolor == "#FFFFFF"


@pytest.mark.parametrize("kind", list(_DEFAULT_HEIGHTS.keys()))
def test_default_height(kind):
    fig = finalize_figure(_make_fig(kind), kind)
    assert fig.layout.height == _DEFAULT_HEIGHTS[kind]


def test_custom_height():
    fig = finalize_figure(_make_fig("bar"), "bar", height=500)
    assert fig.layout.height == 500


@pytest.mark.parametrize("legend,visible", [
    ("bottom", True), ("right", True), ("none", False),
])
def test_legend_mode(legend, visible):
    fig = finalize_figure(_make_fig("bar"), "bar", legend=legend)
    if not visible:
        assert fig.layout.showlegend is False
    else:
        assert fig.layout.showlegend is not False


def test_bar_cliponaxis():
    fig = finalize_figure(_make_fig("bar"), "bar")
    for trace in fig.data:
        if trace.type == "bar":
            assert trace.cliponaxis is False


def test_donut_hole():
    fig = finalize_figure(_make_fig("donut"), "donut")
    for trace in fig.data:
        if trace.type == "pie":
            assert trace.hole == 0.62


def test_series_palette():
    assert len(SERIES) >= 5
    for c in SERIES:
        assert c.startswith("#")
