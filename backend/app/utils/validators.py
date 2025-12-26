import re
from typing import Any, Dict, List, Optional
from datetime import datetime
import ipaddress


def validate_email(email: str) -> bool:
    """Validate email address format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """Validate URL format"""
    pattern = r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?::\d+)?(?:/[-\w@:%+.~#?&/=]*)?$'
    return bool(re.match(pattern, url))


def validate_date(date_str: str, format: str = "%Y-%m-%d") -> bool:
    """Validate date string format"""
    try:
        datetime.strptime(date_str, format)
        return True
    except ValueError:
        return False


def validate_database_url(url: str, db_type: str) -> bool:
    """Validate database connection URL"""
    if db_type == "postgres":
        return url.startswith("postgresql://") or url.startswith("postgres://")
    elif db_type == "mysql":
        return url.startswith("mysql://") or url.startswith("mysql+aiomysql://")
    elif db_type == "mongodb":
        return url.startswith("mongodb://") or url.startswith("mongodb+srv://")
    return False


def validate_query_safety(query: str) -> bool:
    """Validate query for safety"""
    dangerous_keywords = [
        "DROP", "DELETE", "TRUNCATE", "ALTER", 
        "CREATE", "INSERT", "UPDATE", "GRANT", 
        "REVOKE", "EXEC", "EXECUTE"
    ]
    
    query_upper = query.upper()
    
    for keyword in dangerous_keywords:
        if re.search(rf'\b{keyword}\b', query_upper):
            return False
    
    # Check for multiple statements
    if query_upper.count(';') > 1:
        return False
    
    return True


def validate_json(data: str) -> bool:
    """Validate JSON string"""
    try:
        import json
        json.loads(data)
        return True
    except:
        return False


def validate_ip_address(ip: str) -> bool:
    """Validate IP address"""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def validate_port(port: int) -> bool:
    """Validate port number"""
    return 1 <= port <= 65535


def validate_limit(limit: int, max_limit: int = 1000) -> bool:
    """Validate query limit"""
    return 1 <= limit <= max_limit


def validate_timeframe(timeframe: str) -> bool:
    """Validate timeframe string"""
    valid_timeframes = ["day", "week", "month", "quarter", "year"]
    return timeframe in valid_timeframes


def validate_parameters(params: Dict[str, Any], required: List[str]) -> bool:
    """Validate required parameters"""
    for param in required:
        if param not in params:
            return False
    
    return True