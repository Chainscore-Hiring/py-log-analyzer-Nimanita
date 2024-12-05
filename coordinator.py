import argparse
import asyncio
import aiohttp  # Add this line
from aiohttp import web # type: ignore
import os
import logging
import json
from typing import Dict, List, Any

class Coordinator:
    """Manages workers and aggregates results"""
    
    def __init__(self, port: int):
        print(f"Starting coordinator on port {port}")
        self.workers = {}
        self.results = {}
        self.port = port
        self.file_chunks = {}  # Tracking chunk processing status
        self.results = {}  # Aggregated results
        #self.logger = logging.getLogger('Coordinator')
        #self.logger.setLevel(logging.INFO)
        
        # Setup logging
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        #self.logger.addHandler(handler)
        
    def start(self) -> None:
        """Start coordinator server"""
        print(f"Starting coordinator on port {self.port}...")
        
        asyncio.run(self.start_server())
    
    async def start_server(self) -> None:
        """Start coordinator server"""
        print(f"Starting coordinator on port {self.port}...")
        
        app = web.Application()
        
        app.router.add_post('/register', self.register_worker)
        app.router.add_post('/results', self.receive_results)
        print(f"Router setup")
        
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", self.port)
        await site.start()
        
        # Add heartbeat task
        
        asyncio.get_event_loop().create_task(self.check_worker_heartbeats())
        
        asyncio.get_event_loop().create_task(self.process_test_logs())
        
        # Use runner.cleanup() instead of web.run_app()
        try:
            while True:
                await asyncio.sleep(3600)  # Keep the server running
        except asyncio.CancelledError:
            await runner.cleanup()
            
    async def process_test_logs(self):
        """Process test logs from test_vectors/logs directory"""
        print(f"Waiting for workers to register")
        await asyncio.sleep(40)  # Wait for workers to register
        print(f"Waiting for workers to register over")
        # Path to test logs
        log_dir = 'test_vectors/logs'
        
        # Find log files
        log_files = [
            os.path.join(log_dir, f) 
            for f in os.listdir(log_dir) 
            if f.endswith('.log')
        ]
        print(f"logfiles {log_files}")
        # Distribute work for each log file
        for filepath in log_files:
            print(f"distribute work started")
            await self.distribute_work(filepath)
    
    async def register_worker(self, request):
        """Handle worker registration"""
        print(f"Register worker {self.port} {request}...")

        data = await request.json()
        worker_id = data.get('worker_id')
        print(data , worker_id)
        if not worker_id:
            return web.json_response({'status': 'error', 'message': 'Worker ID required'}, status=400)
        
        self.workers[worker_id] = {
            'last_heartbeat': asyncio.get_event_loop().time(),
            'status': 'active',
            'port' : data.get('port')
        }
        
        print(f"Worker {worker_id} registered")
        return web.json_response({'status': 'success'})
    
    
    async def distribute_work(self, filepath: str):
        """Split file and assign chunks to workers"""
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            return

        file_size = os.path.getsize(filepath)
        num_workers = len(self.workers)
        
        if num_workers == 0:
            print("No workers available")
            return

        # Split file into chunks
        chunk_size = file_size // num_workers
        chunks = []
        print(f"{self.workers}")
        for i, worker_id in enumerate(self.workers.keys()):
            print(f"{worker_id}")
            start = i * chunk_size
            size = chunk_size if i < num_workers - 1 else file_size - start
            
            chunk = {
                'worker_id': worker_id,
                'port' : self.workers[worker_id]['port'],
                'filepath': filepath,
                'start': start,
                'size': size,
                'status': 'pending'
            }
            chunks.append(chunk)
            
        self.file_chunks[filepath] = chunks
        
        # Distribute chunks to workers
        async with aiohttp.ClientSession() as session:
            tasks = []
            for chunk in chunks:
                task = self.send_chunk_to_worker(session, chunk)
                tasks.append(task)
            
            await asyncio.gather(*tasks)

    async def send_chunk_to_worker(self, session, chunk):
        """Send log file chunk to a specific worker"""
        print(f"Sending chunk to worker {chunk}")
        worker_id = chunk['worker_id']
        port = chunk['port']
        try:
            async with session.post(f'http://localhost:{int(port)}/process', 
                                    json=chunk) as response:
                if response.status == 200:
                    print(f"Chunk sent to worker {worker_id}")
                else:
                    print(f"Failed to send chunk to worker {worker_id}")
        except Exception as e:
            print(f"Error sending chunk to worker {worker_id}: {e}")

    async def receive_results(self, request):
        """Handle results from workers"""
        data = await request.json()
        worker_id = data.get('worker_id')
        filepath = data.get('filepath')
        chunk_results = data.get('results', [])

        if not worker_id or not filepath:
            return web.json_response({'status': 'error'}, status=400)

        # Update results and chunk status
        if filepath not in self.results:
            self.results[filepath] = []
        
        self.results[filepath].extend(chunk_results)
        
        # Update chunk processing status
        for chunk in self.file_chunks.get(filepath, []):
            if chunk['worker_id'] == worker_id:
                chunk['status'] = 'completed'
        
        print(f"Received results from worker {worker_id}")
        return web.json_response({'status': 'success'})

    async def handle_worker_failure(self, worker_id: str):
        """Reassign work from failed worker"""
        print(f"Handling failure for worker {worker_id}")
        
        # Mark worker as inactive
        if worker_id in self.workers:
            self.workers[worker_id]['status'] = 'failed'
        print(f"worker failed ")
        # Find and reassign uncompleted chunks
        for filepath, chunks in self.file_chunks.items():
            for chunk in chunks:
                if chunk['worker_id'] == worker_id and chunk['status'] != 'completed':
                    # Find a new active worker
                    new_worker = next((w for w in self.workers if self.workers[w]['status'] == 'active'), None)
                    
                    if new_worker:
                        chunk['worker_id'] = new_worker
                        chunk['status'] = 'pending'
                        
                        # Attempt to redistribute chunk
                        async with aiohttp.ClientSession() as session:
                            await self.send_chunk_to_worker(session, chunk)

    async def check_worker_heartbeats(self):
        """Periodically check worker heartbeats"""
        print(f"Checking worker heartbeat")
        while True:
            current_time = asyncio.get_event_loop().time()

            for worker_id, worker_info in list(self.workers.items()):
                print(f"Heartbeat received {worker_id} {worker_info}")
                if current_time - worker_info['last_heartbeat'] > 30:  # 30 seconds timeout
                    await self.handle_worker_failure(worker_id)
            
            await asyncio.sleep(10)  # Check every 10 seconds
            
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Log Analyzer Coordinator")
    parser.add_argument("--port", type=int, default=8000, help="Coordinator port")
    args = parser.parse_args()

    coordinator = Coordinator(port=args.port)
    coordinator.start()
