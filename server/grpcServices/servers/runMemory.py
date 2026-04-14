"""
Entry point for standalone Memory gRPC server.
Run from server/ directory:  python -m grpc.servers.runMemory
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from config.logger import logger
from config.database import db
from common.cacheService import cacheService
from grpcServices.servers.memoryServer import MemoryGrpcServer


async def main():
    await db.connect()
    await cacheService.connect()
    server = MemoryGrpcServer()
    await server.start()
    logger.info("Memory gRPC server ready — waiting for requests")
    try:
        await server.waitForTermination()
    except KeyboardInterrupt:
        logger.info("Shutting down Memory gRPC server...")
        await server.stop()
        await cacheService.close()
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
