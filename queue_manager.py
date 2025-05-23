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
    def __init__(self, max_workers=3):
        self.queue = Queue()
        self.results = {}
        self.lock = Lock()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._start_workers()
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()

    def _start_workers(self):
        """Start worker threads to process the queue"""
        for _ in range(self.executor._max_workers):
            self.executor.submit(self._worker)

    def _worker(self):
        """Worker function that processes items from the queue"""
        while True:
            try:
                task_id, task = self.queue.get()
                if task is None:  # Poison pill
                    break
                
                try:
                    # Update status to processing
                    with self.lock:
                        self.results[task_id].update({
                            'status': 'processing',
                            'started_at': time.time(),
                            'progress': 0
                        })
                    
                    # Run the task
                    result = task['func'](*task['args'], **task['kwargs'])
                    
                    with self.lock:
                        self.results[task_id].update({
                            'status': 'completed',
                            'result': result,
                            'error': None,
                            'completed_at': time.time()
                        })
                except Exception as e:
                    logger.error(f"Error processing task {task_id}: {str(e)}")
                    with self.lock:
                        self.results[task_id].update({
                            'status': 'failed',
                            'result': None,
                            'error': str(e),
                            'failed_at': time.time()
                        })
                finally:
                    self.queue.task_done()
            except Exception as e:
                logger.error(f"Worker error: {str(e)}")
                time.sleep(1)  # Prevent tight loop on errors

    def add_task(self, task_id, func, *args, **kwargs):
        """Add a task to the queue"""
        with self.lock:
            self.results[task_id] = {
                'status': 'queued',
                'result': None,
                'error': None,
                'created_at': time.time(),
                'progress': 0
            }
        self.queue.put((task_id, {
            'func': func,
            'args': args,
            'kwargs': kwargs
        }))
        return task_id

    def get_result(self, task_id):
        """Get the result of a task"""
        with self.lock:
            result = self.results.get(task_id)
            if result and result['status'] == 'processing':
                # Calculate progress based on time elapsed
                elapsed = time.time() - result.get('started_at', time.time())
                # Assume average processing time of 15 seconds
                progress = min(95, int((elapsed / 15) * 100))
                result['progress'] = progress
            return result

    def _cleanup_loop(self):
        """Background thread to clean up old results"""
        while True:
            try:
                self.cleanup_old_results()
                time.sleep(300)  # Run cleanup every 5 minutes
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    def cleanup_old_results(self, max_age_seconds=3600):
        """Clean up old results to prevent memory bloat"""
        current_time = time.time()
        with self.lock:
            for task_id in list(self.results.keys()):
                created_at = self.results[task_id].get('created_at', 0)
                if current_time - created_at > max_age_seconds:
                    del self.results[task_id]

    def shutdown(self):
        """Shutdown the queue and workers"""
        for _ in range(self.executor._max_workers):
            self.queue.put((None, None))  # Poison pill
        self.executor.shutdown(wait=True)

# Global queue instance
summarization_queue = SummarizationQueue(max_workers=10) 