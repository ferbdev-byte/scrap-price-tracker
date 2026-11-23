from datetime import date

from scrapprice import PriceDB, Quote
from scrapprice.cli import main


def test_export_then_import_roundtrip(tmp_path):
    a = PriceDB(tmp_path / "a.db")
    a.add(Quote(date(2026, 11, 1), "sat-dac", 9200, "vựa A", "giao, tận nơi"))
    a.add(Quote(date(2026, 11, 2), "dong-cap", 182000))
    out = tmp_path / "gia.csv"
    assert a.export_csv(out) == 2
    assert out.read_bytes().startswith(b"\xef\xbb\xbf")
    b = PriceDB(tmp_path / "b.db")
    assert b.import_csv(out) == (2, [])
    assert b.history("sat-dac") == a.history("sat-dac")
    a.close()
    b.close()


def test_cli_export(tmp_path, capsys):
    dbp = str(tmp_path / "c.db")
    main(["--db", dbp, "add", "sắt loại 1", "9.500"])
    assert main(["--db", dbp, "export", "-o", str(tmp_path / "x.csv"), "--days", "30"]) == 0
    assert "Đã xuất 1 dòng" in capsys.readouterr().out
