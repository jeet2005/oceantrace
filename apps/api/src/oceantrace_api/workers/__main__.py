from oceantrace_api.storage.rq_job_queue import RQJobQueue
from rq import Worker

if __name__ == "__main__":
    job_queue = RQJobQueue()
    worker = Worker(job_queue._queue, connection=job_queue._redis)
    worker.work()