import asyncio
import time

import gui


async def generate_msgs(queue: asyncio.Queue):
    while True:
        message = time.time()
        queue.put_nowait(message)
        await asyncio.sleep(1)


async def main():
    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    await asyncio.gather(
        gui.draw(messages_queue, sending_queue, status_updates_queue),
        generate_msgs(messages_queue),
    )


if __name__ == '__main__':
    asyncio.run(main())
