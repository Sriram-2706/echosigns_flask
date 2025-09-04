import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import LoginManager, login_required, current_user
from werkzeug.utils import secure_filename

from .auth import auth_bp
from .database import db, User, History, ContactMessage
from .models.text2isl import Text2ISL
from .models.asr import asr_file_vosk, VOSK_OK

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)

# FIX: templates and static are in frontend/
TEMPLATES_DIR = os.path.join(PROJECT_DIR, "frontend", "templates")
STATIC_DIR    = os.path.join(PROJECT_DIR, "frontend", "static")

UPLOAD_DIR    = os.path.join(STATIC_DIR, "uploads")
VIDEOS_DIR    = os.path.join(STATIC_DIR, "isl_videos")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
app.secret_key = os.environ.get("SECRET_KEY", "replace-this-with-a-random-secret")

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(PROJECT_DIR, 'echosigns.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Login manager
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Blueprints
app.register_blueprint(auth_bp)

# Text→ISL engine
text2isl_engine = Text2ISL(video_root=VIDEOS_DIR, max_phrase_len=3)

# --------- Pages ----------
@app.route("/")
def home_page():
    return render_template("home.html")

@app.route("/about")
def about_page():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact_page():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip()
        message = (request.form.get("message") or "").strip()
        if not name or not email or not message:
            flash("Please fill all fields.", "error")
        else:
            cm = ContactMessage(
                name=name, email=email, message=message,
                user_id=current_user.id if current_user.is_authenticated else None
            )
            db.session.add(cm)
            db.session.commit()
            flash("Thanks! We received your message.", "success")
            return redirect(url_for("contact_page"))
    return render_template("contact.html")

@app.route("/dashboard")
@login_required
def dashboard_page():
    items = History.query.filter_by(user_id=current_user.id).order_by(History.id.desc()).all()
    return render_template("dashboard.html", history=items)

# --------- Converter / Animation ----------
@app.route("/animation", methods=["GET", "POST"])
@login_required
def animation_page():
    text_display = ""
    keywords_list = []
    playlist_files = []
    lang = "en"
    if request.method == "POST":
        mode = request.form.get("mode", "text")      # text|speech_upload
        lang = request.form.get("lang", "en")        # en|hi

        if mode == "text":
            text = (request.form.get("sen") or "").strip()
            if not text:
                flash("Enter some text.", "error")
                return render_template("animation.html", text=text_display, words=keywords_list, files=playlist_files, lang=lang)
            text_display = text
            keywords_list, playlist_files = text2isl_engine.text_to_playlist(text, lang=lang)

        elif mode == "speech_upload":
            f = request.files.get("audio_file")
            if not f or f.filename == "":
                flash("Upload a WAV/WEBM/OGG audio file.", "error")
                return render_template("animation.html", text=text_display, words=keywords_list, files=playlist_files, lang=lang)
            fname = secure_filename(f.filename)
            save_path = os.path.join(UPLOAD_DIR, fname)
            f.save(save_path)

            try:
                recognized = asr_file_vosk(save_path, language=("hi-IN" if lang=="hi" else "en-IN")) if VOSK_OK else ""
            except Exception as e:
                recognized = ""
                flash(f"ASR error: {e}", "error")

            if not recognized:
                flash("No transcription produced (configure VOSK for offline ASR).", "error")
                return render_template("animation.html", text=text_display, words=keywords_list, files=playlist_files, lang=lang)

            text_display = recognized
            keywords_list, playlist_files = text2isl_engine.text_to_playlist(recognized, lang=lang)

        # Save history
        if playlist_files:
            hist = History(
                user_id=current_user.id,
                input_text=text_display,
                lang=lang,
                output_videos="|".join(playlist_files)
            )
            db.session.add(hist)
            db.session.commit()

    return render_template("animation.html", text=text_display, words=keywords_list, files=playlist_files, lang=lang, vosk_ok=VOSK_OK)

# ---- Live mic capture ----
@app.route("/api/asr/live/start", methods=["POST"])
@login_required
def asr_live_start():
    rec_id = str(uuid.uuid4())
    folder = os.path.join(UPLOAD_DIR, "live")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{rec_id}.webm")
    open(path, "wb").close()
    return jsonify({"rec_id": rec_id})

@app.route("/api/asr/live/append/<rec_id>", methods=["POST"])
@login_required
def asr_live_append(rec_id):
    folder = os.path.join(UPLOAD_DIR, "live")
    path = os.path.join(folder, f"{rec_id}.webm")
    if not os.path.isfile(path):
        return jsonify({"error": "unknown rec id"}), 400
    chunk = request.data
    with open(path, "ab") as f:
        f.write(chunk)
    return jsonify({"ok": True})

@app.route("/api/asr/live/stop/<rec_id>", methods=["POST"])
@login_required
def asr_live_stop(rec_id):
    lang = request.args.get("lang", "en")
    folder = os.path.join(UPLOAD_DIR, "live")
    webm_path = os.path.join(folder, f"{rec_id}.webm")
    if not os.path.isfile(webm_path):
        return jsonify({"error": "unknown rec id"}), 400

    if not VOSK_OK:
        return jsonify({"text": "", "note": "VOSK not configured. Use upload with WAV or set VOSK_MODEL_EN/HI."})

    return jsonify({"text": "", "note": "Transcoding from WEBM to WAV not implemented. Upload WAV on Animation page."})

# ---- Static serving for uploaded preview ----
@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)

# ---- CLI ----
@app.cli.command("init-db")
def init_db_cmd():
    with app.app_context():
        db.create_all()
        print("Initialized database.")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
