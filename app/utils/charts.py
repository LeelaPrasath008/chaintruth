"""Plotly chart helpers — light theme matching design tokens."""

from utils.theme import T

SERIES = T["series"]

_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor=T["surface"],
    font=dict(family=T["font"], color=T["text"], size=13),
    title_font=dict(size=14, color=T["text"]),
    legend=dict(font=dict(color=T["text_muted"], size=12)),
    xaxis=dict(gridcolor=T["grid"], zerolinecolor=T["grid"],
               tickfont=dict(color=T["text_muted"], size=11)),
    yaxis=dict(gridcolor=T["grid"], zerolinecolor=T["grid"],
               tickfont=dict(color=T["text_muted"], size=11)),
    margin=dict(l=48, r=16, t=36, b=36),
)


def apply_light(fig, height: int = 380):
    fig.update_layout(**_LAYOUT, height=height)
    return fig
