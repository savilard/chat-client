import asyncio
from contextlib import asynccontextmanager
import functools
import socket
from tkinter import messagebox
from typing import AsyncGenerator

import anyio
from async_timeout import timeout
from loguru import logger

from chat_client.exceptions import TkAppClosedError


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


async def watch_for_connection(queue: asyncio.Queue[str], timeout_seconds=3):
    """Keeps track of the connection to the server.

    Args:
        queue: watchdog queue
        timeout_seconds: connection timeout in seconds

    Raises:
        ConnectionError: connection error raise
    """
    while True:
        async with timeout(timeout_seconds) as cm:
            try:
                log_message = await queue.get()
            except (asyncio.TimeoutError, asyncio.CancelledError) as err:
                if not cm.expired:
                    raise err
                logger.warning('Тайм-аут истек')
                raise ConnectionError
            else:
                logger.info(log_message)


def reconnect(delay=1, retries=30, backoff=1.4):
    """Manages reconnection to the server."""

    def wrap(func):
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            _delay, _retries = delay, retries
            while _retries > 0:
                try:
                    return await func(*args, **kwargs)
                except (ConnectionError, anyio.ExceptionGroup, socket.gaierror):
                    await anyio.sleep(delay)
                    _retries -= 1
                    _delay *= backoff

            messagebox.showerror('Ошибка', 'Отсутствует соединение с сервером')
            raise TkAppClosedError

        return wrapped

    return wrap
