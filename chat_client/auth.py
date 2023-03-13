import asyncio
import json

from chat_client import exceptions
from chat_client import gui
from chat_client.queues import Queues
from chat_client.server import get_response_from_server
from chat_client.server import submit_message


async def authorise(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    token: str,
    queues: Queues,
) -> dict[str, str]:
    """Auth to server.

    Args:
        reader: asyncio.StreamReader
        writer: asyncio.StreamWriter
        token: user token for authorization on the server
        queues: project queues

    Returns:
        object: response from server

    Raises:
        InvalidTokenError: error when using an invalid token
    """
    queues.status.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
    queues.status.put_nowait(gui.SendingConnectionStateChanged.INITIATED)
    queues.watchdog.put_nowait('Connection is alive. Prompt before auth')
    await get_response_from_server(reader)
    await submit_message(writer, f'{token}\n')
    server_response = await get_response_from_server(reader)
    account_info = json.loads(server_response)
    if account_info is None:
        raise exceptions.InvalidTokenError
    queues.watchdog.put_nowait('Connection is alive. Authorization done')
    queues.status.put_nowait(gui.NicknameReceived(account_info['nickname']))
    return account_info
