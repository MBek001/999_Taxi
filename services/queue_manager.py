import asyncio
import logging
from typing import Callable, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class QueueManager:
    def __init__(self, max_concurrent: int = 5, delay_between_tasks: float = 0.5):
        self.max_concurrent = max_concurrent
        self.delay_between_tasks = delay_between_tasks
        self.queue = asyncio.Queue()
        self.running = False
        self.active_tasks = 0

    async def add_task(self, func: Callable, *args, **kwargs):
        await self.queue.put((func, args, kwargs))
        logger.debug(f"Task added to queue. Queue size: {self.queue.qsize()}")

    async def start(self):
        self.running = True
        logger.info("Queue manager started")

        while self.running:
            if self.queue.empty():
                await asyncio.sleep(1)
                continue

            if self.active_tasks >= self.max_concurrent:
                await asyncio.sleep(0.1)
                continue

            try:
                func, args, kwargs = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                asyncio.create_task(self._execute_task(func, args, kwargs))
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in queue manager: {e}")

    async def _execute_task(self, func: Callable, args: tuple, kwargs: dict):
        self.active_tasks += 1
        try:
            if asyncio.iscoroutinefunction(func):
                await func(*args, **kwargs)
            else:
                func(*args, **kwargs)

            await asyncio.sleep(self.delay_between_tasks)
        except Exception as e:
            logger.error(f"Error executing task {func.__name__}: {e}")
        finally:
            self.active_tasks -= 1

    async def stop(self):
        self.running = False
        logger.info("Queue manager stopped")

    def get_queue_size(self) -> int:
        return self.queue.qsize()

    def get_active_tasks(self) -> int:
        return self.active_tasks

queue_manager = QueueManager()
