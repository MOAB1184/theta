import os
from rq import Worker, Queue
from rq.connections import Connection
import redis
from transcription_tasks import process_transcription_job

# If you have any app-specific setup, import it here
# For Flask, you may need to set up the app context

listen = ['default']

redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
conn = redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(list(map(str, listen)))
        worker.work() 