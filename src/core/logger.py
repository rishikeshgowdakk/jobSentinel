import logging
import sys
import asyncio

# Global queue for real-time log streaming via WebSockets
log_queue = asyncio.Queue()

class QueueHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            # Use call_soon_threadsafe if logs come from other threads, 
            # though we are mostly async.
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.call_soon_threadsafe(log_queue.put_nowait, {"type": "log", "message": msg})
        except Exception:
            pass

def setup_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(message)s'
    )
    
    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # WebSocket handler
    qh = QueueHandler()
    qh.setFormatter(formatter)
    logger.addHandler(qh)
    
    return logger

logger = setup_logger("SentinelApply")
