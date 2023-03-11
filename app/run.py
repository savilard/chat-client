import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from dataclasses import field
import datetime
from functools import wraps
import json
import sys
from tkinter import messagebox
from typing import AsyncGenerator

import aiofiles
from exceptions import InvalidTokenError
import gui
from loguru import logger
import typer


@dataclass
class Queues:
    """Project queues."""

    messages: asyncio.Queue[str] = field(default=asyncio.Queue())
    sending: asyncio.Queue[str] = field(default=asyncio.Queue())
    status: asyncio.Queue[
        gui.SendingConnectionStateChanged | gui.ReadConnectionStateChanged | gui.NicknameReceived
    ] = field(default=asyncio.Queue())
    history: asyncio.Queue[str] = field(default=asyncio.Queue())
    watchdog: asyncio.Queue[str] = field(default=asyncio.Queue())


def get_current_time() -> str:
    """Get current time in str format.

    Returns:
        object: formatted current time
    """
    now_datetime = datetime.datetime.now()
    return now_datetime.strftime('%d.%m.%Y %H:%M:%S')  # noqa: WPS323


def sanitize(text: str) -> str:
    r"""Sanitize text.

    '\\n' because click escapes command line arguments

    Args:
        text: text for processing

    Returns:
        object: reworked text
    """
    return text.replace('\\n', '')  # noqa: WPS342


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


async def read_msgs_from_server(
    host: str,
    port: int,
    queues: Queues,
) -> None:
    """Reads messages from the server.

    Args:
        host: server host
        port: server listen port
        queues: queues
    """
    async with open_connection(host, port) as (reader, writer):
        while True:
            queues.status.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
            chat_message = await reader.readline()
            decoded_chat_message = chat_message.decode()
            queues.messages.put_nowait(decoded_chat_message)
            queues.history.put_nowait(decoded_chat_message)
            queues.watchdog.put_nowait('Connection is alive. New message in chat')


async def read_msgs_from_file(
    filepath: str,
    messages_queue: asyncio.Queue[str],
) -> None:
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


async def get_response_from_server(reader: asyncio.StreamReader) -> bytes:
    """Read message from server.

    Args:
        reader: asyncio.StreamReader

    Returns:
        object: response from server
    """
    return await reader.readline()


async def submit_message(writer, message: str):
    """Send message to chat.

    Args:
        writer: asyncio.StreamWriter
        message: message to be sent to the server
    """
    writer.write(message.encode())
    await writer.drain()


async def log_on_to_server(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    token: str,
    queues: Queues,
) -> dict[str, str]:
    """Log on to server.

    Args:
        reader: asyncio.StreamReader
        writer: asyncio.StreamWriter
        token: user token for authorization on the server
        queues: project queues

    Returns:
        object: response from server

    Raises:
        InvalidTokenError: error when using an invalid token
    """
    queues.status.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
    queues.status.put_nowait(gui.SendingConnectionStateChanged.INITIATED)
    queues.watchdog.put_nowait('Connection is alive. Prompt before auth')
    await get_response_from_server(reader)
    await submit_message(writer, f'{token}\n')
    server_response = await get_response_from_server(reader)
    account_info = json.loads(server_response)
    if account_info is None:
        raise InvalidTokenError
    queues.watchdog.put_nowait('Connection is alive. Authorization done')
    return account_info


async def send_msgs(
    host: str,
    port: int,
    queues: Queues,
    token: str,
):
    """Send message to server.

    Args:
        host: server host
        port: writing server port
        token: user token for authorization on the server
        queues: queues
    """
    async with open_connection(host, port) as (reader, writer):
        await submit_message(writer, f'{token}\n')
        while True:
            queues.status.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)
            user_msg = await queues.sending.get()
            await submit_message(writer, message=f'{sanitize(user_msg)}\n\n')
            queues.watchdog.put_nowait('Connection is alive. Message sent')


async def watch_for_connection(queue: asyncio.Queue[str]):
    """Keeps track of the connection to the server.

    Args:
        queue: watchdog queue
    """
    while True:
        log_message = await queue.get()
        logger.info(log_message)


@run_async  # type: ignore
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
    queues = Queues()

    try:
        async with open_connection(host, writing_server_port) as (reader, writer):
            await log_on_to_server(reader, writer, token, queues)
    except InvalidTokenError:
        messagebox.showinfo('Неверный токен', 'Проверьте токен, сервер не узнал его')
        sys.exit('Неверный токен')

    await read_msgs_from_file(
        filepath=history_file_path,
        messages_queue=queues.messages,
    )

    await asyncio.gather(
        gui.draw(queues.messages, queues.sending, queues.status),
        read_msgs_from_server(
            host=host,
            port=listen_server_port,
            queues=queues,
        ),
        save_msgs(
            filepath=history_file_path,
            current_time=get_current_time(),
            queue=queues.history,
        ),
        send_msgs(
            host=host,
            port=writing_server_port,
            token=token,
            queues=queues,
        ),
        watch_for_connection(queue=queues.watchdog),
    )


if __name__ == '__main__':
    typer.run(main)
