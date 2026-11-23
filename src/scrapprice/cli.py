"""Dòng lệnh scrapprice."""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

from . import __version__
from .db import PriceDB, Quote, parse_price
from .materials import MATERIALS, normalize


def vnd(n: float) -> str:
    return f"{n:,.0f}".replace(",", ".")


def pct(x: float | None) -> str:
    if x is None:
        return "—"
    arrow = "▲" if x > 0 else "▼" if x < 0 else "="
    return f"{arrow} {abs(x):.1f}%"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="scrapprice", description="Theo dõi giá phế liệu.")
    p.add_argument("--version", action="version", version=f"scrapprice {__version__}")
    p.add_argument("--db", default="gia-phe-lieu.db")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="thêm một báo giá")
    a.add_argument("loai")
    a.add_argument("gia", help="vd. 12500, 12.500, 12.5k")
    a.add_argument("--ngay", type=date.fromisoformat, default=date.today())
    a.add_argument("--nguon", default="")

    i = sub.add_parser("import", help="nhập CSV: ngay,loai,gia[,nguon,ghi_chu]")
    i.add_argument("csv")

    ex = sub.add_parser("export", help="xuất CSV (nhập lại được bằng import)")
    ex.add_argument("-o", "--out", default="gia-phe-lieu.csv")
    ex.add_argument("--days", type=int, help="chỉ lấy N ngày gần nhất")

    sub.add_parser("board", help="bảng giá hiện tại")
    sub.add_parser("types", help="danh mục loại phế liệu")

    h = sub.add_parser("history", help="lịch sử giá một loại")
    h.add_argument("loai")
    h.add_argument("--days", type=int, default=30)

    c = sub.add_parser("chart", help="vẽ biểu đồ PNG")
    c.add_argument("loai", nargs="+")
    c.add_argument("-o", "--out", default="bieu-do-gia.png")
    c.add_argument("--days", type=int, default=90)

    args = p.parse_args(argv)
    db = PriceDB(args.db)
    try:
        if args.cmd == "add":
            db.add(Quote(args.ngay, normalize(args.loai), parse_price(args.gia), args.nguon))
            print("Đã lưu.")
        elif args.cmd == "import":
            ok, errors = db.import_csv(args.csv)
            print(f"Đã nhập {ok} dòng, {len(errors)} lỗi")
            for e in errors[:20]:
                print("  ", e)
            return 1 if errors and not ok else 0
        elif args.cmd == "export":
            since = date.today() - timedelta(days=args.days) if args.days else None
            print(f"Đã xuất {db.export_csv(args.out, since)} dòng ra {args.out}")
        elif args.cmd == "types":
            for code, (label, group) in MATERIALS.items():
                print(f"{code:<16} {label:<22} {group}")
        elif args.cmd == "board":
            rows = db.board()
            if not rows:
                print("Chưa có dữ liệu. Thêm bằng: scrapprice add sat-dac 9500")
                return 0
            print(f"{'Loại':<22} {'Giá (đ/kg)':>11} {'Ngày':>11} {'7 ngày':>9} {'30 ngày':>9} {'Thấp–Cao 90 ngày':>22}")
            for s in rows:
                print(f"{MATERIALS[s.material][0]:<22} {vnd(s.latest):>11} {s.latest_day:%d/%m/%Y} "
                      f"{pct(s.change_7d):>9} {pct(s.change_30d):>9} {vnd(s.low) + ' – ' + vnd(s.high):>22}")
        elif args.cmd == "history":
            for d, price in db.history(normalize(args.loai), date.today() - timedelta(days=args.days)):
                print(f"{d:%d/%m/%Y}  {vnd(price):>10}")
        elif args.cmd == "chart":
            from .chart import plot

            codes = [normalize(x) for x in args.loai]
            out = plot(db, codes, args.out, date.today() - timedelta(days=args.days))
            print(f"Đã vẽ {out}")
    except ValueError as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 2
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
