import sqlite3
from datetime import date, timedelta

import pytest

from scrapprice import PriceDB, Quote, normalize
from scrapprice.cli import main
from scrapprice.db import parse_price


@pytest.mark.parametrize(
    "raw, code",
    [("Sắt loại 1", "sat-dac"), ("sat L2", "sat-vun"), ("Đồng cáp", "dong-cap"), ("INOX304", "inox-304"),
     ("Nhôm lon (bia)", "nhom-lon"), ("Sắt đặc (loại 1)", "sat-dac"), ("carton", "giay-carton")],
)
def test_normalize(raw, code):
    assert normalize(raw) == code


def test_normalize_unknown():
    with pytest.raises(ValueError):
        normalize("vàng 9999")


@pytest.mark.parametrize("raw, value", [("12.500", 12500), ("12,500", 12500), ("12500đ", 12500), ("12.5k", 12500),
                                        ("185k", 185000), (9000, 9000)])
def test_parse_price(raw, value):
    assert parse_price(raw) == value


@pytest.fixture
def db(tmp_path):
    d = PriceDB(tmp_path / "g.db")
    start = date(2026, 10, 1)
    for i in range(40):
        d.add(Quote(start + timedelta(days=i), "sat-dac", 9000 + i * 10))
    d.add(Quote(date(2026, 11, 9), "dong-cap", 180000, "vựa A"))
    d.add(Quote(date(2026, 11, 9), "dong-cap", 184000, "vựa B"))
    yield d
    d.close()


def test_history_averages_sources(db):
    assert db.history("dong-cap") == [(date(2026, 11, 9), 182000)]


def test_stats_changes(db):
    s = db.stats("sat-dac", today=date(2026, 11, 9))
    assert s.latest == 9390 and s.latest_day == date(2026, 11, 9)
    assert s.change_7d == round(70 / 9320 * 100, 1)
    assert s.change_30d == round(300 / 9090 * 100, 1)
    assert s.low == 9000 and s.high == 9390


def test_upsert_same_day_same_source(db):
    db.add(Quote(date(2026, 11, 9), "sat-dac", 9999))
    assert db.history("sat-dac")[-1][1] == 9999


def test_board(db):
    codes = [s.material for s in db.board(today=date(2026, 11, 9))]
    assert codes == ["dong-cap", "sat-dac"]


def test_rejects_bad_price(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.add(Quote(date(2026, 1, 1), "sat-dac", 0))


def test_import_csv(tmp_path):
    csv_file = tmp_path / "gia.csv"
    csv_file.write_text(
        "ngay,loai,gia,nguon\n2026-11-01,Sắt loại 1,9.200,vựa A\n2026-11-01,Đồng cáp,182k,\n"
        "2026-11-02,không rõ,1000,\n2026-13-01,sat-dac,9000,\n",
        encoding="utf-8",
    )
    d = PriceDB(tmp_path / "x.db")
    ok, errors = d.import_csv(csv_file)
    assert ok == 2 and len(errors) == 2
    d.close()


def test_chart(db, tmp_path):
    pytest.importorskip("matplotlib")
    from scrapprice.chart import plot

    out = plot(db, ["sat-dac", "dong-cap"], tmp_path / "c.png")
    assert out.stat().st_size > 5000


def test_cli(tmp_path, capsys):
    dbp = str(tmp_path / "c.db")
    assert main(["--db", dbp, "add", "sắt loại 1", "9.500"]) == 0
    assert main(["--db", dbp, "board"]) == 0
    out = capsys.readouterr().out
    assert "Sắt đặc" in out and "9.500" in out
    assert main(["--db", dbp, "add", "vàng", "1"]) == 2
