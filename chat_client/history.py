import asyncio
from contextlib import suppress

import aiofiles


async def save_msgs(
    filepath: str,
    current_time: str,
    queue: asyncio.Queue[str],
) -> None:
    """Save chat message to history file.

    Args:
        filepath: path to history file
        current_time: current time
        queue: history update queue
    """
    while True:
        chat_message = await queue.get()
        async with aiofiles.open(filepath, mode='a') as history_file:
            await history_file.writelines(f'[{current_time}] {chat_message}')


async def read_msgs(
    filepath: str,
    messages_queue: asyncio.Queue[str],
) -> None:
    """Read messages from file.

    Args:
        filepath: path to file with messages
        messages_queue: messages queue
    """
    with suppress(FileNotFoundError):
        async with aiofiles.open(filepath, mode='r') as history_file:
            async for line in history_file:
                messages_queue.put_nowait(str(line))
