from queue import Queue
from threading import Thread, Lock
import time
from concurrent.futures import ThreadPoolExecutor
import logging
import asyncio
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SummarizationQueue:
    def __init__(self, max_workers=10):
        self.tasks = {}
        self.results = {}
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        logger.info(f"Initialized SummarizationQueue with {max_workers} workers")

    def add_task(self, task_id, future):
        """Add a task to the queue and set up callback to store result."""
        with self.lock:
            logger.info(f"Adding task {task_id} to queue")
            self.tasks[task_id] = future
            
            def store_result(future):
                try:
                    result = future.result()
                    with self.lock:
                        logger.info(f"Task {task_id} completed successfully")
                        self.results[task_id] = {
                            'status': 'completed',
                            'result': result
                        }
                except Exception as e:
                    logger.error(f"Task {task_id} failed: {str(e)}")
                    with self.lock:
                        self.results[task_id] = {
                            'status': 'failed',
                            'error': str(e)
                        }
                finally:
                    with self.lock:
                        if task_id in self.tasks:
                            del self.tasks[task_id]

            future.add_done_callback(store_result)

    def get_result(self, task_id):
        """Get the result of a task."""
        with self.lock:
            if task_id in self.results:
                logger.info(f"Found result for task {task_id}")
                return self.results[task_id]
            elif task_id in self.tasks:
                logger.info(f"Task {task_id} still processing")
                return {'status': 'processing'}
            else:
                logger.warning(f"Task {task_id} not found in results")
                return None

    def cleanup(self):
        """Clean up completed tasks."""
        with self.lock:
            current_time = time.time()
            # Keep results for 1 hour
            self.results = {k: v for k, v in self.results.items() 
                          if current_time - float(k.split('-')[0]) < 3600}

    def shutdown(self):
        """Shutdown the queue and workers"""
        for _ in range(self.executor._max_workers):
            self.executor.submit(lambda: None)  # Poison pill
        self.executor.shutdown(wait=True)

# Global queue instance
summarization_queue = SummarizationQueue(max_workers=10) 