import asyncio
from typing import Dict, Any

class ConnectionManager:
    def __init__(self):
        # Maps user_id to a list of asyncio Queues
        self.active_connections: Dict[str, list[asyncio.Queue]] = {}

    async def connect(self, user_id: str):
        queue = asyncio.Queue()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(queue)
        return queue

    def disconnect(self, user_id: str, queue: asyncio.Queue):
        self.active_connections[user_id].remove(queue)

    async def broadcast_to_user(self, user_id: str, data: Any):
        if user_id in self.active_connections:
            for queue in self.active_connections[user_id]:
                await queue.put(data)

manager = ConnectionManager()
