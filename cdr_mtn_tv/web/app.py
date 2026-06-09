"""Flask web app for cdr_mtn_tv — single process, no threads."""

import argparse
import json
import os
import sys
from pathlib import Path

from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from events_display.render import fetch_events  # noqa: E402
from menu_display.render import render_menu  # noqa: E402
from paths import load_config, root_path  # noqa: E402

ROLE = os.environ.get("CDR_ROLE", "editor")


def create_app(role: str = ROLE) -> Flask:
    app = Flask(__name__)
    app.config["CDR_ROLE"] = role
    config = load_config()
    app.config["CDR_CONFIG"] = config

    def role_allows(*allowed: str) -> bool:
        return role in allowed

    @app.route("/")
    def editor():
        if not role_allows("editor"):
            abort(404)
        menu_path = root_path("data", "menu.json")
        with open(menu_path, encoding="utf-8") as f:
            menu = json.load(f)
        return render_template(
            "editor.html",
            menu=menu,
            config=config,
            saved=request.args.get("saved"),
        )

    @app.route("/save", methods=["POST"])
    def save_menu():
        if not role_allows("editor"):
            abort(404)
        menu = {
            "header": request.form.get("header", ""),
            "footer": request.form.get("footer", ""),
            "rows": [],
        }
        row_count = config.get("menu_row_count", 10)
        for i in range(row_count):
            row = {}
            for col in config["menu_columns"]:
                row[col["key"]] = request.form.get(f"row_{i}_{col['key']}", "")
            menu["rows"].append(row)

        menu_path = root_path("data", "menu.json")
        with open(menu_path, "w", encoding="utf-8") as f:
            json.dump(menu, f, indent=2)
            f.write("\n")
        return redirect(url_for("editor", saved="1"))

    @app.route("/generate", methods=["POST"])
    def generate_menu():
        if not role_allows("editor"):
            abort(404)
        render_menu(config=config)
        return redirect(url_for("editor", saved="generated"))

    @app.route("/events")
    def events_page():
        if not role_allows("editor"):
            abort(404)
        streamed = []
        error = None
        try:
            raw = fetch_events(config["events_api_url"])
            for event in raw:
                title = event.get("post_title", "")
                if "streamed" in title.lower():
                    date = event.get("_EventStartDate", [""])[0]
                    streamed.append({"title": title, "date": date})
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        return render_template(
            "events.html",
            streamed_events=streamed,
            error=error,
        )

    @app.route("/tv1")
    def tv1_display():
        if not role_allows("tv1"):
            abort(404)
        return render_template(
            "display.html",
            display_name="TV1 Menu",
            image_endpoint=url_for("tv1_image"),
            refresh_seconds=config["display_refresh_seconds"],
        )

    @app.route("/tv2")
    def tv2_display():
        if not role_allows("tv2"):
            abort(404)
        return render_template(
            "display.html",
            display_name="TV2 Events",
            image_endpoint=url_for("tv2_image"),
            refresh_seconds=config["display_refresh_seconds"],
        )

    @app.route("/image/tv1")
    def tv1_image():
        if not role_allows("tv1", "editor"):
            abort(404)
        path = root_path(config["output"]["tv1_menu"])
        if not path.exists():
            abort(404)
        return send_file(path, mimetype="image/jpeg")

    @app.route("/image/tv2")
    def tv2_image():
        if not role_allows("tv2", "editor"):
            abort(404)
        path = root_path(config["output"]["tv2_events"])
        if not path.exists():
            abort(404)
        return send_file(path, mimetype="image/jpeg")

    return app


def main():
    parser = argparse.ArgumentParser(description="cdr_mtn_tv web app")
    parser.add_argument(
        "--role",
        choices=["editor", "tv1", "tv2"],
        default=ROLE,
        help="App role (editor, tv1 display, tv2 display)",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    config = load_config()
    port = args.port
    if port is None:
        port_key = args.role if args.role != "editor" else "editor"
        if args.role == "tv1":
            port_key = "tv1"
        elif args.role == "tv2":
            port_key = "tv2"
        port = config["ports"][port_key]

    app = create_app(role=args.role)
    app.run(host=args.host, port=port, threaded=False)


if __name__ == "__main__":
    main()
