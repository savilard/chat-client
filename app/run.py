import asyncio
from contextlib import asynccontextmanager
from functools import wraps
from typing import NoReturn

import typer

import gui


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


async def read_msgs(host: str, port: int, queue: asyncio.Queue[str]) -> NoReturn:
    """Reads messages from the server.

    Args:
        host: server host
        port: server listen port
        queue: messages queue
    """
    async with open_connection(host, port) as (reader, writer):
        while True:
            chat_message = await reader.readline()
            queue.put_nowait(chat_message.decode())


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

    await asyncio.gather(
        gui.draw(messages_queue, sending_queue, status_updates_queue),
        read_msgs(host=host, port=listen_server_port, queue=messages_queue),
    )


if __name__ == '__main__':
    typer.run(main)
