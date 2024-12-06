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
            'error_rate': defaultdict(lambda: defaultdict(int)),
            'response_times': defaultdict(lambda: defaultdict(list)),
            'request_count': defaultdict(lambda: defaultdict(int)),
            'error_count': defaultdict(lambda: defaultdict(int)),
            'malformed_lines': defaultdict(int),
            #'total_count2' : defaultdict(int)
        }
    
    
    def update_metrics(self, log_entries):
        """Update metrics with new log entries"""
        with self.lock:
            print(f"logentries {log_entries}")

            for entry in log_entries:
                if isinstance(entry, dict):
                    # Ensure we have a filepath or use a default
                    filepath = entry.get('filepath', 'unknown')
                    filename = os.path.basename(filepath)
                    
                    # Truncate timestamp to minute resolution
                    if isinstance(entry['timestamp'], str):
                        minute_key = datetime.fromisoformat(entry['timestamp']).replace(second=0, microsecond=0)
                    else:
                        minute_key = entry['timestamp'].replace(second=0, microsecond=0)
                    
                    # Count requests per file
                    self.metrics['request_count'][filename][minute_key] += 1
                    #self.metrics['total_count2'][filename] +=1
                    # Track error rate per file
                    if entry["level"] == 'ERROR':
                        self.metrics['error_count'][filename][minute_key] += 1
                    
                    # Track response times per file
                    if 'response_time' in entry["metrics"]:
                        self.metrics['response_times'][filename][minute_key].append(
                            entry['metrics']['response_time']
                        )    
                
            print("Current Metrics State:")
            for metric_name, metric_data in self.metrics.items():
                print(f"\n{metric_name}:")
                for filename, file_data in metric_data.items():
                    print(f"  {filename}:")
                    print(f"    {file_data}")
                    
                    
    def get_current_metrics(self):
        """Return current calculated metrics"""
        with self.lock:
            now = datetime.now()
            window_start = now - timedelta(seconds=self.window_seconds)
            
            metrics_summary = {
                'error_rate': {},
                'avg_response_time': {},
                'request_count': {},
                'requests_per_second': {}
            }
            
            # Calculate metrics for each file
            for filename in set(self.metrics['request_count'].keys()):
                metrics_summary['error_rate'][filename] = {}
                metrics_summary['avg_response_time'][filename] = {}
                metrics_summary['request_count'][filename] = {}
                metrics_summary['requests_per_second'][filename] = {}
                
                for minute, count in self.metrics['request_count'][filename].items():
                    if minute < window_start:
                        continue
                    
                    # Calculate error rate
                    total_requests = count
                    error_count = self.metrics['error_count'][filename].get(minute, 0)
                    error_rate = (error_count / total_requests) * 100 if total_requests else 0
                    metrics_summary['error_rate'][filename][minute] = round(error_rate, 2)
                    
                    # Calculate average response time
                    response_times = self.metrics['response_times'][filename].get(minute, [])
                    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
                    metrics_summary['avg_response_time'][filename][minute] = round(avg_response_time, 2)
                    
                    # Request count and requests per second
                    metrics_summary['request_count'][filename][minute] = total_requests
                    metrics_summary['requests_per_second'][filename][minute] = round(total_requests / 60, 2)
            
            return metrics_summary
        
    def generate_comprehensive_metrics(self, filepath: str) -> dict:
        """Generate comprehensive metrics for a specific log file"""
        with self.lock:
            filename = os.path.basename(filepath)
            
            # Prepare the metrics dictionary
            metrics = {
                'avg_response_time': 0.0,
                'error_rate': 0.0,
                'requests_per_second': 0.0,
                'total_requests': 0,
                'malformed_lines': self.metrics['malformed_lines'].get(filename, 0)
            }
            
            # Aggregate metrics for this specific file
            total_response_times = []
            total_requests = 0
            total_errors = 0
            
            for minute, count in self.metrics['request_count'][filename].items():
                total_requests += count
                
                # Collect response times
                response_times = self.metrics['response_times'][filename].get(minute, [])
                total_response_times.extend(response_times)
                
                # Count errors
                total_errors += self.metrics['error_count'][filename].get(minute, 0)
            
            # Calculate average response time
            if total_response_times:
                metrics['avg_response_time'] = round(sum(total_response_times) / len(total_response_times), 2)
            
            # Calculate total requests and requests per second
            metrics['total_requests'] = total_requests
            metrics['requests_per_second'] = round(total_requests / self.window_seconds, 2)
            #metrics['total_count2'] = self.metrics['total_count2'][filename]
            # Calculate error rate 
            if total_requests > 0:
                metrics['error_rate'] = round((total_errors / total_requests) * 100, 2)
            
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