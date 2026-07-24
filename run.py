import asyncio
import logging

from public_bot import run_public_bot

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    asyncio.run(run_public_bot())
