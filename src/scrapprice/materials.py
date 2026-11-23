"""Danh mục loại phế liệu và cách nhận diện tên viết tự do ("sắt loại 1", "sat L1", "Sắt đặc"...)."""

from __future__ import annotations

import re
import unicodedata

# mã -> (tên hiển thị, nhóm)
MATERIALS: dict[str, tuple[str, str]] = {
    "sat-dac": ("Sắt đặc (loại 1)", "Sắt"),
    "sat-vun": ("Sắt vụn (loại 2)", "Sắt"),
    "sat-ong": ("Sắt ống, sắt hộp", "Sắt"),
    "dong-cap": ("Đồng cáp", "Đồng"),
    "dong-do": ("Đồng đỏ", "Đồng"),
    "dong-vang": ("Đồng vàng", "Đồng"),
    "nhom-dac": ("Nhôm đặc", "Nhôm"),
    "nhom-lon": ("Nhôm lon", "Nhôm"),
    "nhom-dinh-hinh": ("Nhôm định hình", "Nhôm"),
    "inox-304": ("Inox 304", "Inox"),
    "inox-201": ("Inox 201", "Inox"),
    "chi": ("Chì", "Khác"),
    "giay-carton": ("Giấy carton", "Khác"),
    "nhua": ("Nhựa", "Khác"),
}

ALIASES = {
    "sat-loai-1": "sat-dac", "sat-l1": "sat-dac", "sat-1": "sat-dac",
    "sat-loai-2": "sat-vun", "sat-l2": "sat-vun", "sat-2": "sat-vun",
    "sat-hop": "sat-ong",
    "dong-cap-dien": "dong-cap", "cap-dong": "dong-cap",
    "nhom-lon-bia": "nhom-lon", "lon-nhom": "nhom-lon",
    "inox304": "inox-304", "inox201": "inox-201",
    "carton": "giay-carton", "giay": "giay-carton",
}


def slug(text: str) -> str:
    t = unicodedata.normalize("NFD", text.strip().lower()).replace("đ", "d")
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"\(.*?\)", " ", t)
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def normalize(name: str) -> str:
    """Trả về mã loại phế liệu, hoặc ném ValueError nếu không nhận ra."""
    s = slug(name)
    if s in MATERIALS:
        return s
    if s in ALIASES:
        return ALIASES[s]
    for code, (label, _) in MATERIALS.items():
        if slug(label) == s:
            return code
    raise ValueError(f"không nhận ra loại phế liệu: {name!r}")
