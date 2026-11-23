"""Vẽ biểu đồ giá (cần matplotlib: pip install scrap-price-tracker[chart])."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from .db import PriceDB
from .materials import MATERIALS


def plot(db: PriceDB, materials: list[str], out: str | Path, since: date | None = None) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 5), dpi=120)
    for m in materials:
        hist = db.history(m, since)
        if hist:
            days = mdates.date2num([d for d, _ in hist])  # type: ignore[no-untyped-call]
            ax.plot(days, [p for _, p in hist], marker=".", linewidth=1.6, label=MATERIALS[m][0])
    ax.set_title("Giá phế liệu (đồng/kg)")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:,.0f}".replace(",", "."))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))  # type: ignore[no-untyped-call]
    ax.grid(alpha=0.3)
    ax.legend(frameon=False)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    out = Path(out)
    fig.savefig(out)
    plt.close(fig)
    return out
