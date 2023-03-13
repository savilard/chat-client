import asyncio
from dataclasses import dataclass
from dataclasses import field

from chat_client import gui


@dataclass
class Queues:
    """Project queues."""

    messages: asyncio.Queue[str] = field(default=asyncio.Queue())
    sending: asyncio.Queue[str] = field(default=asyncio.Queue())
    status: asyncio.Queue[
        gui.SendingConnectionStateChanged | gui.ReadConnectionStateChanged | gui.NicknameReceived
    ] = field(default=asyncio.Queue())
    history: asyncio.Queue[str] = field(default=asyncio.Queue())
    watchdog: asyncio.Queue[str] = field(default=asyncio.Queue())
