from chat_client import gui
from chat_client.connection import open_connection
from chat_client.queues import Queues
from chat_client.server import Server
from chat_client.server import submit_message


def sanitize(text: str) -> str:
    r"""Sanitize text.

    '\\n' because click escapes command line arguments

    Args:
        text: text for processing

    Returns:
        object: reworked text
    """
    return text.replace('\\n', '')  # noqa: WPS342


async def send_msgs(
    server: Server,
    queues: Queues,
    token: str,
    nickname: str,
):
    """Send message to server.

    Args:
        server: minechat server
        token: user token for authorization on the server
        queues: queues
        nickname: user nickname
    """
    async with open_connection(server.host, server.port_in) as (reader, writer):
        queues.status.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)
        queues.status.put_nowait(gui.NicknameReceived(nickname))
        await submit_message(writer, f'{token}\n')
        while True:
            user_msg = await queues.sending.get()
            await submit_message(writer, message=f'{sanitize(user_msg)}\n\n')
            queues.watchdog.put_nowait('Connection is alive. Message sent')
