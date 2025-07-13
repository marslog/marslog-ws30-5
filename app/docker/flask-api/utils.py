#!/usr/bin/env python3
"""
MARSLOG-ClickHouse Utilities
Enhanced utility functions for MARSLOG with ClickHouse integration
"""

import json
import os
import bcrypt
import base64
import uuid
import subprocess
import re
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# ================================
# PATH CONFIGURATION
# ================================

# Data directory paths
DATA_DIR = Path("/app/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

USERS_FILE_PATH = DATA_DIR / "users.json"
DEVICES_FILE_PATH = DATA_DIR / "devices.json"
DEVICE_STATUS_LOG_PATH = DATA_DIR / "device_status_log.json"
LOG_PATTERNS_FILE = DATA_DIR / "log_patterns.json"

# Configuration directories
CONFIG_DIR = Path("/app/config")
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

BEATS_CONFIG_DIR = Path("/app/beats-config")
BEATS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# ================================
# USER MANAGEMENT
# ================================

def load_users() -> List[Dict]:
    """Load users from JSON file"""
    if not USERS_FILE_PATH.exists():
        default_users = [
            {
                "id": str(uuid.uuid4()),
                "username": "admin",
                "password": hash_password("Marslog@admin123"),
                "role": "admin",
                "email": "admin@marslog.local",
                "created_at": datetime.utcnow().isoformat(),
                "last_login": None,
                "active": True
            },
            {
                "id": str(uuid.uuid4()),
                "username": "marslog",
                "password": hash_password("marslog"),
                "role": "user",
                "email": "user@marslog.local",
                "created_at": datetime.utcnow().isoformat(),
                "last_login": None,
                "active": True
            }
        ]
        save_users(default_users)
        return default_users
    
    try:
        with open(USERS_FILE_PATH, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_users(users: List[Dict]) -> None:
    """Save users to JSON file"""
    try:
        with open(USERS_FILE_PATH, 'w') as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        print(f"Error saving users: {e}")
        raise

def find_user_by_username(username: str) -> Optional[Dict]:
    """Find user by username"""
    users = load_users()
    for user in users:
        if user.get('username') == username and user.get('active', True):
            return user
    return None

def find_user_by_id(user_id: str) -> Optional[Dict]:
    """Find user by ID"""
    users = load_users()
    for user in users:
        if user.get('id') == user_id and user.get('active', True):
            return user
    return None

def add_user_to_json(user_data: Dict) -> Dict:
    """Add new user to JSON file"""
    users = load_users()
    
    # Check if username already exists
    if find_user_by_username(user_data.get('username', '')):
        raise ValueError("Username already exists")
    
    # Generate user ID if not provided
    if 'id' not in user_data:
        user_data['id'] = str(uuid.uuid4())
    
    # Set default values
    user_data.setdefault('created_at', datetime.utcnow().isoformat())
    user_data.setdefault('active', True)
    user_data.setdefault('role', 'user')
    
    # Hash password if provided
    if 'password' in user_data:
        user_data['password'] = hash_password(user_data['password'])
    
    users.append(user_data)
    save_users(users)
    
    # Return user data without password
    safe_user = user_data.copy()
    safe_user.pop('password', None)
    return safe_user

def update_user_login_time(username: str) -> None:
    """Update user's last login time"""
    users = load_users()
    for user in users:
        if user.get('username') == username:
            user['last_login'] = datetime.utcnow().isoformat()
            break
    save_users(users)

# ================================
# PASSWORD MANAGEMENT
# ================================

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

# ================================
# DEVICE MANAGEMENT
# ================================

def load_devices() -> List[Dict]:
    """Load devices from JSON file"""
    if not DEVICES_FILE_PATH.exists():
        DEVICES_FILE_PATH.write_text("[]")
        return []
    
    try:
        with open(DEVICES_FILE_PATH, 'r') as f:
            devices = json.load(f)
        print(f"[utils] Loaded {len(devices)} devices")
        return devices
    except json.JSONDecodeError as e:
        print(f"[utils] JSON decode error: {e}")
        # Backup corrupted file
        backup_path = DEVICES_FILE_PATH.with_suffix('.json.bak')
        if DEVICES_FILE_PATH.exists():
            DEVICES_FILE_PATH.rename(backup_path)
        DEVICES_FILE_PATH.write_text("[]")
        return []

def save_devices(devices: List[Dict]) -> None:
    """Save devices to JSON file"""
    try:
        with open(DEVICES_FILE_PATH, 'w') as f:
            json.dump(devices, f, indent=2)
        print(f"[utils] Saved {len(devices)} devices")
    except Exception as e:
        print(f"Error saving devices: {e}")
        raise

def find_device_by_id(device_id: str) -> Optional[Dict]:
    """Find device by ID"""
    devices = load_devices()
    for device in devices:
        if device.get('id') == device_id:
            return device
    return None

def find_device_by_ip(ip_address: str) -> Optional[Dict]:
    """Find device by IP address"""
    devices = load_devices()
    for device in devices:
        if device.get('ip') == ip_address:
            return device
    return None

# ================================
# DEVICE STATUS LOGGING
# ================================

def load_device_status_log() -> List[Dict]:
    """Load device status log with 30-day retention"""
    if not DEVICE_STATUS_LOG_PATH.exists():
        DEVICE_STATUS_LOG_PATH.write_text("[]")
        return []
    
    try:
        with open(DEVICE_STATUS_LOG_PATH, 'r') as f:
            logs = json.load(f)
        return logs
    except (json.JSONDecodeError, FileNotFoundError):
        DEVICE_STATUS_LOG_PATH.write_text("[]")
        return []

def save_device_status_log(logs: List[Dict]) -> None:
    """Save device status log with automatic cleanup"""
    # Keep only last 30 days
    cutoff = datetime.utcnow().timestamp() - 30 * 24 * 60 * 60
    filtered_logs = [
        entry for entry in logs 
        if entry.get("timestamp", 0) >= cutoff
    ]
    
    try:
        with open(DEVICE_STATUS_LOG_PATH, 'w') as f:
            json.dump(filtered_logs, f, indent=2)
    except Exception as e:
        print(f"Error saving device status log: {e}")
        raise

def append_device_status_log(entry: Dict) -> None:
    """Append entry to device status log"""
    logs = load_device_status_log()
    
    # Add timestamp if not present
    if 'timestamp' not in entry:
        entry['timestamp'] = datetime.utcnow().timestamp()
    
    logs.append(entry)
    save_device_status_log(logs)

# ================================
# LOG PATTERN MANAGEMENT
# ================================

def load_log_patterns() -> Dict:
    """Load log parsing patterns"""
    if not LOG_PATTERNS_FILE.exists():
        default_patterns = {
            "syslog": {
                "pattern": r"^(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(?P<host>\S+)\s+(?P<program>\S+)(?:\[(?P<pid>\d+)\])?\s*:\s*(?P<message>.*)",
                "fields": ["timestamp", "host", "program", "pid", "message"]
            },
            "apache": {
                "pattern": r'^(?P<host>\S+)\s+\S+\s+(?P<user>\S+)\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>\S+)\s+(?P<path>\S+)\s+(?P<protocol>\S+)"\s+(?P<status>\d+)\s+(?P<size>\S+)(?:\s+"(?P<referer>[^"]*)"\s+"(?P<user_agent>[^"]*)")?',
                "fields": ["host", "user", "timestamp", "method", "path", "protocol", "status", "size", "referer", "user_agent"]
            },
            "nginx": {
                "pattern": r'^(?P<host>\S+)\s+-\s+(?P<user>\S+)\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>\S+)\s+(?P<path>\S+)\s+(?P<protocol>\S+)"\s+(?P<status>\d+)\s+(?P<size>\S+)(?:\s+"(?P<referer>[^"]*)"\s+"(?P<user_agent>[^"]*)")?',
                "fields": ["host", "user", "timestamp", "method", "path", "protocol", "status", "size", "referer", "user_agent"]
            }
        }
        save_log_patterns(default_patterns)
        return default_patterns
    
    try:
        with open(LOG_PATTERNS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_log_patterns(patterns: Dict) -> None:
    """Save log parsing patterns"""
    try:
        with open(LOG_PATTERNS_FILE, 'w') as f:
            json.dump(patterns, f, indent=2)
    except Exception as e:
        print(f"Error saving log patterns: {e}")
        raise

# ================================
# NETWORK UTILITIES
# ================================

def get_ip_info(ip_address: str) -> Dict:
    """Get information about an IP address"""
    info = {
        'ip': ip_address,
        'type': 'unknown',
        'network': None,
        'is_private': False,
        'is_loopback': False,
        'is_multicast': False
    }
    
    try:
        import ipaddress
        ip_obj = ipaddress.ip_address(ip_address)
        
        info['type'] = 'ipv4' if ip_obj.version == 4 else 'ipv6'
        info['is_private'] = ip_obj.is_private
        info['is_loopback'] = ip_obj.is_loopback
        info['is_multicast'] = ip_obj.is_multicast
        
        # Determine network type
        if ip_obj.is_loopback:
            info['network'] = 'loopback'
        elif ip_obj.is_private:
            info['network'] = 'private'
        elif ip_obj.is_multicast:
            info['network'] = 'multicast'
        else:
            info['network'] = 'public'
            
    except ValueError:
        pass
    
    return info

def validate_ip_address(ip_address: str) -> bool:
    """Validate IP address format"""
    try:
        import ipaddress
        ipaddress.ip_address(ip_address)
        return True
    except ValueError:
        return False

def validate_port(port: int) -> bool:
    """Validate port number"""
    return 1 <= port <= 65535

# ================================
# SYSTEM UTILITIES
# ================================

def get_system_info() -> Dict:
    """Get basic system information"""
    import platform
    import psutil
    
    try:
        return {
            'hostname': platform.node(),
            'platform': platform.platform(),
            'architecture': platform.architecture()[0],
            'processor': platform.processor() or "Unknown",
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'disk_usage': psutil.disk_usage('/').total,
            'boot_time': psutil.boot_time(),
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        print(f"Error getting system info: {e}")
        return {'error': str(e)}

def execute_command(command: str, timeout: int = 30) -> Dict:
    """Execute system command safely"""
    try:
        result = subprocess.run(
            command.split(),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return {
            'success': result.returncode == 0,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Command timed out'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

# ================================
# FILE UTILITIES
# ================================

def ensure_directory(path: Path) -> None:
    """Ensure directory exists"""
    path.mkdir(parents=True, exist_ok=True)

def safe_write_json(file_path: Path, data: Any) -> None:
    """Safely write JSON data to file"""
    temp_path = file_path.with_suffix('.tmp')
    try:
        with open(temp_path, 'w') as f:
            json.dump(data, f, indent=2)
        temp_path.replace(file_path)
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise e

def backup_file(file_path: Path, max_backups: int = 5) -> None:
    """Create backup of file with rotation"""
    if not file_path.exists():
        return
    
    backup_dir = file_path.parent / 'backups'
    ensure_directory(backup_dir)
    
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    backup_path = backup_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}"
    
    try:
        import shutil
        shutil.copy2(file_path, backup_path)
        
        # Cleanup old backups
        backup_files = sorted(
            backup_dir.glob(f"{file_path.stem}_*{file_path.suffix}"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        for old_backup in backup_files[max_backups:]:
            old_backup.unlink()
            
    except Exception as e:
        print(f"Error creating backup: {e}")

# ================================
# VALIDATION UTILITIES
# ================================

def validate_email(email: str) -> bool:
    """Validate email address format"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_username(username: str) -> bool:
    """Validate username format"""
    if not username or len(username) < 3:
        return False
    return re.match(r'^[a-zA-Z0-9_-]+$', username) is not None

def sanitize_string(text: str, max_length: int = 255) -> str:
    """Sanitize string input"""
    if not isinstance(text, str):
        return ""
    
    # Remove null bytes and control characters
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length]
    
    return text.strip()

# ================================
# INITIALIZATION
# ================================

def initialize_data_files() -> None:
    """Initialize all data files with defaults"""
    print("Initializing MARSLOG data files...")
    
    # Initialize users
    if not USERS_FILE_PATH.exists():
        load_users()  # This will create default users
        print("Created default users file")
    
    # Initialize devices
    if not DEVICES_FILE_PATH.exists():
        save_devices([])
        print("Created empty devices file")
    
    # Initialize device status log
    if not DEVICE_STATUS_LOG_PATH.exists():
        save_device_status_log([])
        print("Created device status log file")
    
    # Initialize log patterns
    if not LOG_PATTERNS_FILE.exists():
        load_log_patterns()  # This will create default patterns
        print("Created default log patterns file")
    
    print("Data files initialization complete")

# Initialize on import
if __name__ != '__main__':
    initialize_data_files()
