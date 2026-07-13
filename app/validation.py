from email_validator import validate_email as _validate, EmailNotValidError


def validate_email_format(email: str) -> bool:
    """Return True if *email* is syntactically valid, False otherwise."""
    try:
        _validate(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


__all__ = ["validate_email_format"]
