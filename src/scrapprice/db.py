"""Lưu giá vào SQLite và tính thống kê."""

from __future__ import annotations

import csv
import sqlite3
import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from .materials import MATERIALS, normalize

SCHEMA = """
CREATE TABLE IF NOT EXISTS quote (
    day       TEXT NOT NULL,         -- YYYY-MM-DD
    material  TEXT NOT NULL,
    price     INTEGER NOT NULL CHECK (price > 0),   -- đồng / kg
    source    TEXT NOT NULL DEFAULT '',             -- nơi báo giá: vựa, đối tác, nhà máy...
    note      TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (day, material, source)
);
CREATE INDEX IF NOT EXISTS idx_quote_material ON quote(material, day);
"""


@dataclass(frozen=True)
class Quote:
    day: date
    material: str
    price: int
    source: str = ""
    note: str = ""


@dataclass(frozen=True)
class Stats:
    material: str
    latest: int
    latest_day: date
    low: int
    high: int
    mean: float
    change_7d: float | None   # % so với giá gần nhất cách >= 7 ngày
    change_30d: float | None


def parse_price(text: str | int) -> int:
    """'12.500' / '12,500' / '12500đ' / '12.5k' -> 12500."""
    if isinstance(text, int):
        return text
    t = str(text).strip().lower().replace("đ", "").replace("vnd", "").replace(" ", "")
    if t.endswith("k"):
        return round(float(t[:-1].replace(",", ".")) * 1000)
    return int(t.replace(".", "").replace(",", ""))


class PriceDB:
    def __init__(self, path: str | Path = "gia-phe-lieu.db"):
        self.conn = sqlite3.connect(str(path))
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    def add(self, q: Quote) -> None:
        if q.material not in MATERIALS:
            raise ValueError(f"mã không hợp lệ: {q.material}")
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO quote(day, material, price, source, note) VALUES (?,?,?,?,?)",
                (q.day.isoformat(), q.material, q.price, q.source, q.note),
            )

    def import_csv(self, path: str | Path) -> tuple[int, list[str]]:
        """CSV có cột: ngay, loai, gia, [nguon], [ghi_chu]. Trả về (số dòng nhập, danh sách lỗi)."""
        ok, errors = 0, []
        with open(path, encoding="utf-8-sig", newline="") as f:
            for i, row in enumerate(csv.DictReader(f), start=2):
                try:
                    day = date.fromisoformat(row["ngay"].strip())
                    q = Quote(day, normalize(row["loai"]), parse_price(row["gia"]),
                              (row.get("nguon") or "").strip(), (row.get("ghi_chu") or "").strip())
                    self.add(q)
                    ok += 1
                except (KeyError, ValueError) as exc:
                    errors.append(f"dòng {i}: {exc}")
        return ok, errors

    def export_csv(self, path: str | Path, since: date | None = None) -> int:
        """Ghi ra CSV cùng định dạng với `import_csv` (nhập lại được), UTF-8 BOM để Excel mở đúng dấu."""
        rows = self.conn.execute(
            "SELECT day, material, price, source, note FROM quote WHERE day>=? ORDER BY day, material, source",
            ((since or date.min).isoformat(),),
        ).fetchall()
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["ngay", "loai", "gia", "nguon", "ghi_chu"])
            w.writerows(rows)
        return len(rows)

    def history(self, material: str, since: date | None = None) -> list[tuple[date, int]]:
        """Giá theo ngày (trung bình nếu một ngày có nhiều nguồn)."""
        rows = self.conn.execute(
            "SELECT day, AVG(price) FROM quote WHERE material=? AND day>=? GROUP BY day ORDER BY day",
            (material, (since or date.min).isoformat()),
        ).fetchall()
        return [(date.fromisoformat(d), round(p)) for d, p in rows]

    def materials(self) -> list[str]:
        return [r[0] for r in self.conn.execute("SELECT DISTINCT material FROM quote ORDER BY material")]

    def stats(self, material: str, days: int = 90, today: date | None = None) -> Stats | None:
        today = today or date.today()
        hist = self.history(material, today - timedelta(days=days))
        if not hist:
            return None
        latest_day, latest = hist[-1]

        def change(back: int) -> float | None:
            ref = [p for d, p in hist if d <= latest_day - timedelta(days=back)]
            return None if not ref else round((latest - ref[-1]) / ref[-1] * 100, 1)

        prices = [p for _, p in hist]
        return Stats(material, latest, latest_day, min(prices), max(prices),
                     round(statistics.fmean(prices)), change(7), change(30))

    def board(self, today: date | None = None) -> list[Stats]:
        """Bảng giá hiện tại của mọi loại đã có dữ liệu."""
        out = [self.stats(m, today=today) for m in self.materials()]
        return [s for s in out if s]
