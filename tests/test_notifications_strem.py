"""Unit tests for notifications ConnectionManager (strem)."""
import asyncio

from notifications.strem import ConnectionManager


def _run(coro):
    return asyncio.run(coro)


def test_connect_creates_queue():
    manager = ConnectionManager()
    queue = _run(manager.connect("user-1"))
    assert queue is not None
    assert isinstance(queue, asyncio.Queue)
    assert "user-1" in manager.active_connections
    assert len(manager.active_connections["user-1"]) == 1
    assert manager.active_connections["user-1"][0] is queue


def test_connect_multiple_queues_same_user():
    manager = ConnectionManager()
    q1 = _run(manager.connect("user-1"))
    q2 = _run(manager.connect("user-1"))
    assert len(manager.active_connections["user-1"]) == 2
    assert q1 is not q2


def test_disconnect_removes_queue():
    manager = ConnectionManager()
    queue = _run(manager.connect("user-1"))
    manager.disconnect("user-1", queue)
    assert len(manager.active_connections["user-1"]) == 0


def test_disconnect_one_of_many():
    manager = ConnectionManager()
    q1 = _run(manager.connect("user-1"))
    q2 = _run(manager.connect("user-1"))
    manager.disconnect("user-1", q1)
    assert len(manager.active_connections["user-1"]) == 1
    assert manager.active_connections["user-1"][0] is q2


def test_broadcast_to_user_delivers_to_all_queues():
    manager = ConnectionManager()
    q1 = _run(manager.connect("user-1"))
    q2 = _run(manager.connect("user-1"))
    data = {"event": "unread_count", "unread_count": 3}
    _run(manager.broadcast_to_user("user-1", data))

    assert q1.get_nowait() == data
    assert q2.get_nowait() == data


def test_broadcast_to_nonexistent_user_no_op():
    manager = ConnectionManager()
    _run(manager.connect("user-1"))
    _run(manager.broadcast_to_user("user-2", {"x": 1}))
    assert manager.active_connections["user-1"][0].empty()


def test_broadcast_empty_connections_no_error():
    manager = ConnectionManager()
    _run(manager.broadcast_to_user("no-such-user", {"event": "test"}))
