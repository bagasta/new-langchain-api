import uuid
import re
import html
from typing import Any, Dict, List


def generate_uuid() -> str:
    """Generate a UUID string"""
    return str(uuid.uuid4())


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def sanitize_input(text: str) -> str:
    """Sanitize text input to prevent XSS"""
    return html.escape(text)


def truncate_string(text: str, max_length: int = 100) -> str:
    """Truncate string to specified length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """Flatten a nested dictionary"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two dictionaries recursively"""
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def remove_empty_values(d: Dict[str, Any]) -> Dict[str, Any]:
    """Remove empty values from dictionary"""
    return {k: v for k, v in d.items() if v is not None and v != "" and v != []}


def format_duration(ms: int) -> str:
    """Format duration in milliseconds to human readable format"""
    if ms < 1000:
        return f"{ms}ms"
    elif ms < 60000:
        return f"{ms/1000:.1f}s"
    else:
        minutes = ms // 60000
        seconds = (ms % 60000) // 1000
        return f"{minutes}m {seconds}s"


def safe_get(d: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    """Safely get nested dictionary values"""
    current = d
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current