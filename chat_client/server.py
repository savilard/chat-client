import asyncio


async def get_response_from_server(reader: asyncio.StreamReader) -> bytes:
    """Read message from server.

    Args:
        reader: asyncio.StreamReader

    Returns:
        object: response from server
    """
    return await reader.readline()


async def submit_message(writer, message: str):
    """Send message to chat.

    Args:
        writer: asyncio.StreamWriter
        message: message to be sent to the server
    """
    writer.write(message.encode())
    await writer.drain()
