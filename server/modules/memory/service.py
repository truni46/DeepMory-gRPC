"""
Memory facade — single import point for message/service.py.
Delegates to shortTerm (Conv) and longTerm (Mem) sub-modules,
or to gRPC remote when MEMORY_USE_GRPC=true.
"""
from __future__ import annotations

import os
from typing import Dict, List

from modules.memory.shortTerm.convRAG import convRAG
from modules.memory.longTerm.memRAG import memRAG


class MemoryFacade:

    def __init__(self):
        self._useGrpc = os.getenv("MEMORY_USE_GRPC", "false").lower() == "true"

    def _grpcAvailable(self) -> bool:
        if not self._useGrpc:
            return False
        from grpcServices.clients.memoryClient import memoryGrpcClient
        return memoryGrpcClient.isConnected

    async def addTurn(self, conversationId: str, role: str, content: str) -> None:
        if self._grpcAvailable():
            from grpcServices.clients.memoryClient import memoryGrpcClient
            return await memoryGrpcClient.addTurn(conversationId, role, content)
        await convRAG.addTurn(conversationId, role, content)

    async def getContextWindow(self, conversationId: str) -> List[Dict]:
        if self._grpcAvailable():
            from grpcServices.clients.memoryClient import memoryGrpcClient
            return await memoryGrpcClient.getContextWindow(conversationId)
        return await convRAG.getContextWindow(conversationId)

    async def clearConversation(self, conversationId: str) -> None:
        if self._grpcAvailable():
            from grpcServices.clients.memoryClient import memoryGrpcClient
            return await memoryGrpcClient.clearConversation(conversationId)
        await convRAG.clearConversation(conversationId)

    async def retrieveRelevantMemories(
        self,
        userId: str,
        query: str,
        limit: int = 5,
    ) -> List[str]:
        if self._grpcAvailable():
            from grpcServices.clients.memoryClient import memoryGrpcClient
            return await memoryGrpcClient.retrieveRelevantMemories(userId, query, limit)
        return await memRAG.retrieveRelevantMemories(userId, query, limit)

    async def processConversationTurn(
        self,
        userId: str,
        conversationId: str,
        userMessage: str,
        assistantResponse: str,
    ) -> None:
        if self._grpcAvailable():
            from grpcServices.clients.memoryClient import memoryGrpcClient
            return await memoryGrpcClient.processConversationTurn(
                userId, conversationId, userMessage, assistantResponse
            )
        await memRAG.processConversationTurn(
            userId, conversationId, userMessage, assistantResponse
        )

    async def deleteMemory(self, userId: str, memoryId: str) -> bool:
        if self._grpcAvailable():
            from grpcServices.clients.memoryClient import memoryGrpcClient
            return await memoryGrpcClient.deleteMemory(userId, memoryId)
        return await memRAG.deleteMemory(userId, memoryId)


memoryFacade = MemoryFacade()
