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
    def __init__(self):
        self.queue = Queue()
        self.results = {}
        self.lock = Lock()
        self.thread_pool = ThreadPoolExecutor(max_workers=10)
        self.cleanup_thread = Thread(target=self._cleanup_old_results, daemon=True)
        self.cleanup_thread.start()
        logger.info("SummarizationQueue initialized with 10 workers")

    def add_task(self, task_id, future):
        with self.lock:
            self.results[task_id] = {
                'status': 'processing',
                'future': future,
                'timestamp': time.time()
            }
            logger.info(f"Task {task_id} added to queue with future {future}")

    def get_result(self, task_id):
        with self.lock:
            if task_id not in self.results:
                logger.warning(f"Task {task_id} not found in results")
                return None
            result = self.results[task_id]
            if result['status'] == 'processing':
                if result['future'].done():
                    try:
                        result['result'] = result['future'].result()
                        result['status'] = 'completed'
                        logger.info(f"Task {task_id} completed with result: {result['result']}")
                    except Exception as e:
                        result['status'] = 'failed'
                        result['error'] = str(e)
                        logger.error(f"Task {task_id} failed with error: {e}")
            return result

    def _cleanup_old_results(self):
        while True:
            time.sleep(3600)  # Cleanup every hour
            with self.lock:
                current_time = time.time()
                for task_id, result in list(self.results.items()):
                    if current_time - result['timestamp'] > 3600:  # Remove results older than 1 hour
                        del self.results[task_id]
                        logger.info(f"Cleaned up old task {task_id}")

    def shutdown(self):
        """Shutdown the queue and workers"""
        for _ in range(self.thread_pool._max_workers):
            self.queue.put((None, None))  # Poison pill
        self.thread_pool.shutdown(wait=True)

# Global queue instance
summarization_queue = SummarizationQueue() 