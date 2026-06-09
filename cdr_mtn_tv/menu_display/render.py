"""Render TV1 landscape menu table from menu.json."""

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import load_config, root_path  # noqa: E402

BG_COLOR = (32, 32, 32)
HEADER_BG = (64, 64, 64)
ROW_ALT_BG = (40, 40, 40)
TEXT_COLOR = (255, 255, 255)
BORDER_COLOR = (96, 96, 96)


def load_font(path: Path, size: int, config: dict | None = None) -> ImageFont.FreeTypeFont:
    fallback = root_path((config or load_config())["fonts"]["fallback"])
    try:
        font = ImageFont.truetype(str(path), size)
        if hasattr(font, "set_variation_by_axes"):
            try:
                font.set_variation_by_axes([700])
            except OSError:
                pass
        return font
    except OSError:
        return ImageFont.truetype(str(fallback), size)


def load_menu() -> dict:
    menu_path = root_path("data", "menu.json")
    with open(menu_path, encoding="utf-8") as f:
        return json.load(f)


def column_layout(config: dict) -> list[dict]:
    tv_width = config["tv1"]["width"]
    layout = []
    x = 0
    for group in config["menu_groups"]:
        group_width = int(tv_width * group["width_percent"] / 100)
        group_x = x
        col_x = group_x
        group_cols = [
            c for c in config["menu_columns"] if c["group"] == group["key"]
        ]
        for col in group_cols:
            col_width = int(group_width * col["width_percent"] / 100)
            layout.append(
                {
                    "key": col["key"],
                    "label": col["label"],
                    "group": group["key"],
                    "group_label": group["label"],
                    "x": col_x,
                    "width": col_width,
                    "group_x": group_x,
                    "group_width": group_width,
                }
            )
            col_x += col_width
        x += group_width
    return layout


def draw_centered_text(draw, text, font, x, y, width, height, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    tx = x + (width - text_w) // 2
    ty = y + (height - text_h) // 2
    draw.text((tx, ty), text, font=font, fill=fill)


def draw_cell_border(draw, x, y, width, height):
    draw.rectangle(
        [x, y, x + width - 1, y + height - 1],
        outline=BORDER_COLOR,
        width=1,
    )


def render_menu(config: dict | None = None, menu: dict | None = None) -> Path:
    config = config or load_config()
    menu = menu or load_menu()
    tv1 = config["tv1"]
    width = tv1["width"]
    height = tv1["height"]

    header_font = load_font(root_path(config["fonts"]["header"]), 56, config)
    body_font = load_font(root_path(config["fonts"]["body"]), 36, config)
    label_font = load_font(root_path(config["fonts"]["body"]), 32, config)

    layout = column_layout(config)
    row_count = config.get("menu_row_count", 10)

    header_h = 90
    group_h = 60
    col_header_h = 50
    footer_h = 70
    body_h = height - header_h - group_h - col_header_h - footer_h
    data_row_h = body_h // row_count

    image = Image.new("RGB", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(image)

    y = 0
    draw.rectangle([0, y, width, y + header_h], fill=HEADER_BG)
    draw_centered_text(
        draw,
        menu.get("header") or config["placeholders"]["header"],
        header_font,
        0,
        y,
        width,
        header_h,
        TEXT_COLOR,
    )
    draw_cell_border(draw, 0, y, width, header_h)
    y += header_h

    group_y = y
    group_x = 0
    for group in config["menu_groups"]:
        group_width = int(width * group["width_percent"] / 100)
        draw.rectangle(
            [group_x, group_y, group_x + group_width, group_y + group_h],
            fill=HEADER_BG,
        )
        draw_centered_text(
            draw,
            group["label"],
            label_font,
            group_x,
            group_y,
            group_width,
            group_h,
            TEXT_COLOR,
        )
        draw_cell_border(draw, group_x, group_y, group_width, group_h)
        group_x += group_width
    y += group_h

    col_y = y
    for col in layout:
        draw.rectangle(
            [col["x"], col_y, col["x"] + col["width"], col_y + col_header_h],
            fill=HEADER_BG,
        )
        draw_centered_text(
            draw,
            col["label"],
            label_font,
            col["x"],
            col_y,
            col["width"],
            col_header_h,
            TEXT_COLOR,
        )
        draw_cell_border(draw, col["x"], col_y, col["width"], col_header_h)
    y += col_header_h

    rows = menu.get("rows", [])
    for i in range(row_count):
        row_y = y + i * data_row_h
        row_bg = ROW_ALT_BG if i % 2 else BG_COLOR
        draw.rectangle([0, row_y, width, row_y + data_row_h], fill=row_bg)
        row_data = rows[i] if i < len(rows) else {}
        for col in layout:
            value = str(row_data.get(col["key"], ""))
            draw_centered_text(
                draw,
                value,
                body_font,
                col["x"],
                row_y,
                col["width"],
                data_row_h,
                TEXT_COLOR,
            )
            draw_cell_border(draw, col["x"], row_y, col["width"], data_row_h)
    y += row_count * data_row_h

    draw.rectangle([0, y, width, height], fill=HEADER_BG)
    draw_centered_text(
        draw,
        menu.get("footer") or config["placeholders"]["footer"],
        label_font,
        0,
        y,
        width,
        footer_h,
        TEXT_COLOR,
    )
    draw_cell_border(draw, 0, y, width, footer_h)

    output_path = root_path(config["output"]["tv1_menu"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, quality=95)
    print(f"Saved menu poster to {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Render TV1 menu poster")
    parser.parse_args()
    render_menu()


if __name__ == "__main__":
    main()
