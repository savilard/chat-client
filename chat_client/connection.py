import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from loguru import logger


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
    """
    while True:
        log_message = await queue.get()
        logger.info(log_message)
