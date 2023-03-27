import asyncio

from chat_client.queues import Queues
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
    writer: asyncio.StreamWriter,
    queues: Queues,
):
    """Send message to server.

    Args:
        writer: asyncio.StreamWriter
        queues: queues
    """
    while True:
        user_msg = await queues.sending.get()
        await submit_message(writer, message=f'{sanitize(user_msg)}\n\n')
        queues.watchdog.put_nowait('Сообщение отправлено')
