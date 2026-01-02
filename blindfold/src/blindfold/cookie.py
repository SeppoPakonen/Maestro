"""Cookie generation module for error tracking."""

import secrets


def generate_cookie() -> str:
    """
    Generate a random cookie ID in the format "0x" + 8 lowercase hex digits.
    
    Returns:
        str: Cookie ID in format "0x" + 8 hex digits (e.g. "0x12ab34cd")
    """
    value = secrets.randbits(32)
    return f"0x{value:08x}"


def validate_cookie(s: str) -> bool:
    """
    Validate if a string is a properly formatted cookie.
    
    Args:
        s: String to validate
        
    Returns:
        bool: True if valid cookie format, False otherwise
    """
    if not s.startswith("0x"):
        return False
    hex_part = s[2:]
    if len(hex_part) != 8:
        return False
    try:
        int(hex_part, 16)
        return True
    except ValueError:
        return False