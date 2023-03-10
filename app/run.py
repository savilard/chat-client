import asyncio
import datetime
from contextlib import asynccontextmanager
from functools import wraps
from typing import NoReturn

import aiofiles
import typer

import gui


def get_current_time() -> str:
    """Get current time in str format.

    Returns:
        object: formatted current time
    """
    now_datetime = datetime.datetime.now()
    return now_datetime.strftime('%d.%m.%Y %H:%M:%S')  # noqa: WPS323


def run_async(func):
    """Used for asynchronous run with click arguments.

    https://github.com/tiangolo/typer/issues/88#issuecomment-889486850

    Args:
        func: decoratable asynchronous function

    Returns:
        object: decorate asynchronous function
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@asynccontextmanager
async def open_connection(host, port):
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


async def read_msgs_from_server(
    host: str,
    port: int,
    messages_queue: asyncio.Queue[str],
    history_update_queue: asyncio.Queue[str],
) -> NoReturn:
    """Reads messages from the server.

    Args:
        host: server host
        port: server listen port
        messages_queue: messages queue
        history_update_queue: queue for saving message to file
    """
    async with open_connection(host, port) as (reader, writer):
        while True:
            chat_message = await reader.readline()
            decoded_chat_message = chat_message.decode()
            messages_queue.put_nowait(decoded_chat_message)
            history_update_queue.put_nowait(decoded_chat_message)


async def read_msgs_from_file(filepath: str, messages_queue: asyncio.Queue[str]) -> None:
    """Read messages from file.

    Args:
        filepath: path to file with messages
        messages_queue: messages queue
    """
    async with aiofiles.open(filepath, mode='r') as history_file:
        history_file_content = await history_file.read()
        messages_queue.put_nowait(history_file_content)


async def save_msgs(
    filepath: str,
    current_time: str,
    queue: asyncio.Queue[str],
) -> NoReturn:
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


@run_async
async def main(
    host: str = typer.Option(
        default='minechat.dvmn.org',
        help='Minechat host',
        envvar='SERVER_HOST',
    ),
    listen_server_port: int = typer.Option(
        default=5000,
        help='Minechat listen port',
        envvar='LISTEN_SERVER_PORT',
    ),
    writing_server_port: int = typer.Option(
        default=5050,
        help='Minechat writing port',
        envvar='WRITING_SERVER_PORT',
    ),
    token: str = typer.Option(
        None,
        help='Your token',
        envvar='MINECHAT_TOKEN',
    ),
    history_file_path: str = typer.Option(
        default='minechat.history',
        help='Path to file with history of minechat',
        envvar='HISTORY_FILE_PATH',
    ),
) -> None:
    """Entry point.

    Args:
        host: minechat server host
        listen_server_port: port to receive messages
        writing_server_port: port for sending messages
        token: token to access the server
        history_file_path: Path to file with history of minechat
    """
    messages_queue: asyncio.Queue[str] = asyncio.Queue()
    sending_queue: asyncio.Queue[str] = asyncio.Queue()
    status_updates_queue: asyncio.Queue[str] = asyncio.Queue()
    history_updates_queue: asyncio.Queue[str] = asyncio.Queue()

    await read_msgs_from_file(filepath=history_file_path, messages_queue=messages_queue)

    await asyncio.gather(
        gui.draw(messages_queue, sending_queue, status_updates_queue),
        read_msgs_from_server(
            host=host,
            port=listen_server_port,
            messages_queue=messages_queue,
            history_update_queue=history_updates_queue,
        ),
        save_msgs(
            filepath=history_file_path,
            current_time=get_current_time(),
            queue=history_updates_queue,
        ),
    )


if __name__ == '__main__':
    typer.run(main)
