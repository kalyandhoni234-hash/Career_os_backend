"""PDF generation engine with graceful fallback and health checks.

Primary engine: WeasyPrint (Linux/Render — requires GTK/Pango/Cairo native libs).
If the native dependencies are missing, the engine returns a clear error rather
than crashing with an opaque traceback.
"""

import logging

logger = logging.getLogger(__name__)

_weasyprint_available = False
_weasyprint_error = None


def _init_engine():
    global _weasyprint_available, _weasyprint_error
    try:
        from weasyprint import HTML  # noqa: F401
        _weasyprint_available = True
        _weasyprint_error = None
    except ImportError as exc:
        _weasyprint_available = False
        _weasyprint_error = f"WeasyPrint package not installed: {exc}"
    except OSError as exc:
        _weasyprint_available = False
        _weasyprint_error = str(exc)


_init_engine()


def html_to_pdf(html_string, filename_hint="resume"):
    """Render an HTML string to PDF bytes.

    Returns (pdf_bytes | None, error_message | None).
    """
    global _weasyprint_available, _weasyprint_error
    if not _weasyprint_available:
        return None, (
            "PDF generation is not available because a required native library "
            "could not be loaded.\n\n"
            f"Details: {_weasyprint_error}\n\n"
            "On Linux (Render):\n"
            "  sudo apt install libpango-1.0-0 libpangocairo-1.0-0 "
            "libgdk-pixbuf2.0-0 libffi-dev libcairo2\n\n"
            "On macOS:\n"
            "  brew install pango gdk-pixbuf libffi\n\n"
            "On Windows:\n"
            "  Install GTK from https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer\n"
            "  Or use WSL for development."
        )

    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html_string).write_pdf()
        return pdf_bytes, None
    except OSError as exc:
        _weasyprint_available = False
        _weasyprint_error = str(exc)
        msg = (
            "PDF generation failed because a required native library could not "
            f"be loaded.\n\nDetails: {exc}\n\n"
            "See /api/resume/pdf-health for troubleshooting information."
        )
        return None, msg
    except Exception as exc:
        logger.exception("PDF generation failed unexpectedly")
        return None, f"PDF generation failed: {exc}"


def get_status():
    """Return dict with engine health information."""
    return {
        "available": _weasyprint_available,
        "engine": "weasyprint",
        "error": _weasyprint_error,
        "hint_for_windows": (
            "Install GTK from: "
            "https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer"
        ),
        "hint_for_linux": "sudo apt install libpango-1.0-0 libpangocairo-1.0-0 "
        "libgdk-pixbuf2.0-0 libffi-dev libcairo2",
        "hint_for_macos": "brew install pango gdk-pixbuf libffi",
    }
