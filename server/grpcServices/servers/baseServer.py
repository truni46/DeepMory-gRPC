"""
Base gRPC async server.
"""
from __future__ import annotations

from concurrent import futures

import grpc

from config.logger import logger


class BaseGrpcServer:

    def __init__(self, serviceName: str, port: int, maxWorkers: int = 10):
        self.serviceName = serviceName
        self.port = port
        self.server = None
        self.maxWorkers = maxWorkers

    async def start(self):
        self.server = grpc.aio.server(
            futures.ThreadPoolExecutor(max_workers=self.maxWorkers),
            options=[
                ("grpc.max_send_message_length", 50 * 1024 * 1024),
                ("grpc.max_receive_message_length", 50 * 1024 * 1024),
                ("grpc.keepalive_time_ms", 30000),
                ("grpc.keepalive_timeout_ms", 10000),
                ("grpc.keepalive_permit_without_calls", True),
            ],
        )
        self.registerServices(self.server)
        self.server.add_insecure_port(f"[::]:{self.port}")
        await self.server.start()
        logger.info(f"gRPC {self.serviceName} started on port {self.port}")

    def registerServices(self, server):
        raise NotImplementedError

    async def stop(self):
        if self.server:
            await self.server.stop(grace=5)
            logger.info(f"gRPC {self.serviceName} stopped")

    async def waitForTermination(self):
        await self.server.wait_for_termination()
