import asyncio
import contextlib
import datetime
from functools import wraps
import json
import os
import sys
from tkinter import messagebox

import anyio
from dotenv import load_dotenv

from chat_client import connection
from chat_client import exceptions
from chat_client import gui
from chat_client import history
from chat_client import messages
from chat_client import server
from chat_client.args import get_args
from chat_client.auth import authorise
from chat_client.queues import Queues


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
        async def coro_wrapper():
            return await func(*args, **kwargs)

        return anyio.run(coro_wrapper)

    return wrapper


async def ping_pong(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, delay=60):
    """Checks for a connection to the server.

    Args:
        reader: asyncio.StreamReader
        writer: asyncio.StreamWriter
        delay: ping_pong delay
    """
    while True:
        await server.submit_message(writer, '')
        await reader.readuntil()
        await anyio.sleep(delay=delay)


@connection.reconnect()
async def handle_connection(
    minechat_server: server.Server,
    token: str,
    queues: Queues,
):
    """Controls the network connection.

    Args:
        minechat_server: minechat server
        token: user token
        queues: app queues
    """
    queues.status.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
    queues.status.put_nowait(gui.SendingConnectionStateChanged.INITIATED)
    queues.status.put_nowait(gui.NicknameReceived('неизвестно'))
    async with (
        connection.open_connection(minechat_server.host, minechat_server.port_in) as (send_reader, send_writer),
        connection.open_connection(minechat_server.host, minechat_server.port_out) as (read_reader, read_writer),
    ):
        queues.status.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
        queues.status.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)

        try:
            await authorise(send_reader, send_writer, token, queues)
        except exceptions.InvalidTokenError:
            messagebox.showinfo('Неверный токен', 'Проверьте токен, сервер не узнал его')
            sys.exit('Неверный токен')

        async with anyio.create_task_group() as tg:
            tg.start_soon(messages.read_msgs, read_reader, queues)
            tg.start_soon(messages.send_msgs, send_writer, queues, token)
            tg.start_soon(connection.watch_for_connection, queues.watchdog)
            tg.start_soon(ping_pong, send_reader, send_writer)


@run_async  # type: ignore
async def main() -> None:
    """Entry point."""
    load_dotenv()
    queues = Queues()
    settings = get_args()
    minechat_server = server.Server(host=settings.host, port_in=settings.inport, port_out=settings.outport)

    if settings.token is None:
        registration_run_command = (
            f'python chat_client/register.py --host {minechat_server.host} --outport {minechat_server.port_in}'
        )
        register = await anyio.run_process(registration_run_command)
        token = register.stdout.decode()
    else:
        token = settings.token

    async with anyio.create_task_group() as tg:
        tg.start_soon(history.read_msgs, settings.history, queues.messages)
        tg.start_soon(gui.draw, queues.messages, queues.sending, queues.status)
        tg.start_soon(history.save_msgs, settings.history, get_current_time(), queues.history)
        tg.start_soon(handle_connection, minechat_server, token, queues)


if __name__ == '__main__':
    with contextlib.suppress(KeyboardInterrupt, gui.TkAppClosedError, json.decoder.JSONDecodeError):
        main()
