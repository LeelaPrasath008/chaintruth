"""Centralized Plotly chart system.

Every chart goes through ``render_chart`` which wraps it in a titled white card
and calls ``finalize_figure`` to enforce consistent layout rules.

No page should call ``st.plotly_chart`` directly.
"""
from __future__ import annotations
import streamlit as st
from utils.theme import T

SERIES = T["series"]

_FONT = T["font"]
_TEXT = T["text"]
_MUTED = T["text_muted"]
_GRID = T["grid"]
_WHITE = "#FFFFFF"

_DEFAULT_HEIGHTS = {
    "area": 340, "line": 340, "bar": 360, "donut": 340, "pie": 340,
    "heatmap": 380, "scatter": 360, "sankey": 440, "gauge": 360,
    "box": 360, "network": 700,
}

_PLOTLY_CONFIG = {
    "responsive": True,
    "displaylogo": False,
    "displayModeBar": "hover",
}


def finalize_figure(fig, kind: str, height: int | None = None, legend: str = "bottom"):
    h = height or _DEFAULT_HEIGHTS.get(kind, 380)

    fig.update_layout(title=None)

    b_margin = 72 if legend == "bottom" else 36
    fig.update_layout(
        paper_bgcolor=_WHITE,
        plot_bgcolor=_WHITE,
        font=dict(family=_FONT, color=_TEXT, size=13),
        margin=dict(l=16, r=16, t=16, b=b_margin),
        height=h,
        hoverlabel=dict(bgcolor=_WHITE, bordercolor=T["border"], font_size=12),
    )

    fig.update_xaxes(
        gridcolor=_GRID, zerolinecolor=_GRID, automargin=True,
        title_standoff=12, tickfont=dict(color=_MUTED, size=12),
    )
    fig.update_yaxes(
        gridcolor=_GRID, zerolinecolor=_GRID, automargin=True,
        title_standoff=12, tickfont=dict(color=_MUTED, size=12),
    )

    if kind in ("donut", "pie"):
        fig.update_traces(
            hole=0.62, textposition="inside", textinfo="percent",
            insidetextorientation="horizontal",
        )
        fig.update_layout(
            uniformtext=dict(minsize=11, mode="hide"),
        )

    if legend == "bottom":
        fig.update_layout(legend=dict(
            orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0,
            font=dict(size=12, color=_MUTED), title_text="",
        ))
    elif legend == "right":
        fig.update_layout(legend=dict(
            font=dict(size=12, color=_MUTED), title_text="",
        ))
    elif legend == "none":
        fig.update_layout(showlegend=False)

    if kind == "bar":
        fig.update_traces(
            cliponaxis=False,
            selector=dict(type="bar"),
        )
        fig.update_layout(uniformtext=dict(minsize=11, mode="hide"))

    for axis_name in list(fig.layout.to_plotly_json().keys()):
        if axis_name.startswith("xaxis"):
            axis = getattr(fig.layout, axis_name)
            if axis.title and axis.title.text:
                txt = axis.title.text.lower()
                if txt in ("month", "order_month"):
                    fig.update_layout(**{axis_name: dict(title_text="")})
                else:
                    fig.update_layout(**{axis_name: dict(
                        title_font=dict(size=12, color=_MUTED))})
        if axis_name.startswith("yaxis"):
            axis = getattr(fig.layout, axis_name)
            if axis.title and axis.title.text:
                fig.update_layout(**{axis_name: dict(
                    title_font=dict(size=12, color=_MUTED))})

    return fig


def render_chart(
    fig,
    kind: str,
    title: str,
    subtitle: str | None = None,
    key: str | None = None,
    height: int | None = None,
    legend: str = "bottom",
):
    finalize_figure(fig, kind, height=height, legend=legend)

    sub_html = f'<div style="font-size:12px; color:{_MUTED}; margin-top:2px;">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div style="background:{_WHITE}; border:1px solid {T["border"]}; '
        f'border-radius:{T["radius"]}; padding:16px; margin-bottom:12px; '
        f'box-shadow:{T["shadow"]};">'
        f'<div style="font-size:15px; font-weight:600; color:{_TEXT};">{title}</div>'
        f'{sub_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CONFIG, key=key)
