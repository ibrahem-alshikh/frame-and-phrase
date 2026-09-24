import io

from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.exceptions import HTTPException

from batch import build_template_workbook, read_mapping, run_batch
from config import load_settings, save_settings
from imaging import generate_image, FONT_CHOICES, CANVAS_SIZE

app = Flask(__name__)
# Generous limits: a whole folder of photos for /batch/run can easily be
# well over the previous 20 MB cap, or contain more files than Werkzeug's
# default 1000-part cap — both used to fail the upload outright.
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB uploads
app.config["MAX_FORM_PARTS"] = 10000


@app.errorhandler(HTTPException)
def handle_http_exception(e):
    # Without this, Flask's default error pages are HTML — and any
    # frontend code doing `await res.json()` blows up with a confusing
    # "Unexpected token '<'" instead of a readable message.
    message = e.description or e.name
    if e.code == 413:
        message = "حجم الملفات المرفوعة أكبر من الحد المسموح به (500 ميجابايت). قسّم المجموعة إلى دفعات أصغر."
    return jsonify({"error": message}), e.code


@app.errorhandler(Exception)
def handle_unexpected_exception(e):
    return jsonify({"error": f"حدث خطأ غير متوقع في الخادم: {e}"}), 500


def settings_from_form(form, current):
    """Build a settings dict from form fields, falling back to `current` values."""
    def g(key, cast, section, field):
        raw = form.get(key)
        if raw is None or raw == "":
            return current[section][field]
        try:
            return cast(raw)
        except (TypeError, ValueError):
            return current[section][field]

    return {
        "box": {
            "x": g("box_x", int, "box", "x"),
            "y": g("box_y", int, "box", "y"),
            "width": g("box_width", int, "box", "width"),
            "height": g("box_height", int, "box", "height"),
            "border_width": g("box_border_width", int, "box", "border_width"),
            "border_color": g("box_border_color", str, "box", "border_color"),
            "corner_radius": g("box_corner_radius", int, "box", "corner_radius"),
            "fit_mode": g("box_fit_mode", str, "box", "fit_mode"),
            "background_color": g("box_background_color", str, "box", "background_color"),
        },
        "text": {
            "x": g("text_x", int, "text", "x"),
            "y": g("text_y", int, "text", "y"),
            "width": g("text_width", int, "text", "width"),
            "height": g("text_height", int, "text", "height"),
            "font": g("text_font", str, "text", "font"),
            "font_size": g("text_font_size", int, "text", "font_size"),
            "color": g("text_color", str, "text", "color"),
            "align": g("text_align", str, "text", "align"),
            "valign": g("text_valign", str, "text", "valign"),
            "line_spacing": g("text_line_spacing", float, "text", "line_spacing"),
        },
    }


def build_image_response(image_file, text, settings):
    if image_file is None or image_file.filename == "":
        return jsonify({"error": "الرجاء اختيار صورة"}), 400
    if not text or not text.strip():
        return jsonify({"error": "الرجاء إدخال الكلمات"}), 400

    img = generate_image(image_file, text, settings)
    buf = io.BytesIO()
    img.save(buf, format="PNG")  # keep the alpha channel: transparent PNG background
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route("/")
def index():
    settings = load_settings()
    return render_template("simple.html", fonts=FONT_CHOICES, settings=settings)


@app.route("/generate", methods=["POST"])
def generate():
    current = load_settings()
    settings = settings_from_form(request.form, current)
    return build_image_response(request.files.get("image"), request.form.get("text", ""), settings)


@app.route("/admin")
def admin():
    settings = load_settings()
    return render_template(
        "admin.html",
        settings=settings,
        fonts=FONT_CHOICES,
        canvas=CANVAS_SIZE,
    )


@app.route("/admin/preview", methods=["POST"])
def admin_preview():
    current = load_settings()
    settings = settings_from_form(request.form, current)
    return build_image_response(request.files.get("image"), request.form.get("text", ""), settings)


@app.route("/admin/save", methods=["POST"])
def admin_save():
    current = load_settings()
    settings = settings_from_form(request.form, current)
    save_settings(settings)
    return jsonify({"ok": True})


@app.route("/admin/reset", methods=["POST"])
def admin_reset():
    from config import DEFAULT_SETTINGS
    save_settings(DEFAULT_SETTINGS)
    return jsonify({"ok": True})


@app.route("/batch")
def batch_page():
    return render_template("batch.html")


@app.route("/batch/template.xlsx")
def batch_template():
    buf = build_template_workbook()
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="نموذج_الكلمات.xlsx",
    )


@app.route("/batch/run", methods=["POST"])
def batch_run():
    mapping_file = request.files.get("mapping")
    image_files = request.files.getlist("images")

    if mapping_file is None or mapping_file.filename == "":
        return jsonify({"error": "الرجاء رفع ملف الكلمات (Excel أو CSV)"}), 400
    if not image_files:
        return jsonify({"error": "الرجاء اختيار الصور"}), 400

    try:
        mapping = read_mapping(mapping_file)
    except Exception as e:
        return jsonify({"error": f"تعذرت قراءة ملف الكلمات: {e}"}), 400

    if not mapping:
        return jsonify({"error": "لم يتم العثور على أي صفوف صالحة في ملف الكلمات"}), 400

    settings = load_settings()
    report = run_batch(image_files, mapping, settings)
    return jsonify(report)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
