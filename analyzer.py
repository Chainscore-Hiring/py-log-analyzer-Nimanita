import os
from collections import defaultdict, deque
from datetime import datetime, timedelta
import threading
import json

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
            'error_count': defaultdict(int),
            'malformed_lines': defaultdict(int)
        }
    
    def update_metrics(self, log_entries):
        """Update metrics with new log entries"""
        print("inside update metrics")
        with self.lock:
            for entry in log_entries:
                if isinstance(entry, dict):
                    # Truncate timestamp to minute resolution
                    if isinstance(entry['timestamp'], str):
                        minute_key = datetime.fromisoformat(entry['timestamp']).replace(second=0, microsecond=0)
                    else:
                        minute_key = entry['timestamp'].replace(second=0, microsecond=0)
                    
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
        
    def generate_comprehensive_metrics(self, filepath: str) -> dict:
        """Generate comprehensive metrics for a log file"""
        with self.lock:
            # Prepare the metrics dictionary
            metrics = {
                'avg_response_time': 0.0,
                'error_rate': 0.0,
                'requests_per_second': 0.0,
                'total_requests': 0,
                'malformed_lines': self.metrics.get('malformed_lines', {}).get(os.path.basename(filepath), 0)
            }
            
            # Aggregate metrics across all time
            total_response_times = []
            total_requests = 0
            total_errors = 0
            
            for minute, count in self.metrics['request_count'].items():
                total_requests += count
                
                # Collect response times
                response_times = self.metrics['response_times'].get(minute, [])
                total_response_times.extend(response_times)
                
                # Count errors
                total_errors += self.metrics['error_count'].get(minute, 0)
            
            # Calculate average response time
            if total_response_times:
                metrics['avg_response_time'] = round(sum(total_response_times) / len(total_response_times), 1)
            
            # Calculate total requests and requests per second
            metrics['total_requests'] = total_requests
            metrics['requests_per_second'] = round(total_requests / 100, 2)  # Assuming 100-second window
            
            # Calculate error rate (per 100 seconds)
            if total_requests > 0:
                metrics['error_rate'] = round((total_errors / total_requests) * 100, 1)
            
            return metrics
    
    def write_metrics_to_file(self, log_dir: str, output_file: str = 'metrics_output.json'):
        """Write metrics for all log files to a JSON file"""
        # Identify log files
        log_files = [
            f for f in os.listdir(log_dir) 
            if f.endswith('.log')
        ]
        
        # Compile metrics for each log file
        comprehensive_metrics = {}
        for log_file in log_files:
            filepath = os.path.join(log_dir, log_file)
            comprehensive_metrics[log_file] = self.generate_comprehensive_metrics(filepath)
        
        # Write to output file
        with open(output_file, 'w') as f:
            json.dump(comprehensive_metrics, f, indent=4)
        
        print(f"Metrics written to {output_file}")