import argparse
import asyncio
import aiohttp  # Add this line
from aiohttp import web # type: ignore
import logging
import os
import json
from typing import Dict, List
from logEntry import LogEntry
from analyzer import analyzer
import traceback
from datetime import datetime

class Worker:
    """Processes log chunks and reports results"""
    
    def __init__(self, port: int, worker_id: str, coordinator_url: str):
        self.worker_id = worker_id
        self.coordinator_url = coordinator_url
        self.port = port
        
        self.session = None
        self.is_registered = False

        self.analyzer = analyzer()
        #self.logger = logging.getLogger(f'Worker-{worker_id}')
        #self.logger.setLevel(logging.DEBUG)
        
        # Setup logging
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        #self.logger.addHandler(handler)
    
    def start(self) -> None:
        """Start worker server"""
        print(f"Starting worker {self.worker_id} on port {self.port}...")
        
        # Use asyncio.run() to manage the event loop
        asyncio.run(self.start_server())
         
    async def start_server(self) -> None:
        """Start worker server"""
        print(f"Starting worker {self.worker_id} on port {self.port}...")
        app = web.Application()
        app.router.add_post('/process', self.process_chunk_request)
        
        await self.register_with_coordinator()
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", self.port)
        await site.start()
        
        # Add heartbeat task
        heartbeat_task = asyncio.create_task(self.send_heartbeat())
        
        # Use runner.cleanup() instead of web.run_app()
        try:
            while True:
                await asyncio.sleep(3600)  # Keep the server running
        except asyncio.CancelledError:
            await runner.cleanup()
            
    async def register_with_coordinator(self):
        """Register worker with coordinator"""
        print(f" Register with coordinator started {self.port}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f'{self.coordinator_url}/register', 
                                        json={'worker_id': self.worker_id , 'port' : self.port}) as response:
                    if response.status == 200:
                        print(f"Registered with coordinator at {self.coordinator_url}")
                    else:
                        print("Failed to register with coordinator")
        except Exception as e:
            print(f"Registration error: {e}")
            
    async def process_chunk(self, filepath: str, start: int, size: int) -> dict:
        """Process a chunk of log file and return metrics"""
        """Process a chunk of log file and return metrics"""
        print(f"Processing chunk: {filepath}, start={start}, size={size}")
        
        processed_logs = []
        
        try:
            with open(filepath, 'r') as file:
                # Move to chunk start
                file.seek(start)
                
                # Read chunk
                chunk_data = file.read(size)
                log_lines = chunk_data.split('\n')
                #print(chunk_data)
                #print(log_lines)
                for line in log_lines:
                    #print(line , "line before parsing")
                    if line.strip():
                        try:
                            log_entry = LogEntry.parse(line)
                            #print(f"logentry parsed successfully {log_entry}")
                            processed_logs.append({
                                'timestamp': log_entry["timestamp"],
                                'level': log_entry["level"],
                                'message': log_entry["message"],
                                'metrics': log_entry["metrics"],
                                'filepath': filepath
                            })
                        except ValueError as e:
                            pass
                
                # Update analyzer with processed logs
                #print("processed logs" , processed_logs)
                self.analyzer.update_metrics(processed_logs)
                #print("update metrics successult" , processed_logs)
              
                
        except Exception as e:
            print(f"Chunk processing error: {e}")
        
        #self.print_metrics()
        return processed_logs


    async def send_results(self, filepath: str, results: List[Dict]):
        """Send processing results back to coordinator"""
        try:
            async with aiohttp.ClientSession() as session:
                for result in results:
                    if isinstance(result['timestamp'], datetime):
                        result['timestamp'] = result['timestamp'].isoformat()
           
                payload = {
                    'worker_id': self.worker_id,
                    'filepath': filepath,
                    'results': results
                }
                print("payload" , payload)
                
                async with session.post(f'{self.coordinator_url}/results', json=payload ) as response:
                    if response.status == 200:
                        print("Results sent successfully")
                    else:
                        print("Failed to send results")
        except Exception as e:
            print(f"Results sending error: {e}")

    async def process_chunk_request(self, request):
        """HTTP endpoint to receive chunk processing request"""
        try:
            #print(f"Chunck received {request.json()}")
            data = await request.json()
            filepath = data['filepath']
            start = data['start']
            size = data['size']
            
            # Process chunk
            results = await self.process_chunk(filepath, start, size)
            
            # Send results back
            #print(results , "results")
            await self.send_results(filepath, results)
            
            return web.json_response({'status': 'success'})
        except Exception as e:
            print(f"Chunk processing error: {e}")
            
            exceptionTrace = traceback.format_exc()
            print(
                      f"Exception: {str(e)}"
                      f"trace: {exceptionTrace}")
            return web.json_response({'status': 'error', 'message': str(e)}, status=500)

    async def send_heartbeat(self):
        """Periodically send heartbeat to coordinator"""
        print(f"sending heartbeat to coordinator")
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    print(f"heartbeat sent to coordinator")
                    await session.post(f'{self.coordinator_url}/heartbeat', 
                                       json={'worker_id': self.worker_id})
                await asyncio.sleep(10)  # Heartbeat every 10 seconds
            except Exception as e:
                print(f"Heartbeat error: {e}")
                await asyncio.sleep(10)

    def print_metrics(self):
        """Print out current metrics after processing"""
        metrics = self.analyzer.get_current_metrics()
        #print(f"\nMetrics for Worker {self.worker_id}:")
        #print(metrics)
        #print(json.dumps(metrics, indent=2))
   

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Log Analyzer Worker")
    parser.add_argument("--port", type=int, default=8000, help="Worker port")
    parser.add_argument("--id", type=str, default="worker1", help="Worker ID")
    parser.add_argument("--coordinator", type=str, default="http://localhost:8000", help="Coordinator URL")
    args = parser.parse_args()

    worker = Worker(port=args.port, worker_id=args.id, coordinator_url=args.coordinator)
    worker.start()