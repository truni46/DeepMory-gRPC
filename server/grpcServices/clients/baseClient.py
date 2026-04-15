"""
Base gRPC client with retry logic and error mapping.
"""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator

import grpc
from fastapi import HTTPException

from config.logger import logger


GRPC_TO_HTTP = {
    grpc.StatusCode.OK: 200,
    grpc.StatusCode.INVALID_ARGUMENT: 400,
    grpc.StatusCode.UNAUTHENTICATED: 401,
    grpc.StatusCode.PERMISSION_DENIED: 403,
    grpc.StatusCode.NOT_FOUND: 404,
    grpc.StatusCode.ALREADY_EXISTS: 409,
    grpc.StatusCode.RESOURCE_EXHAUSTED: 429,
    grpc.StatusCode.UNAVAILABLE: 503,
    grpc.StatusCode.DEADLINE_EXCEEDED: 504,
    grpc.StatusCode.INTERNAL: 500,
}

RETRYABLE_CODES = (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED)


def grpcErrorToHttp(error: grpc.aio.AioRpcError) -> HTTPException:
    httpStatus = GRPC_TO_HTTP.get(error.code(), 500)
    return HTTPException(status_code=httpStatus, detail=error.details())


class BaseGrpcClient:

    def __init__(self, serviceName: str, host: str, port: int):
        self.serviceName = serviceName
        self.address = f"{host}:{port}"
        self.channel = None
        self.maxRetries = 3
        self.retryDelay = 0.5

    async def connect(self):
        try:
            self.channel = grpc.aio.insecure_channel(
                self.address,
                options=[
                    ("grpc.keepalive_time_ms", 30000),
                    ("grpc.keepalive_timeout_ms", 10000),
                    ("grpc.keepalive_permit_without_calls", True),
                    ("grpc.max_send_message_length", 50 * 1024 * 1024),
                    ("grpc.max_receive_message_length", 50 * 1024 * 1024),
                ],
            )
            await self.channel.channel_ready()
            logger.info(f"gRPC client connected to {self.serviceName} at {self.address}")
        except Exception as e:
            logger.error(f"gRPC connect to {self.serviceName} failed: {e}")
            raise

    async def disconnect(self):
        if self.channel:
            await self.channel.close()
            logger.info(f"gRPC client disconnected from {self.serviceName}")

    @property
    def isConnected(self) -> bool:
        return self.channel is not None

    async def callWithRetry(self, method, request, methodName: str = "unknown"):
        lastError = None
        for attempt in range(1, self.maxRetries + 1):
            try:
                return await method(request)
            except grpc.aio.AioRpcError as e:
                lastError = e
                if e.code() in RETRYABLE_CODES:
                    logger.warning(
                        f"{self.serviceName}.{methodName} attempt {attempt}/{self.maxRetries} "
                        f"failed: {e.code().name} - {e.details()}"
                    )
                    if attempt < self.maxRetries:
                        await asyncio.sleep(self.retryDelay * attempt)
                    continue
                logger.error(f"{self.serviceName}.{methodName} failed: {e.code().name} - {e.details()}")
                raise
            except Exception as e:
                logger.error(f"{self.serviceName}.{methodName} unexpected error: {e}")
                raise
        logger.error(f"{self.serviceName}.{methodName} exhausted {self.maxRetries} retries")
        raise lastError

    async def streamWithRetry(self, method, request, methodName: str = "unknown") -> AsyncGenerator:
        lastError = None
        for attempt in range(1, self.maxRetries + 1):
            try:
                stream = method(request)
                async for event in stream:
                    yield event
                return
            except grpc.aio.AioRpcError as e:
                lastError = e
                if e.code() in RETRYABLE_CODES:
                    logger.warning(
                        f"{self.serviceName}.{methodName} stream attempt {attempt}/{self.maxRetries} "
                        f"failed: {e.code().name}"
                    )
                    if attempt < self.maxRetries:
                        await asyncio.sleep(self.retryDelay * attempt)
                    continue
                logger.error(f"{self.serviceName}.{methodName} stream failed: {e.code().name}")
                raise
            except Exception as e:
                logger.error(f"{self.serviceName}.{methodName} stream unexpected error: {e}")
                raise
        logger.error(f"{self.serviceName}.{methodName} stream exhausted retries")
        raise lastError
