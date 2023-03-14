import asyncio
from contextlib import asynccontextmanager
import functools
from typing import AsyncGenerator

import anyio
from async_timeout import timeout
from loguru import logger

from chat_client import gui


@asynccontextmanager
async def open_connection(
    host: str,
    port: int,
) -> AsyncGenerator[tuple[asyncio.StreamReader, asyncio.StreamWriter], None]:
    """Open connection to server.

    Args:
        host: server host
        port: server port
    """
    reader, writer = await asyncio.open_connection(host, port)
    try:
        yield reader, writer
    finally:
        writer.close()
        await writer.wait_closed()


async def watch_for_connection(queue: asyncio.Queue[str]):
    """Keeps track of the connection to the server.

    Args:
        queue: watchdog queue

    Raises:
        ConnectionError: connection error raise
    """
    timeout_seconds = 1
    while True:
        async with timeout(timeout_seconds) as cm:
            try:
                log_message = await queue.get()
            except (asyncio.TimeoutError, asyncio.CancelledError) as err:
                if not cm.expired:
                    raise err
                logger.warning(f'{timeout_seconds}s timeout is elapsed')
                raise ConnectionError
            else:
                logger.info(log_message)


def reconnect(func):
    """Manages reconnection to the server.

    Args:
        func:  Function controlling network connections

    Returns:
        object: decorate func
    """
    @functools.wraps(func)
    async def wrapped(*args, **kwargs):
        delay = 1
        while True:
            try:
                return await func(*args, **kwargs)
            except ConnectionError:
                queues = kwargs.get('queues')
                queues.status.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
                queues.status.put_nowait(gui.SendingConnectionStateChanged.INITIATED)
                await anyio.sleep(delay)
                delay = 3
    return wrapped
