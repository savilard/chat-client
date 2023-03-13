from chat_client import gui
from chat_client.connection import open_connection
from chat_client.queues import Queues


async def read_msgs(
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
