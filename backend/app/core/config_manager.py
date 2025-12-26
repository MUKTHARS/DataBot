import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

CONFIG_FILE = Path(__file__).parent.parent / "db_config.json"


class ConfigManager:
    """Manages persistent configuration storage"""
    
    @staticmethod
    def save_config(config: Dict[str, Any]) -> bool:
        """Save configuration to file"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    @staticmethod
    def load_config() -> Optional[Dict[str, Any]]:
        """Load configuration from file"""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
        return None
    
    @staticmethod
    def get_current_config() -> Dict[str, Any]:
        """Get current configuration"""
        config = ConfigManager.load_config()
        if config:
            return config
        
        # Return default config if none exists
        return {
            "database_type": "postgres",
            "connection_url": "",
            "last_updated": None
        }