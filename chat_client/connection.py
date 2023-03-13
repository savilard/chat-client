import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from async_timeout import timeout
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
    timeout_seconds = 1
    while True:
        async with timeout(timeout_seconds) as cm:
            try:
                log_message = await queue.get()
            except (asyncio.TimeoutError, asyncio.CancelledError) as err:
                if not cm.expired:
                    raise err
                logger.warning(f'{timeout_seconds}s timeout is elapsed')

            else:
                logger.info(log_message)
