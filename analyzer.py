from collections import defaultdict, deque
from datetime import datetime, timedelta
import threading

class analyzer:
    """Calculates real-time metrics from log entries"""
    
    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self.lock = threading.Lock()
        
        # Metrics tracking
        self.metrics = {
            'error_rate': defaultdict(int),
            'response_times': defaultdict(list),
            'request_count': defaultdict(int),
            'error_count': defaultdict(int)
        }
    
    def update_metrics(self, log_entries):
        """Update metrics with new log entries"""
        print("inside update metrics")
        with self.lock:
            for entry in log_entries:
                # Truncate timestamp to minute resolution
                minute_key = entry["timestamp"].replace(second=0, microsecond=0)
                
                # Count requests
                self.metrics['request_count'][minute_key] += 1
                
                # Track error rate
                if entry["level"] == 'ERROR':
                    self.metrics['error_count'][minute_key] += 1
                
                # Track response times
                if 'response_time' in entry["metrics"]:
                    self.metrics['response_times'][minute_key].append(
                        entry['metrics']['response_time']
                    )
    
    def get_current_metrics(self):
        """Return current calculated metrics"""
        with self.lock:
            now = datetime.now()
            window_start = now - timedelta(seconds=self.window_seconds)
            
            metrics_summary = {
                'error_rate': {},
                'avg_response_time': {},
                'request_count': {}
            }
            
            for minute, count in self.metrics['request_count'].items():
                if minute < window_start:
                    continue
                
                # Calculate error rate
                total_requests = count
                error_count = self.metrics['error_count'].get(minute, 0)
                metrics_summary['error_rate'][minute] = (error_count / total_requests) if total_requests else 0
                
                # Calculate average response time
                response_times = self.metrics['response_times'].get(minute, [])
                metrics_summary['avg_response_time'][minute] = (
                    sum(response_times) / len(response_times) if response_times else 0
                )
                
                metrics_summary['request_count'][minute] = total_requests
            
            return metrics_summary