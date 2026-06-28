"""Render TV1 landscape menu matching Cedar Mountain Canteen layout."""

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from menu_format import format_abv, format_price  # noqa: E402
from paths import load_config, root_path  # noqa: E402

# Set True to print sidebar font-fit diagnostics.
DEBUG = False
_crop_debug_counter = 0


def load_font(path: Path, size: int, config: dict) -> ImageFont.FreeTypeFont:
    fallback = root_path(config["fonts"]["fallback"])
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
    with open(root_path("data", "menu.json"), encoding="utf-8") as f:
        return json.load(f)


def rgb(config: dict, key: str) -> tuple:
    return tuple(config["menu_colors"][key])


def text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def wrap_text(draw, text, font, max_width):
    words = text.split()
    if not words:
        return [text]
    lines = [words[0]]
    for word in words[1:]:
        trial = f"{lines[-1]} {word}"
        if text_size(draw, trial, font)[0] <= max_width:
            lines[-1] = trial
        else:
            lines.append(word)
    return lines


def _rotated_label_image(text, font, config, rotation):
    """Render horizontal text, then rotate. After 90°: width ≈ font height, height ≈ text length."""
    pad = 8
    fill = rgb(config, "white")
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    left, top, right, bottom = probe.textbbox((0, 0), text, font=font)
    tw = right - left
    th = bottom - top
    label_img = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(label_img).text(
        (pad - left, pad - top), text, font=font, fill=fill
    )
    return label_img.rotate(rotation, expand=True)


def _debug_sidebar(
    text,
    font_size,
    rotation,
    x,
    y,
    w,
    h,
    border_inset,
    inner_pad,
    inner_x,
    inner_y,
    inner_w,
    inner_h,
    rx,
    ry,
    label,
    hit_min=False,
):
    note = " (min size)" if hit_min else ""
    box_r = x + w
    box_b = y + h
    inner_r = inner_x + inner_w
    inner_b = inner_y + inner_h
    label_r = rx + label.width
    label_b = ry + label.height
    print(
        f"[sidebar] text={text!r}{note}\n"
        f"  font_size={font_size} rotation={rotation} label={label.width}x{label.height}\n"
        f"  box=({x},{y})-({box_r},{box_b}) size={w}x{h} border_inset={border_inset}\n"
        f"  inner=({inner_x},{inner_y})-({inner_r},{inner_b}) size={inner_w}x{inner_h} "
        f"pad={inner_pad}\n"
        f"  paste=({rx},{ry})-({label_r},{label_b})\n"
        f"  gap_x=({rx - inner_x},{inner_r - label_r}) gap_y=({ry - inner_y},{inner_b - label_b})"
    )


def _crop_to_content(image: Image.Image, margin: int = 2) -> Image.Image:
    """Trim transparent margins; keep a small halo so rounded glyphs are not clipped."""
    global _crop_debug_counter
    bbox = image.getbbox()
    if not bbox:
        cropped = image
    else:
        left = max(0, bbox[0] - margin)
        top = max(0, bbox[1] - margin)
        right = min(image.width, bbox[2] + margin)
        bottom = min(image.height, bbox[3] + margin)
        cropped = image.crop((left, top, right, bottom))
    if DEBUG:
        _crop_debug_counter += 1
        out_dir = root_path("output")
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = f"sidebar_crop_{_crop_debug_counter:03d}"
        image.save(out_dir / f"{stem}_before.png")
        cropped.save(out_dir / f"{stem}_after.png")
    return cropped


def _fit_rotated_label(text, font_path, start_size, config, inner_w, inner_h, rotation):
    """Pick the largest font size that fits the sidebar interior."""
    glyph_pad = 2
    for size in range(start_size, 18, -2):
        font = load_font(font_path, size, config)
        rotated = _rotated_label_image(text, font, config, rotation)
        cropped = _crop_to_content(rotated)
        if (
            cropped.width + glyph_pad <= inner_w
            and cropped.height + glyph_pad <= inner_h
        ):
            return cropped, size, False
    min_size = 18
    font = load_font(font_path, min_size, config)
    rotated = _rotated_label_image(text, font, config, rotation)
    cropped = _crop_to_content(rotated)
    return cropped, min_size, True


def draw_sidebar(image, x, y, w, h, text, config):
    """Draw a vertical sidebar label with border."""
    layout = config["menu_layout"]
    inner_pad = layout.get("sidebar_inner_pad", 6)
    border_inset = layout.get("sidebar_border_inset", 2)
    border_color = rgb(config, "sidebar_border")
    font_path = root_path(config["fonts"]["sidebar"])
    start_size = layout.get("sidebar_font_size", 34)
    rotation = 90

    draw = ImageDraw.Draw(image)
    draw.rectangle(
        [x + border_inset, y + border_inset, x + w - border_inset, y + h - border_inset],
        outline=border_color,
        width=2,
    )

    inner_x = x + inner_pad
    inner_y = y + inner_pad
    inner_w = w - inner_pad * 2
    inner_h = h - inner_pad * 2
    rotated, font_size, hit_min = _fit_rotated_label(
        text, font_path, start_size, config, inner_w, inner_h, rotation
    )
    rx = inner_x + max(0, (inner_w - rotated.width) // 2)
    ry = inner_y + max(0, (inner_h - rotated.height) // 2)
    if DEBUG:
        _debug_sidebar(
            text,
            font_size,
            rotation,
            x,
            y,
            w,
            h,
            border_inset,
            inner_pad,
            inner_x,
            inner_y,
            inner_w,
            inner_h,
            rx,
            ry,
            rotated,
            hit_min=hit_min,
        )
    image.paste(rotated, (rx, ry), rotated)


def draw_split_row(draw, y, name, abv, price, x, width, font, fill, abv_x, price_x, pad_x):
    draw.text((x + pad_x, y), name, font=font, fill=fill)
    if abv:
        abv_w, _ = text_size(draw, abv, font)
        draw.text((abv_x - abv_w // 2, y), abv, font=font, fill=fill)
    if price:
        price_w, _ = text_size(draw, price, font)
        draw.text((price_x - price_w, y), price, font=font, fill=fill)


def draw_name_price_row(draw, y, name, price, x, width, font, fill, pad_x):
    draw.text((x + pad_x, y), name, font=font, fill=fill)
    if price:
        price_w, _ = text_size(draw, price, font)
        draw.text((x + width - price_w - pad_x, y), price, font=font, fill=fill)


def render_menu(config: dict | None = None, menu: dict | None = None) -> Path:
    config = config or load_config()
    menu = menu or load_menu()
    layout = config["menu_layout"]

    width = config["tv1"]["width"]
    height = config["tv1"]["height"]
    sidebar_w = layout["sidebar_width"]
    sidebar_inset = layout.get("sidebar_inset", 4)
    column_gutter = layout.get("column_gutter", 28)
    content_pad_x = layout.get("content_pad_x", 12)
    footer_h = layout["footer_height"]
    content_h = height - footer_h

    body_font_path = root_path(config["fonts"]["body"])
    draft_font = load_font(body_font_path, 34, config)
    right_body_font = load_font(body_font_path, 32, config)
    right_small_font = load_font(body_font_path, 24, config)
    right_section_font = load_font(body_font_path, 36, config)
    footer_font = load_font(body_font_path, 30, config)

    white = rgb(config, "white")
    wine_color = rgb(config, "wine")
    bev_color = rgb(config, "beverage")
    food_color = rgb(config, "food")
    yellow = rgb(config, "yellow")
    bg = rgb(config, "background")

    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)

    # Symmetric margins: inset | sidebar | gutter | content | gutter | sidebar | inset
    left_sb_x = sidebar_inset
    right_sb_x = width - sidebar_inset - sidebar_w
    main_x = left_sb_x + sidebar_w + content_pad_x
    main_right = width - sidebar_inset - sidebar_w - content_pad_x
    main_w = main_right - main_x
    draft_w = int((main_w - column_gutter) * layout["draft_width_percent"] / 100)
    right_x = main_x + draft_w + column_gutter
    right_w = main_right - right_x

    draw_sidebar(
        image, left_sb_x, 0, sidebar_w, content_h,
        menu.get("sidebar_left", "DRAFT"), config,
    )
    draw_sidebar(
        image, right_sb_x, 0, sidebar_w, content_h,
        menu.get("sidebar_right", "Cedar Mountain Canteen"), config,
    )

    draft_rows = menu.get("draft", [])
    draft_count = layout["draft_row_count"]
    draft_slots = draft_count + 2
    row_h = content_h // max(draft_slots, 1)
    abv_x = main_x + int(draft_w * layout.get("draft_abv_x_percent", 84) / 100)
    price_x = main_x + draft_w - content_pad_x

    for slot in range(draft_slots):
        if slot == 0 or slot == draft_slots - 1:
            continue
        row = draft_rows[slot - 1] if slot - 1 < len(draft_rows) else {}
        y = slot * row_h + (row_h - 34) // 2
        draw_split_row(
            draw, y,
            row.get("name", ""),
            format_abv(row.get("abv", "")),
            format_price(row.get("price", "")),
            main_x, draft_w, draft_font, white,
            abv_x, price_x, content_pad_x,
        )

    ry = 10
    wine = menu.get("wine", {})
    draw.text((right_x + content_pad_x, ry), "WINE", font=right_section_font, fill=wine_color)
    note = wine.get("note", "")
    if note:
        wine_label_w, _ = text_size(draw, "WINE", right_section_font)
        draw.text(
            (right_x + content_pad_x + wine_label_w + 12, ry + 5),
            note, font=right_small_font, fill=wine_color,
        )
    ry += 44

    wine_items = wine.get("items", [])
    wine_count = layout["wine_row_count"]
    wine_row_h = 34
    for i in range(wine_count):
        item = wine_items[i] if i < len(wine_items) else {}
        draw_name_price_row(
            draw, ry + i * wine_row_h,
            item.get("name", ""), format_price(item.get("price", "")),
            right_x, right_w, right_body_font, wine_color, content_pad_x,
        )
    ry += wine_count * wine_row_h + 10

    coffee = menu.get("coffee", {})
    draw.text((right_x + content_pad_x, ry), "COFFEE", font=right_section_font, fill=bev_color)
    coffee_price = coffee.get("price_line", "")
    if coffee_price:
        pw, _ = text_size(draw, coffee_price, right_body_font)
        draw.text(
            (right_x + right_w - pw - content_pad_x, ry + 3),
            coffee_price, font=right_body_font, fill=bev_color,
        )
    ry += 38
    bev_max_w = right_w - content_pad_x * 2
    bev_line_h = 26
    coffee_sub = coffee.get("subtext", "")
    if coffee_sub:
        for line in wrap_text(draw, coffee_sub, right_small_font, bev_max_w):
            draw.text((right_x + content_pad_x, ry), line, font=right_small_font, fill=bev_color)
            ry += bev_line_h
        ry += 2

    tea = menu.get("tea", {})
    draw.text((right_x + content_pad_x, ry), "LOOSE LEAF TEA", font=right_section_font, fill=bev_color)
    tea_price = tea.get("price_line", "")
    if tea_price:
        pw, _ = text_size(draw, tea_price, right_body_font)
        draw.text(
            (right_x + right_w - pw - content_pad_x, ry + 3),
            tea_price, font=right_body_font, fill=bev_color,
        )
    ry += 38
    varieties = tea.get("varieties", "")
    if varieties:
        for line in wrap_text(draw, varieties, right_small_font, bev_max_w):
            draw.text((right_x + content_pad_x, ry), line, font=right_small_font, fill=bev_color)
            ry += bev_line_h
        ry += 6

    cooler = menu.get("cooler_note", "")
    if cooler:
        ry += 6
        for line in wrap_text(draw, cooler, right_small_font, bev_max_w):
            draw.text((right_x + content_pad_x, ry), line, font=right_small_font, fill=yellow)
            ry += bev_line_h
        ry += 24

    food = menu.get("food", {})
    draw.text((right_x + content_pad_x, ry), "FOOD", font=right_section_font, fill=food_color)
    ry += 40

    food_items = food.get("items", [])
    food_count = layout["food_row_count"]
    for i in range(food_count):
        item = food_items[i] if i < len(food_items) else {}
        name = item.get("name", "")
        price = format_price(item.get("price", ""))
        subtext = item.get("subtext", "")
        draw.text((right_x + content_pad_x, ry), name, font=right_body_font, fill=food_color)
        if price:
            pw, _ = text_size(draw, price, right_body_font)
            draw.text(
                (right_x + right_w - pw - content_pad_x, ry),
                price, font=right_body_font, fill=food_color,
            )
        ry += 32
        if subtext:
            draw.text((right_x + content_pad_x + 8, ry), subtext, font=right_small_font, fill=food_color)
            ry += 26

    glass_note = menu.get("glass_note", "")
    if glass_note:
        gw, _ = text_size(draw, glass_note, right_small_font)
        draw.text(
            (right_x + (right_w - gw) // 2, ry + 6),
            glass_note, font=right_small_font, fill=white,
        )

    footer = menu.get("footer", {})
    fy = height - footer_h
    draw.line(
        [(left_sb_x, fy), (right_sb_x + sidebar_w, fy)],
        fill=white, width=1,
    )

    half_pour = footer.get("half_pour", "")
    if half_pour:
        draw.text(
            (main_x + 8, fy + 12),
            half_pour,
            font=load_font(root_path(config["fonts"]["fallback"]), 30, config),
            fill=white,
        )

    wifi_pw = footer.get("wifi_password", "")
    if wifi_pw:
        wifi_text = f"WIFI Password: {wifi_pw}"
        ww, _ = text_size(draw, wifi_text, footer_font)
        wifi_x = right_sb_x + sidebar_w - ww - 16
        draw.text((wifi_x, fy + 12), "WIFI Password: ", font=footer_font, fill=yellow)
        prefix_w, _ = text_size(draw, "WIFI Password: ", footer_font)
        draw.text((wifi_x + prefix_w, fy + 12), wifi_pw, font=footer_font, fill=yellow)

    newsletter = footer.get("newsletter", "")
    if newsletter:
        draw.text((main_x + 8, fy + 48), newsletter, font=footer_font, fill=yellow)

    output_path = root_path(config["output"]["tv1_menu"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, quality=95)
    print(f"Saved menu poster to {output_path}")
    return output_path


def main():
    global DEBUG, _crop_debug_counter
    parser = argparse.ArgumentParser(description="Render TV1 menu poster")
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Print sidebar font-fit and positioning diagnostics"
    )
    args = parser.parse_args()
    if args.debug:
        DEBUG = True
        _crop_debug_counter = 0
    render_menu()


if __name__ == "__main__":
    main()
