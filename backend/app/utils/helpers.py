import json
import re
from typing import Any, Dict, List, Optional
from datetime import datetime, date
import hashlib
import urllib.parse


def generate_session_id() -> str:
    """Generate unique session ID"""
    return hashlib.md5(f"{datetime.now().timestamp()}".encode()).hexdigest()[:12]


def format_timestamp(dt: datetime) -> str:
    """Format timestamp for display"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format currency amount"""
    if currency == "USD":
        return f"${amount:,.2f}"
    elif currency == "EUR":
        return f"€{amount:,.2f}"
    elif currency == "GBP":
        return f"£{amount:,.2f}"
    else:
        return f"{amount:,.2f} {currency}"


def format_large_number(number: int) -> str:
    """Format large numbers with K, M, B suffixes"""
    if number >= 1_000_000_000:
        return f"{number/1_000_000_000:.1f}B"
    elif number >= 1_000_000:
        return f"{number/1_000_000:.1f}M"
    elif number >= 1_000:
        return f"{number/1_000:.1f}K"
    else:
        return f"{number:,}"


def safe_json_dumps(data: Any) -> str:
    """Safely dump data to JSON with datetime handling"""
    def json_serializer(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    
    return json.dumps(data, default=json_serializer, indent=2)


def sanitize_query_string(query: str) -> str:
    """Sanitize query string for security"""
    # Remove comments
    query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
    query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
    
    # Remove multiple spaces
    query = re.sub(r'\s+', ' ', query).strip()
    
    return query


def extract_parameters(query: str) -> Dict[str, Any]:
    """Extract parameters from query string"""
    params = {}
    
    # Look for date parameters
    date_matches = re.findall(r'(\d{4}-\d{2}-\d{2})', query)
    if date_matches:
        params["dates"] = date_matches
    
    # Look for numeric parameters
    num_matches = re.findall(r'\b(\d+)\b', query)
    if num_matches:
        params["numbers"] = [int(n) for n in num_matches]
    
    # Look for string parameters
    str_matches = re.findall(r"'([^']+)'", query)
    if str_matches:
        params["strings"] = str_matches
    
    return params


def calculate_percentage(part: float, whole: float) -> float:
    """Calculate percentage"""
    if whole == 0:
        return 0.0
    return (part / whole) * 100


def format_duration(seconds: float) -> str:
    """Format duration in seconds to readable string"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split list into chunks"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """Merge two dictionaries recursively"""
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def get_nested_value(obj: Dict, path: str, default: Any = None) -> Any:
    """Get nested value from dictionary using dot notation"""
    keys = path.split('.')
    current = obj
    
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    
    return current


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to maximum length"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def encode_database_url(url: str) -> str:
    """Encode special characters in database URL"""
    if not url:
        return url
    
    # Parse the URL
    if "://" in url:
        protocol, rest = url.split("://", 1)
        if "@" in rest:
            # Extract user info and the rest
            userinfo, hostinfo = rest.split("@", 1)
            
            # Parse userinfo to encode password
            if ":" in userinfo:
                username, password = userinfo.split(":", 1)
                # Encode the password
                password = urllib.parse.quote(password, safe='')
                userinfo = f"{username}:{password}"
            
            # Reconstruct the URL
            url = f"{protocol}://{userinfo}@{hostinfo}"
    
    # Ensure postgresql URLs use asyncpg for async operations
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://")
    
    return url    