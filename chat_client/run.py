import asyncio
import datetime
from functools import wraps
import sys
from tkinter import messagebox

import anyio
import typer

from chat_client import connection
from chat_client import exceptions
from chat_client import gui
from chat_client import history
from chat_client import listen
from chat_client import write
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


@connection.reconnect
async def handle_connection(
    host: str,
    listen_server_port: int,
    writing_server_port: int,
    token: str,
    queues: Queues,
):
    """Controls the network connection.

    Args:
        host: server host
        listen_server_port: server listen port
        writing_server_port: server writing port
        token: user token
        queues: app queues
    """
    async with anyio.create_task_group() as tg:
        tg.start_soon(listen.read_msgs, host, listen_server_port, queues)
        tg.start_soon(write.send_msgs, host, writing_server_port, queues, token)
        tg.start_soon(connection.watch_for_connection, queues.watchdog)


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
        async with connection.open_connection(host, writing_server_port) as (reader, writer):
            await authorise(reader, writer, token, queues)
    except exceptions.InvalidTokenError:
        messagebox.showinfo('Неверный токен', 'Проверьте токен, сервер не узнал его')
        sys.exit('Неверный токен')

    await history.read_msgs(filepath=history_file_path, messages_queue=queues.messages)

    await asyncio.gather(
        gui.draw(queues.messages, queues.sending, queues.status),
        history.save_msgs(
            filepath=history_file_path,
            current_time=get_current_time(),
            queue=queues.history,
        ),
        handle_connection(
            host=host,
            listen_server_port=listen_server_port,
            writing_server_port=writing_server_port,
            token=token,
            queues=queues,
        ),
    )


if __name__ == '__main__':
    typer.run(main)
