from chat_client import gui
from chat_client.connection import open_connection
from chat_client.queues import Queues
from chat_client.server import Server


async def read_msgs(
    server: Server,
    queues: Queues,
    nickname: str,
) -> None:
    """Reads messages from the server.

    Args:
        server: minechat server
        queues: queues
        nickname: user nickname
    """
    async with open_connection(server.host, server.port_out) as (reader, writer):
        queues.status.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
        queues.status.put_nowait(gui.NicknameReceived(nickname))
        while True:
            chat_message = await reader.readline()
            decoded_chat_message = chat_message.decode()
            queues.messages.put_nowait(decoded_chat_message)
            queues.history.put_nowait(decoded_chat_message)
            queues.watchdog.put_nowait('Connection is alive. New message in chat')
