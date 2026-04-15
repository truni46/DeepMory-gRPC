"""
gRPC client for Memory service.
"""
from __future__ import annotations

import os
from typing import Dict, List

from grpcServices.clients.baseClient import BaseGrpcClient
from grpcServices.generated import memory_pb2, memory_pb2_grpc
from config.logger import logger


class MemoryGrpcClient(BaseGrpcClient):

    def __init__(self):
        super().__init__(
            serviceName="MemoryService",
            host=os.getenv("MEMORY_GRPC_HOST", "localhost"),
            port=int(os.getenv("MEMORY_GRPC_PORT", "50052")),
        )
        self.stub = None

    async def connect(self):
        await super().connect()
        self.stub = memory_pb2_grpc.MemoryServiceStub(self.channel)

    async def getContextWindow(self, conversationId: str) -> List[Dict]:
        request = memory_pb2.ContextWindowRequest(conversationId=conversationId)
        response = await self.callWithRetry(
            self.stub.GetContextWindow, request, "getContextWindow"
        )
        return [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp}
            for m in response.messages
        ]

    async def retrieveRelevantMemories(
        self, userId: str, query: str, limit: int = 5
    ) -> List[str]:
        request = memory_pb2.RelevantMemoriesRequest(
            userId=userId, query=query, topK=limit
        )
        response = await self.callWithRetry(
            self.stub.RetrieveRelevantMemories, request, "retrieveRelevantMemories"
        )
        return list(response.memories)

    async def processConversationTurn(
        self, userId: str, conversationId: str, userMessage: str, assistantResponse: str
    ) -> None:
        request = memory_pb2.ConversationTurnRequest(
            conversationId=conversationId,
            userId=userId,
            userMessage=userMessage,
            assistantResponse=assistantResponse,
        )
        await self.callWithRetry(
            self.stub.ProcessConversationTurn, request, "processConversationTurn"
        )

    async def addTurn(self, conversationId: str, role: str, content: str) -> None:
        request = memory_pb2.AddTurnRequest(
            conversationId=conversationId, role=role, content=content
        )
        await self.callWithRetry(self.stub.AddTurn, request, "addTurn")

    async def clearConversation(self, conversationId: str) -> None:
        request = memory_pb2.ClearConversationRequest(conversationId=conversationId)
        await self.callWithRetry(
            self.stub.ClearConversation, request, "clearConversation"
        )

    async def listMemories(self, userId: str) -> List[Dict]:
        request = memory_pb2.ListMemoriesRequest(userId=userId)
        response = await self.callWithRetry(
            self.stub.ListMemories, request, "listMemories"
        )
        return [
            {
                "id": m.id,
                "content": m.content,
                "createdAt": m.createdAt,
                "metadata": dict(m.metadata),
            }
            for m in response.memories
        ]

    async def updateMemory(self, memoryId: str, userId: str, content: str) -> None:
        request = memory_pb2.UpdateMemoryRequest(
            memoryId=memoryId, userId=userId, content=content
        )
        await self.callWithRetry(self.stub.UpdateMemory, request, "updateMemory")

    async def deleteMemory(self, userId: str, memoryId: str) -> bool:
        request = memory_pb2.DeleteMemoryRequest(memoryId=memoryId, userId=userId)
        response = await self.callWithRetry(
            self.stub.DeleteMemory, request, "deleteMemory"
        )
        return response.success


memoryGrpcClient = MemoryGrpcClient()
