import asyncio

from chat_client.queues import Queues


async def read_msgs(read_reader: asyncio.StreamReader, queues: Queues) -> None:
    """Reads messages from the server.

    Args:
        read_reader: asyncio.StreamReader
        queues: queues
    """
    while True:
        chat_message = await read_reader.readline()
        decoded_chat_message = chat_message.decode()
        queues.messages.put_nowait(decoded_chat_message)
        queues.history.put_nowait(decoded_chat_message)
        queues.watchdog.put_nowait('Новое сообщение в чате')
