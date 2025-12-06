"""
Task Queue - Async Background Task Processing

Decouples webhook handlers from heavy LLM processing to prevent H12 timeouts.
Implements fire-and-forget pattern with load shedding.

Architecture:
- In-memory asyncio.Queue (can be replaced with Redis/Celery later)
- Background worker loop
- Load shedding when queue exceeds threshold
- Graceful shutdown support
"""
import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    """Task types for processing"""

    PROCESS_MESSAGE = "process_message"
    PROCESS_DISCOVERY = "process_discovery"
    PROCESS_DIAGNOSIS = "process_diagnosis"
    GENERATE_QUESTIONS = "generate_questions"


@dataclass
class Task:
    """Task data structure"""

    task_id: str
    task_type: TaskType
    payload: Dict[str, Any]
    user_id: str
    channel_id: str
    created_at: float
    retries: int = 0
    max_retries: int = 2


class TaskQueue:
    """
    Async task queue for background processing.

    Prevents webhook H12 timeouts by:
    1. Queuing LLM-heavy work immediately
    2. Processing in background worker
    3. Load shedding when queue overflows
    4. Sending fallback messages when needed
    """

    # Queue size thresholds
    QUEUE_WARN_THRESHOLD = 500
    QUEUE_SHED_THRESHOLD = 800
    QUEUE_REJECT_THRESHOLD = 1000

    def __init__(self, max_workers: int = 5):
        """
        Initialize task queue.

        Args:
            max_workers: Number of concurrent worker tasks
        """
        self.queue = asyncio.Queue(maxsize=self.QUEUE_REJECT_THRESHOLD)
        self.max_workers = max_workers
        self.workers = []
        self.running = False
        self.stats = {
            "total_queued": 0,
            "total_processed": 0,
            "total_failed": 0,
            "total_shed": 0,
        }

        # 🚨 CRITICAL FIX: Deduplication and concurrency control
        self.processed_task_ids = set()  # Track completed task IDs
        self.in_flight_task_ids = set()  # Track currently processing task IDs
        self.task_lock = asyncio.Lock()  # Lock for deduplication checks

        logger.info(f"✅ Task queue initialized (max_workers={max_workers})")

    async def start(self):
        """Start background worker tasks"""
        if self.running:
            logger.warning("Task queue already running")
            return

        self.running = True

        # Start worker tasks
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker_loop(worker_id=i))
            self.workers.append(worker)

        logger.info(f"✅ Started {self.max_workers} worker tasks")

    async def stop(self):
        """Stop background workers gracefully"""
        logger.info("Stopping task queue...")
        self.running = False

        # Wait for workers to finish
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)

        logger.info("✅ Task queue stopped")

    async def enqueue(
        self,
        task_type: TaskType,
        payload: Dict[str, Any],
        user_id: str,
        channel_id: str,
    ) -> bool:
        """
        Enqueue a task for background processing with deduplication.

        Args:
            task_type: Type of task
            payload: Task payload data
            user_id: User ID
            channel_id: Channel ID

        Returns:
            True if queued successfully, False if shed/rejected/duplicate
        """
        import time
        import hashlib

        # 🚨 CRITICAL FIX: Generate deterministic task_id from message_id (not random UUID)
        # This enables deduplication of identical webhook events
        message = payload.get("message", {})
        message_id = message.get("id")

        if message_id:
            # Use message_id as deterministic key
            task_id = f"{channel_id}:{message_id}"
        else:
            # Fallback: hash of payload content
            payload_hash = hashlib.md5(str(payload).encode()).hexdigest()[:8]
            task_id = f"{channel_id}:{payload_hash}"

        # 🚨 CRITICAL FIX: Check for duplicates (already processed or in-flight)
        async with self.task_lock:
            if task_id in self.processed_task_ids:
                logger.warning(f"⚠️ Duplicate task detected (already processed): {task_id}")
                return True  # Return True to avoid error message (already handled)

            if task_id in self.in_flight_task_ids:
                logger.warning(f"⚠️ Duplicate task detected (currently processing): {task_id}")
                return True  # Return True to avoid error message (being processed)

            # Mark as in-flight
            self.in_flight_task_ids.add(task_id)

        # Check queue size for load shedding
        queue_size = self.queue.qsize()

        if queue_size >= self.QUEUE_REJECT_THRESHOLD:
            logger.error(
                f"🚨 Queue FULL ({queue_size}/{self.QUEUE_REJECT_THRESHOLD}) - REJECTING task"
            )
            self.stats["total_shed"] += 1
            # Remove from in-flight since we're not actually queuing it
            async with self.task_lock:
                self.in_flight_task_ids.discard(task_id)
            await self._send_overload_message(user_id, channel_id)
            return False

        if queue_size >= self.QUEUE_SHED_THRESHOLD:
            logger.warning(
                f"⚠️ Queue overloaded ({queue_size}/{self.QUEUE_SHED_THRESHOLD}) - shedding task"
            )
            self.stats["total_shed"] += 1
            async with self.task_lock:
                self.in_flight_task_ids.discard(task_id)
            await self._send_overload_message(user_id, channel_id)
            return False

        if queue_size >= self.QUEUE_WARN_THRESHOLD:
            logger.warning(
                f"⚠️ Queue approaching capacity ({queue_size}/{self.QUEUE_WARN_THRESHOLD})"
            )

        # Create task
        task = Task(
            task_id=task_id,  # 🚨 CRITICAL FIX: Use deterministic ID
            task_type=task_type,
            payload=payload,
            user_id=user_id,
            channel_id=channel_id,
            created_at=time.time(),
        )

        # Enqueue
        try:
            await self.queue.put(task)
            self.stats["total_queued"] += 1
            logger.info(
                f"✅ Task queued: {task.task_id} (type={task_type}, queue_size={queue_size + 1})"
            )
            return True
        except asyncio.QueueFull:
            logger.error(f"🚨 Queue full - rejecting task")
            self.stats["total_shed"] += 1
            async with self.task_lock:
                self.in_flight_task_ids.discard(task_id)
            await self._send_overload_message(user_id, channel_id)
            return False

    async def _worker_loop(self, worker_id: int):
        """Background worker loop - processes tasks from queue"""
        logger.info(f"Worker {worker_id} started")

        while self.running:
            try:
                # Wait for task (with timeout to check running flag)
                try:
                    task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                # Process task
                logger.info(
                    f"[Worker {worker_id}] Processing task {task.task_id} (type={task.task_type})"
                )

                try:
                    await self._process_task(task)
                    self.stats["total_processed"] += 1
                    logger.info(
                        f"[Worker {worker_id}] ✅ Task {task.task_id} completed"
                    )

                    # 🚨 CRITICAL FIX: Mark task as processed and remove from in-flight
                    async with self.task_lock:
                        self.in_flight_task_ids.discard(task.task_id)
                        self.processed_task_ids.add(task.task_id)

                        # Prevent memory leak: limit processed_task_ids size
                        if len(self.processed_task_ids) > 10000:
                            # Remove oldest 20% of entries
                            to_remove = list(self.processed_task_ids)[:2000]
                            self.processed_task_ids.difference_update(to_remove)
                            logger.debug(f"🧹 Trimmed processed_task_ids cache ({len(to_remove)} removed)")

                except Exception as e:
                    logger.error(
                        f"[Worker {worker_id}] ❌ Task {task.task_id} failed: {e}",
                        exc_info=True,
                    )
                    self.stats["total_failed"] += 1

                    # Retry logic
                    if task.retries < task.max_retries:
                        task.retries += 1
                        logger.info(
                            f"[Worker {worker_id}] Retrying task {task.task_id} (attempt {task.retries}/{task.max_retries})"
                        )
                        # Keep in in_flight_task_ids during retry
                        await self.queue.put(task)
                    else:
                        logger.error(
                            f"[Worker {worker_id}] Task {task.task_id} exhausted retries"
                        )
                        # Remove from in-flight after final failure
                        async with self.task_lock:
                            self.in_flight_task_ids.discard(task.task_id)
                            self.processed_task_ids.add(task.task_id)  # Mark as processed (failed)

                        await self._send_error_message(
                            task.user_id, task.channel_id, task.task_type
                        )

                finally:
                    self.queue.task_done()

            except Exception as e:
                logger.error(f"[Worker {worker_id}] Unexpected error: {e}", exc_info=True)

        logger.info(f"Worker {worker_id} stopped")

    async def _process_task(self, task: Task):
        """
        Process a task based on its type.

        This is the main dispatch logic for different task types.
        """
        if task.task_type == TaskType.PROCESS_MESSAGE:
            await self._process_message_task(task)

        elif task.task_type == TaskType.PROCESS_DISCOVERY:
            await self._process_discovery_task(task)

        elif task.task_type == TaskType.PROCESS_DIAGNOSIS:
            await self._process_diagnosis_task(task)

        elif task.task_type == TaskType.GENERATE_QUESTIONS:
            await self._process_generate_questions_task(task)

        else:
            logger.error(f"Unknown task type: {task.task_type}")

    async def _process_message_task(self, task: Task):
        """
        Process a message.new event.

        This is the main webhook processing logic, moved to background.
        """
        from ..routes.ai_webhooks_v3 import handle_new_message_background

        payload = task.payload
        await handle_new_message_background(payload)

    async def _process_discovery_task(self, task: Task):
        """Process discovery question generation"""
        # TODO: Implement discovery-specific processing
        logger.info(f"Processing discovery task: {task.task_id}")

    async def _process_diagnosis_task(self, task: Task):
        """Process diagnosis generation"""
        # TODO: Implement diagnosis-specific processing
        logger.info(f"Processing diagnosis task: {task.task_id}")

    async def _process_generate_questions_task(self, task: Task):
        """Process ChatGPT-style question generation"""
        # TODO: Implement question generation
        logger.info(f"Processing question generation task: {task.task_id}")

    async def _send_overload_message(self, user_id: str, channel_id: str):
        """Send overload message when queue is full"""
        try:
            from ..services.stream_bot import get_bot

            bot = get_bot()
            bot.send_ai_message(
                channel_id=channel_id,
                persona="tenant",
                text="We're experiencing high volume right now. Your request has been noted and we'll respond shortly. Thank you for your patience!",
                metadata={"type": "overload", "actionable": False},
            )
        except Exception as e:
            logger.error(f"Failed to send overload message: {e}", exc_info=True)

    async def _send_error_message(
        self, user_id: str, channel_id: str, task_type: TaskType
    ):
        """Send error message when task fails after retries"""
        try:
            from ..services.stream_bot import get_bot

            bot = get_bot()
            bot.send_ai_message(
                channel_id=channel_id,
                persona="tenant",
                text="I'm having trouble processing your request right now. Please try rephrasing or try again in a moment.",
                metadata={"type": "error", "task_type": task_type, "actionable": False},
            )
        except Exception as e:
            logger.error(f"Failed to send error message: {e}", exc_info=True)

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        return {
            "queue_size": self.queue.qsize(),
            "max_size": self.QUEUE_REJECT_THRESHOLD,
            "workers": self.max_workers,
            "running": self.running,
            "stats": self.stats,
            "utilization_pct": (self.queue.qsize() / self.QUEUE_REJECT_THRESHOLD) * 100,
        }


# Singleton instance
_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """Get singleton instance of TaskQueue"""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue(max_workers=5)
    return _task_queue


async def start_task_queue():
    """Start the task queue (call on app startup)"""
    queue = get_task_queue()
    await queue.start()


async def stop_task_queue():
    """Stop the task queue (call on app shutdown)"""
    queue = get_task_queue()
    await queue.stop()
