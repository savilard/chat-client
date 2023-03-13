from chat_client import gui
from chat_client.connection import open_connection
from chat_client.queues import Queues
from chat_client.server import submit_message


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


def sanitize(text: str) -> str:
    r"""Sanitize text.

    '\\n' because click escapes command line arguments

    Args:
        text: text for processing

    Returns:
        object: reworked text
    """
    return text.replace('\\n', '')  # noqa: WPS342
