import logging

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from .models import ImportRecord
from .import_service import ImportService

logger = logging.getLogger(__name__)

import_bp = Blueprint("import", __name__)


@import_bp.route("/ping")
def ping():
    return {"blueprint": "import", "status": "alive"}


def _get_service():
    return ImportService(current_user.id)


@import_bp.route("/start", methods=["POST"])
@login_required
def start_import():
    data = request.get_json(silent=True) or {}
    source = data.get("source")
    raw_data = data.get("raw_data")

    if not source or raw_data is None:
        return jsonify({"error": "source and raw_data are required"}), 400

    service = _get_service()
    record = service.process_import(source, raw_data)
    return jsonify(
        {
            "record_id": record.id,
            "status": record.status,
            "normalized_data": record.normalized_data,
            "confidence_scores": record.confidence_scores,
            "error_message": record.error_message,
        }
    ), 201


@import_bp.route("/linkedin", methods=["POST"])
@login_required
def import_linkedin():
    data = request.get_json(silent=True) or {}
    raw_text = data.get("raw_text")

    if not raw_text:
        return jsonify({"error": "raw_text is required"}), 400

    if not raw_text.strip():
        return jsonify({"error": "raw_text is empty"}), 400

    logger.info("LinkedIn import requested: user=%s text_length=%d", current_user.id, len(raw_text))

    service = _get_service()
    record = service.process_import("linkedin", raw_text)

    logger.info(
        "LinkedIn import complete: record_id=%s status=%s pi=%s skills=%d exp=%d edu=%d",
        record.id,
        record.status,
        (record.normalized_data or {}).get("personal_info", {}),
        len((record.normalized_data or {}).get("skills", [])),
        len((record.normalized_data or {}).get("experience", [])),
        len((record.normalized_data or {}).get("education", [])),
    )

    if record.status == "failed":
        logger.error("LinkedIn import failed: %s", record.error_message)

    return jsonify(
        {
            "record_id": record.id,
            "status": record.status,
            "normalized_data": record.normalized_data,
            "confidence_scores": record.confidence_scores,
            "error_message": record.error_message,
        }
    ), 201 if record.status == "completed" else 422


@import_bp.route("/github", methods=["POST"])
@login_required
def import_github():
    data = request.get_json(silent=True) or {}
    username = data.get("username")

    if not username:
        return jsonify({"error": "username is required"}), 400

    service = _get_service()
    record = service.process_import("github", username)
    return jsonify(
        {
            "record_id": record.id,
            "status": record.status,
            "normalized_data": record.normalized_data,
            "confidence_scores": record.confidence_scores,
            "error_message": record.error_message,
        }
    ), 201


@import_bp.route("/resume/upload", methods=["POST"])
@login_required
def upload_resume():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    text = ""
    try:
        if file.filename.lower().endswith(".pdf"):
            try:
                import PyPDF2

                reader = PyPDF2.PdfReader(file)
                text = "".join(page.extract_text() or "" for page in reader.pages)
            except ImportError:
                import pdfplumber

                with pdfplumber.open(file) as pdf:
                    text = "".join(page.extract_text() or "" for page in pdf.pages)
        elif file.filename.lower().endswith(".docx"):
            from docx import Document

            doc = Document(file)
            text = "\n".join(p.text for p in doc.paragraphs)
        else:
            text = file.read().decode("utf-8", errors="replace")
    except Exception as e:
        return jsonify({"error": f"Failed to extract text: {str(e)}"}), 400

    service = _get_service()
    record = service.process_import("resume", text)
    return jsonify(
        {
            "record_id": record.id,
            "status": record.status,
            "normalized_data": record.normalized_data,
            "confidence_scores": record.confidence_scores,
            "error_message": record.error_message,
        }
    ), 201


@import_bp.route("/portfolio", methods=["POST"])
@login_required
def import_portfolio():
    data = request.get_json(silent=True) or {}
    url = data.get("url")

    if not url:
        return jsonify({"error": "url is required"}), 400

    service = _get_service()
    record = service.process_import("portfolio", url)
    return jsonify(
        {
            "record_id": record.id,
            "status": record.status,
            "normalized_data": record.normalized_data,
            "confidence_scores": record.confidence_scores,
            "error_message": record.error_message,
        }
    ), 201


@import_bp.route("/backup", methods=["POST"])
@login_required
def import_backup():
    data = request.get_json(silent=True) or {}
    backup_data = data.get("data")

    if not backup_data:
        return jsonify({"error": "data is required"}), 400

    service = _get_service()
    record = service.process_import("backup", backup_data)
    return jsonify(
        {
            "record_id": record.id,
            "status": record.status,
            "normalized_data": record.normalized_data,
            "confidence_scores": record.confidence_scores,
            "error_message": record.error_message,
        }
    ), 201


@import_bp.route("/status/<int:record_id>", methods=["GET"])
@login_required
def get_status(record_id):
    record = ImportRecord.query.filter_by(id=record_id, user_id=current_user.id).first()
    if not record:
        return jsonify({"error": "Import record not found"}), 404

    return jsonify(
        {
            "record_id": record.id,
            "source": record.source,
            "status": record.status,
            "confidence_scores": record.confidence_scores,
            "error_message": record.error_message,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }
    ), 200


@import_bp.route("/<int:record_id>/confirm", methods=["PUT"])
@login_required
def confirm_import(record_id):
    record = ImportRecord.query.filter_by(id=record_id, user_id=current_user.id).first()
    if not record:
        return jsonify({"error": "Import record not found"}), 404

    data = request.get_json(silent=True) or {}
    normalized = data.get("normalized_data")
    if normalized:
        record.normalized_data = normalized

    service = _get_service()
    service._build_profile(record)
    service._update_resume(record)

    record.status = "completed"
    from datetime import datetime, timezone

    record.updated_at = datetime.now(timezone.utc)
    from app.extensions import db

    db.session.commit()

    return jsonify(
        {"message": "Import confirmed and saved", "record_id": record.id}
    ), 200


@import_bp.route("/result/<int:record_id>", methods=["GET"])
@login_required
def get_result(record_id):
    record = ImportRecord.query.filter_by(id=record_id, user_id=current_user.id).first()
    if not record:
        return jsonify({"error": "Import record not found"}), 404

    return jsonify(
        {
            "record_id": record.id,
            "source": record.source,
            "status": record.status,
            "normalized_data": record.normalized_data,
            "confidence_scores": record.confidence_scores,
            "import_version": record.import_version,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }
    ), 200
