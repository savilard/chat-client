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
from chat_client import messages
from chat_client import server
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
async def main(
    host: str = typer.Option(
        default='minechat.dvmn.org',
        help='Minechat host',
        envvar='SERVER_HOST',
    ),
    port_out: int = typer.Option(
        default=5000,
        help='Minechat listen port',
        envvar='PORT_OUT',
    ),
    port_in: int = typer.Option(
        default=5050,
        help='Minechat writing port',
        envvar='PORT_IN',
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
        port_out: port to receive messages
        port_in: port for sending messages
        token: token to access the server
        history_file_path: Path to file with history of minechat
    """
    queues = Queues()
    minechat_server = server.Server(host=host, port_in=port_in, port_out=port_out)

    try:
        async with connection.open_connection(minechat_server.host, minechat_server.port_in) as (reader, writer):
            account_info = await authorise(reader, writer, token, queues)
    except exceptions.InvalidTokenError:
        messagebox.showinfo('Неверный токен', 'Проверьте токен, сервер не узнал его')
        sys.exit('Неверный токен')

    await history.read_msgs(filepath=history_file_path, messages_queue=queues.messages)

    async with anyio.create_task_group() as tg:
        tg.start_soon(gui.draw, queues.messages, queues.sending, queues.status)
        tg.start_soon(history.save_msgs, history_file_path, get_current_time(), queues.history)
        tg.start_soon(handle_connection, minechat_server, token, queues, account_info['nickname'])


if __name__ == '__main__':
    typer.run(main)
