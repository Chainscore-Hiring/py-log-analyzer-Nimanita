import re
from datetime import datetime
from typing import Dict, Optional, Union, Any

class LogEntry:
    def __init__(
        self,
        timestamp: datetime,
        level: str,
        message: str,
        metrics: Optional[Dict[str, float]] = None
    ):
        self.timestamp = timestamp
        self.level = level
        self.message = message
        self.metrics = metrics or {}

    @classmethod
    def parse(cls, log_line: str) -> 'LogEntry':
        """
        Parse a log line into a LogEntry object
        
        Supports multiple log formats:
        1. Standard format: 2024-01-24 10:15:32.123 INFO Request processed in 127ms
        2. JSON-like format: {"timestamp": "2024-01-24 10:15:33.001", "level": "INFO", "message": "Request processed", "duration_ms": 95}
        3. Apache/Nginx-like format: 192.168.1.1 - - [24/Jan/2024:10:15:33.125] GET /api/data HTTP/1.1 200 105ms
        """
        # Remove leading/trailing whitespace
        log_line = log_line.strip()
        
        # Try parsing as JSON-like format first
        try:
            return cls._parse_json_format(log_line)
        except (ValueError, TypeError):
            pass
        
        # Try standard timestamp format
        try:
            return cls._parse_standard_format(log_line)
        except ValueError:
            pass
        
        try:
            return cls._parse_nginx_format(log_line)
        except ValueError:
            pass
        
        # If all parsing attempts fail
        raise ValueError(f"Unable to parse log line: {log_line}")

    @classmethod
    def _parse_json_format(cls, log_line: str) -> 'LogEntry':
        print(f"parsing json format")
        """Parse JSON-like log format"""
        import json
        
        try:
            # Try parsing as JSON
            log_data = json.loads(log_line)
            
            # Parse timestamp 
            timestamp = datetime.strptime(log_data['timestamp'], '%Y-%m-%d %H:%M:%S.%f')
            
            # Extract metrics 
            metrics = {}
            for key in ['duration_ms', 'response_time']:
                if key in log_data and isinstance(log_data[key], (int, float)):
                    metrics[key] = float(log_data[key])
            
            
            return {
            'timestamp': timestamp.isoformat(),
            'level': log_data.get('level', 'UNKNOWN'),
            'message': log_data.get('message', ''),
            'metrics': metrics
        }
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise ValueError(f"Invalid JSON format: {e}")

    @classmethod
    def _parse_standard_format(cls, log_line: str) -> 'LogEntry':
        """Parse standard log format with timestamp, level, and message"""
        print(f"parsing standard format")

        # Regex to parse standard log format
        pattern = r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) (\w+) (.+)$'
        match = re.match(pattern, log_line)
        
        if not match:
            raise ValueError(f"Invalid standard log format: {log_line}")
        
        timestamp_str, level, message = match.groups()
        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
        
        # Extract metrics from message if possible
        metrics = {}
        response_time_match = re.search(r'processed in (\d+)ms', message)
        if response_time_match:
            try:
                metrics['response_time'] = float(response_time_match.group(1))
            except (AttributeError, ValueError):
                pass
        return {
            'timestamp': timestamp,
            'level': level,
            'message': message,
            'metrics': metrics
        }

    @classmethod
    def _parse_nginx_format(cls, log_line: str) -> 'LogEntry':
        
        """Parse Apache/Nginx-like log format"""
        # More flexible regex for Apache/Nginx log format
        pattern = r'.*\[([^]]+)\].*(\d+)ms'
        match = re.search(pattern, log_line)
        
        if not match:
            raise ValueError(f"Invalid Nginx/Apache log format: {log_line}")
        
        # Parse timestamp
        timestamp_str = match.group(1)
        timestamp = datetime.strptime(timestamp_str, '%d/%b/%Y:%H:%M:%S.%f')
        
        # Extract response time
        metrics = {
            'response_time': float(match.group(2))
        }
        
        return {
            'timestamp': timestamp,
            'level': 'INFO',
            'message': log_line,
            'metrics': metrics
        }