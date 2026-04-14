"""
gRPC server implementation for Memory service.
"""
from __future__ import annotations

import os

import grpc

from grpcServices.servers.baseServer import BaseGrpcServer
from grpcServices.generated import memory_pb2, memory_pb2_grpc, common_pb2
from config.logger import logger


class MemoryServiceHandler(memory_pb2_grpc.MemoryServiceServicer):

    def __init__(self):
        from modules.memory.service import memoryFacade
        from modules.memory.longTerm.repository import memoryRepository
        self.memoryFacade = memoryFacade
        self.memoryRepository = memoryRepository

    async def GetContextWindow(self, request, context):
        try:
            messages = await self.memoryFacade.getContextWindow(
                conversationId=request.conversationId,
            )
            return memory_pb2.ContextWindowResponse(
                messages=[
                    memory_pb2.ConversationMessage(
                        role=m.get("role", ""),
                        content=m.get("content", ""),
                        timestamp=m.get("timestamp", ""),
                    )
                    for m in messages
                ],
            )
        except Exception as e:
            logger.error(f"MemoryServer.GetContextWindow failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return memory_pb2.ContextWindowResponse()

    async def RetrieveRelevantMemories(self, request, context):
        try:
            memories = await self.memoryFacade.retrieveRelevantMemories(
                userId=request.userId,
                query=request.query,
                limit=request.topK or 5,
            )
            return memory_pb2.RelevantMemoriesResponse(memories=memories)
        except Exception as e:
            logger.error(f"MemoryServer.RetrieveRelevantMemories failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return memory_pb2.RelevantMemoriesResponse()

    async def ProcessConversationTurn(self, request, context):
        try:
            await self.memoryFacade.processConversationTurn(
                userId=request.userId,
                conversationId=request.conversationId,
                userMessage=request.userMessage,
                assistantResponse=request.assistantResponse,
            )
            return memory_pb2.ProcessTurnResponse()
        except Exception as e:
            logger.error(f"MemoryServer.ProcessConversationTurn failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return memory_pb2.ProcessTurnResponse()

    async def AddTurn(self, request, context):
        try:
            await self.memoryFacade.addTurn(
                conversationId=request.conversationId,
                role=request.role,
                content=request.content,
            )
            return common_pb2.Empty()
        except Exception as e:
            logger.error(f"MemoryServer.AddTurn failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return common_pb2.Empty()

    async def ClearConversation(self, request, context):
        try:
            await self.memoryFacade.clearConversation(
                conversationId=request.conversationId,
            )
            return common_pb2.Empty()
        except Exception as e:
            logger.error(f"MemoryServer.ClearConversation failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return common_pb2.Empty()

    async def ListMemories(self, request, context):
        try:
            memories = await self.memoryRepository.getByUser(request.userId, limit=200)
            return memory_pb2.ListMemoriesResponse(
                memories=[
                    memory_pb2.MemoryItem(
                        id=m.get("id", ""),
                        content=m.get("content", ""),
                        createdAt=str(m.get("createdAt", "")),
                        metadata={k: str(v) for k, v in m.get("metadata", {}).items()},
                    )
                    for m in memories
                ]
            )
        except Exception as e:
            logger.error(f"MemoryServer.ListMemories failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return memory_pb2.ListMemoriesResponse()

    async def UpdateMemory(self, request, context):
        try:
            await self.memoryRepository.update(
                request.memoryId, request.userId, request.content
            )
            return common_pb2.Empty()
        except Exception as e:
            logger.error(f"MemoryServer.UpdateMemory failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return common_pb2.Empty()

    async def DeleteMemory(self, request, context):
        try:
            success = await self.memoryFacade.deleteMemory(
                userId=request.userId,
                memoryId=request.memoryId,
            )
            return memory_pb2.DeleteMemoryResponse(success=success)
        except Exception as e:
            logger.error(f"MemoryServer.DeleteMemory failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return memory_pb2.DeleteMemoryResponse(success=False)


class MemoryGrpcServer(BaseGrpcServer):
    def __init__(self):
        super().__init__(
            serviceName="MemoryService",
            port=int(os.getenv("MEMORY_GRPC_PORT", "50052")),
        )

    def registerServices(self, server):
        memory_pb2_grpc.add_MemoryServiceServicer_to_server(
            MemoryServiceHandler(), server
        )
