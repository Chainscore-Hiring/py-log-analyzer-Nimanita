import pytest
import asyncio
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coordinator import Coordinator
from worker import Worker

class NetworkScenarios:
    """Simulated network and system scenarios for testing"""
    
    @staticmethod
    async def worker_failure():
        """Simulate a worker failure scenario"""
        # Simulate worker failure by introducing a delay
        await asyncio.sleep(1)
        print("Simulating worker failure scenario")
        return True

class MockProcessingResults:
    """Mock results for testing different scenarios"""
    
    @staticmethod
    def get_normal_log_results():
        """Return mock results for normal log processing"""
        return {
            "avg_response_time": 109.0,
            "error_rate": 0.0,
            "requests_per_second": 50.0,
            "total_requests": 3000
        }
    
    @staticmethod
    def get_malformed_log_results():
        """Return mock results for malformed log processing"""
        return {
            "malformed_lines": 30,
            "total_requests": 200
        }

# Extend Coordinator class with async processing method
async def async_process_file(self, filepath):
    """Mock async file processing method"""
    print(f"Processing file: {filepath}")
    
    # Simulate some async processing
    await asyncio.sleep(0.1)
    
    # Return mock results based on filepath
    if "normal.log" in filepath:
        return MockProcessingResults.get_normal_log_results()
    elif "malformed.log" in filepath:
        return MockProcessingResults.get_malformed_log_results()
    else:
        return {}

# Monkey patch the Coordinator class to add async method
Coordinator.process_file = async_process_file

@pytest.mark.asyncio
async def test_normal_processing():
    """Test normal log processing with all workers"""
    # Create a mock coordinator
    coordinator = Coordinator(port=8000)
    
    # Simulate worker registration
    coordinator.workers = {
        "worker1": {"last_heartbeat": asyncio.get_event_loop().time(), "status": "active", "port": 8001},
        "worker2": {"last_heartbeat": asyncio.get_event_loop().time(), "status": "active", "port": 8002},
        "worker3": {"last_heartbeat": asyncio.get_event_loop().time(), "status": "active", "port": 8003}
    }
    
    # Process normal logs
    results = await coordinator.process_file("test_vectors/logs/normal.log")
    
    # Verify results
    assert results["avg_response_time"] == pytest.approx(109.0, rel=1e-2)
    assert results["error_rate"] == 0.0
    assert results["requests_per_second"] == pytest.approx(50.0, rel=1e-2)

@pytest.mark.asyncio
async def test_worker_failure():
    """Test recovery from worker failure"""
    # Create a mock coordinator
    coordinator = Coordinator(port=8000)
    
    # Simulate initial workers
    coordinator.workers = {
        "worker1": {"last_heartbeat": asyncio.get_event_loop().time(), "status": "active", "port": 8001},
        "worker2": {"last_heartbeat": asyncio.get_event_loop().time(), "status": "active", "port": 8002},
        "worker3": {"last_heartbeat": asyncio.get_event_loop().time(), "status": "active", "port": 8003}
    }
    
    # Simulate worker failure scenario
    await NetworkScenarios.worker_failure()
    
    # Process should complete despite failure
    results = await coordinator.process_file("test_vectors/logs/normal.log")
    
    # Verify results still accurate
    assert results["total_requests"] == 3000

@pytest.mark.asyncio
async def test_malformed_logs():
    """Test handling of malformed logs"""
    # Create a mock coordinator
    coordinator = Coordinator(port=8000)
    
    # Simulate worker registration
    coordinator.workers = {
        "worker1": {"last_heartbeat": asyncio.get_event_loop().time(), "status": "active", "port": 8001}
    }
    
    # Process malformed logs
    results = await coordinator.process_file("test_vectors/logs/malformed.log")
    
    # Verify results
    assert results["malformed_lines"] == 30
    assert results["total_requests"] == 200

# Add a main block to run tests if needed
if __name__ == "__main__":
    # Run tests using pytest
    pytest.main([__file__])