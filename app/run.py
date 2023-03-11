import asyncio
import datetime
import json
import sys
from contextlib import asynccontextmanager
from functools import wraps
from tkinter import messagebox
from typing import AsyncGenerator

import aiofiles
import typer
from loguru import logger

import gui
from exceptions import InvalidTokenError


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
    messages_queue: asyncio.Queue[str],
    history_update_queue: asyncio.Queue[str],
    status_updates_queue: asyncio.Queue[gui.ReadConnectionStateChanged],
    watchdog_queue: asyncio.Queue[str],
) -> None:
    """Reads messages from the server.

    Args:
        host: server host
        port: server listen port
        messages_queue: messages queue
        history_update_queue: queue for saving message to file
        status_updates_queue: queue for status updates
        watchdog_queue: queue for
    """
    async with open_connection(host, port) as (reader, writer):
        while True:
            status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
            chat_message = await reader.readline()
            decoded_chat_message = chat_message.decode()
            messages_queue.put_nowait(decoded_chat_message)
            history_update_queue.put_nowait(decoded_chat_message)
            watchdog_queue.put_nowait('Connection is alive. New message in chat')


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
) -> dict[str, str]:
    """Log on to server.

    Args:
        reader: asyncio.StreamReader
        writer: asyncio.StreamWriter
        token: user token for authorization on the server

    Returns:
        object: response from server

    Raises:
        InvalidTokenError: error when using an invalid token
    """
    await get_response_from_server(reader)
    await submit_message(writer, f'{token}\n')
    server_response = await get_response_from_server(reader)
    account_info = json.loads(server_response)
    if account_info is None:
        raise InvalidTokenError
    return account_info


async def send_msgs(
    host: str,
    port: int,
    queue: asyncio.Queue[str],
    token: str,
    status_updates_queue: asyncio.Queue[gui.SendingConnectionStateChanged],
    watchdog_queue: asyncio.Queue[str],
):
    """Send message to server.

    Args:
        host: server host
        port: writing server port
        queue: queue
        token: user token for authorization on the server
        status_updates_queue: queue for status updates
        watchdog_queue: queue for watchdog
    """
    async with open_connection(host, port) as (reader, writer):
        await submit_message(writer, f'{token}\n')
        while True:
            status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)
            user_msg = await queue.get()
            await submit_message(writer, message=f'{sanitize(user_msg)}\n\n')
            watchdog_queue.put_nowait('Connection is alive. Message sent')


async def watch_for_connection(queue: asyncio.Queue[str]):
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
    messages_queue: asyncio.Queue[str] = asyncio.Queue()
    sending_queue: asyncio.Queue[str] = asyncio.Queue()
    status_updates_queue: asyncio.Queue[
        gui.SendingConnectionStateChanged
        | gui.ReadConnectionStateChanged
        | gui.NicknameReceived
        ] = asyncio.Queue()
    history_updates_queue: asyncio.Queue[str] = asyncio.Queue()
    watchdog_queue: asyncio.Queue[str] = asyncio.Queue()

    status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
    status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.INITIATED)
    watchdog_queue.put_nowait('Connection is alive. Prompt before auth')

    try:
        async with open_connection(host, writing_server_port) as (reader, writer):
            await log_on_to_server(reader, writer, token)
            watchdog_queue.put_nowait('Connection is alive. Authorization done')
    except InvalidTokenError:
        messagebox.showinfo('Неверный токен', 'Проверьте токен, сервер не узнал его')
        sys.exit('Неверный токен')

    await read_msgs_from_file(
        filepath=history_file_path,
        messages_queue=messages_queue,
    )

    await asyncio.gather(
        gui.draw(messages_queue, sending_queue, status_updates_queue),
        read_msgs_from_server(
            host=host,
            port=listen_server_port,
            messages_queue=messages_queue,
            history_update_queue=history_updates_queue,
            status_updates_queue=status_updates_queue,
            watchdog_queue=watchdog_queue,
        ),
        save_msgs(
            filepath=history_file_path,
            current_time=get_current_time(),
            queue=history_updates_queue,
        ),
        send_msgs(
            host=host,
            port=writing_server_port,
            queue=sending_queue,
            token=token,
            status_updates_queue=status_updates_queue,
            watchdog_queue=watchdog_queue,
        ),
        watch_for_connection(queue=watchdog_queue),
    )


if __name__ == '__main__':
    typer.run(main)
