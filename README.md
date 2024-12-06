# Distributed Log Analyzer Workflow

## Overview
This document breaks down the components, interactions, and workflow of a distributed log processing system.

## 1. Asynchronous HTTP Communication (aiohttp)

### What is aiohttp?
- **Asynchronous HTTP client/server library for Python**
- Allows non-blocking network operations
- Enables concurrent processing of multiple requests
- Uses Python's `asyncio` for efficient I/O operations

### Key Features in Our Implementation
- Workers register with Coordinator
- Coordinator distributes work chunks
- Workers send processing results back
- Supports concurrent network interactions

## 2. Component Interactions

![oie_guHh1SmDgP6j](https://github.com/user-attachments/assets/134b7620-67bf-4a4e-a9ac-57ca323163e9)

### Coordinator Responsibilities

#### 1. Worker Management
- Accept worker registrations
- Track active workers
- Monitor worker health via heartbeats
- Redistribute work if a worker fails

#### 2. Log Processing Distribution
- Split large log files into chunks
- Assign chunks to available workers
- Collect and aggregate results

### Worker Responsibilities

#### 1. Process Log Chunks
- Read assigned file segments
- Parse log entries
- Extract metrics
- Send results back to coordinator

## 3. Real-Time Metrics Analysis

### Analyzer Engine Functionality

The `Analyzer` class calculates real-time metrics through several key methods:

#### Tracking Metrics in Time Windows
```python
self.metrics = { 
    'error_rate': defaultdict(int), 
    'response_times': defaultdict(list), 
    'request_count': defaultdict(int), 
    'error_count': defaultdict(int) 
}
```

#### Calculating Metrics Dynamically
```python
def update_metrics(self, log_entries):
    for entry in log_entries:
        # Track request count
        self.metrics['request_count'][minute_key] += 1
        
        # Track error rate
        if entry.level == 'ERROR':
            self.metrics['error_count'][minute_key] += 1
        
        # Track response times
        if 'response_time' in entry.metrics:
            self.metrics['response_times'][minute_key].append(
                entry.metrics['response_time']
            )
```

#### Generating Aggregated Metrics
```python
def get_current_metrics(self):
    metrics_summary = {
        'error_rate': {},      # Errors per total requests
        'avg_response_time': {},  # Average response time
        'request_count': {}    # Requests per time window
    }
    # Calculation logic...
    return metrics_summary
```

## Workflow Diagram Explanation

1. **Worker Registration**
   - Workers send registration requests to Coordinator
   - Coordinator tracks available workers

2. **Work Distribution**
   - Coordinator reads log file
   - Splits file into chunks
   - Assigns chunks to registered workers

3. **Chunk Processing**
   - Workers read their assigned log file chunks
   - Parse log entries
   - Extract metrics using Analyzer
   - Calculate real-time metrics

4. **Result Reporting**
   - Workers send processed results back to Coordinator
   - Coordinator aggregates results from all workers

5. **Metrics Generation**
   - Analyzer continuously updates metrics
   - Provides real-time insights into log data

## Key Metrics Tracked

1. **Error Rate**
   - Percentage of error logs per time window
   - Shows system reliability

2. **Response Times**
   - Average time to process requests
   - Indicates system performance

3. **Request Count**
   - Number of requests per time window
   - Helps understand system load

## Communication Flow
```
Worker Registration: Worker → HTTP POST → Coordinator (/register)
Chunk Distribution: Coordinator → HTTP POST → Worker (/process)
Results Submission: Worker → HTTP POST → Coordinator (/results)
```

## Advantages of This Architecture

1. **Scalability**
   - Can add more workers dynamically
   - Distributes processing load

2. **Fault Tolerance**
   - Workers can fail and be replaced
   - Coordinator manages work redistribution

3. **Real-Time Processing**
   - Metrics calculated during log processing
   - Provides immediate insights

## Getting Started
```bash
# Setup project
git clone https://github.com/chainscore-hiring/log-analyzer-assessment
cd log-analyzer-assessment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start system (in separate terminals)
python coordinator.py --port 8000
python worker.py --id alice --port 8001 --coordinator http://localhost:8000
python worker.py --id bob --port 8002 --coordinator http://localhost:8000
python worker.py --id charlie --port 8003 --coordinator http://localhost:8000
```
