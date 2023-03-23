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


async def ping_pong(minechat_server: server.Server):
    """Checks for a connection to the server.

    Args:
        minechat_server: minechat server
    """
    async with connection.open_connection(minechat_server.host, minechat_server.port_in) as (reader, writer):
        await server.submit_message(writer, '')


@connection.reconnect
async def handle_connection(
    minechat_server: server.Server,
    token: str,
    queues: Queues,
    nickname: str,
):
    """Controls the network connection.

    Args:
        minechat_server: minechat server
        token: user token
        queues: app queues
        nickname: user nickname
    """
    async with anyio.create_task_group() as tg:
        tg.start_soon(messages.read_msgs, minechat_server, queues, nickname)
        tg.start_soon(messages.send_msgs, minechat_server, queues, token, nickname)
        tg.start_soon(connection.watch_for_connection, queues.watchdog)
        tg.start_soon(ping_pong, minechat_server)


@run_async  # type: ignore
async def main() -> None:
    """Entry point."""
    load_dotenv()
    queues = Queues()
    settings = get_args()
    minechat_server = server.Server(host=settings.host, port_in=settings.inport, port_out=settings.outport)

    if settings.token is None or os.environ.get('TOKEN', None) is None:
        registration_run_command = (
            f'python chat_client/register.py'
            f' --host {minechat_server.host}'
            f' --outport {minechat_server.port_in}'
        )
        register = await anyio.run_process(registration_run_command)
        token = register.stdout.decode()
    else:
        token = settings.token

    try:
        async with connection.open_connection(minechat_server.host, minechat_server.port_in) as (reader, writer):
            account_info = await authorise(reader, writer, token, queues)
    except exceptions.InvalidTokenError:
        messagebox.showinfo('Неверный токен', 'Проверьте токен, сервер не узнал его')
        sys.exit('Неверный токен')

    await history.read_msgs(filepath=settings.history, messages_queue=queues.messages)

    async with anyio.create_task_group() as tg:
        tg.start_soon(gui.draw, queues.messages, queues.sending, queues.status)
        tg.start_soon(history.save_msgs, settings.history, get_current_time(), queues.history)
        tg.start_soon(handle_connection, minechat_server, token, queues, account_info['nickname'])


if __name__ == '__main__':
    with contextlib.suppress(KeyboardInterrupt, gui.TkAppClosedError, json.decoder.JSONDecodeError):
        main()
