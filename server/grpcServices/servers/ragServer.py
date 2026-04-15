"""
gRPC server implementation for RAG service.
"""
from __future__ import annotations

import os

import grpc

from grpcServices.servers.baseServer import BaseGrpcServer
from grpcServices.generated import rag_pb2, rag_pb2_grpc, common_pb2
from config.logger import logger


class RagServiceHandler(rag_pb2_grpc.RagServiceServicer):

    def __init__(self):
        from modules.rag.ragService import ragService
        self.ragService = ragService

    async def SearchContext(self, request, context):
        try:
            results = await self.ragService.searchContext(
                query=request.query,
                projectId=request.projectId,
                limit=request.topK or 5,
                rerank=request.useReranking,
                mode=request.mode or None,
            )
            return rag_pb2.SearchContextResponse(
                results=[
                    rag_pb2.RagResult(
                        content=r.document.content,
                        score=r.score,
                        documentId=r.document.id,
                        fileName=r.document.metadata.get("fileName", ""),
                        metadata={k: str(v) for k, v in r.document.metadata.items()},
                    )
                    for r in results
                ]
            )
        except Exception as e:
            logger.error(f"RagServer.SearchContext failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return rag_pb2.SearchContextResponse()

    async def SearchMemoryVectors(self, request, context):
        try:
            results = await self.ragService.searchMemoryVectors(
                userId=request.userId,
                query=request.query,
                limit=request.topK or 5,
            )
            return rag_pb2.SearchMemoryResponse(
                results=[
                    rag_pb2.MemoryVector(
                        memoryId=r.document.id,
                        content=r.document.content,
                        score=r.score,
                    )
                    for r in results
                ]
            )
        except Exception as e:
            logger.error(f"RagServer.SearchMemoryVectors failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return rag_pb2.SearchMemoryResponse()

    async def IndexDocument(self, request, context):
        try:
            await self.ragService.index(
                filePath=request.filePath,
                projectId=request.projectId,
                documentId=request.documentId,
                userId=request.userId,
            )
            return common_pb2.Empty()
        except Exception as e:
            logger.error(f"RagServer.IndexDocument failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return common_pb2.Empty()

    async def DeleteDocumentChunks(self, request, context):
        try:
            await self.ragService.deleteDocumentChunks(
                projectId=request.projectId,
                documentId=request.documentId,
            )
            return common_pb2.Empty()
        except Exception as e:
            logger.error(f"RagServer.DeleteDocumentChunks failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return common_pb2.Empty()

    async def UpsertMemoryVector(self, request, context):
        try:
            await self.ragService.upsertMemoryVector(
                userId=request.userId,
                memoryId=request.memoryId,
                content=request.content,
                metadata=dict(request.metadata) if request.metadata else None,
            )
            return common_pb2.Empty()
        except Exception as e:
            logger.error(f"RagServer.UpsertMemoryVector failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return common_pb2.Empty()

    async def DeleteMemoryVector(self, request, context):
        try:
            await self.ragService.deleteMemoryVector(
                userId=request.userId,
                memoryId=request.memoryId,
            )
            return common_pb2.Empty()
        except Exception as e:
            logger.error(f"RagServer.DeleteMemoryVector failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return common_pb2.Empty()


class RagGrpcServer(BaseGrpcServer):
    def __init__(self):
        super().__init__(
            serviceName="RagService",
            port=int(os.getenv("RAG_GRPC_PORT", "50051")),
        )

    def registerServices(self, server):
        rag_pb2_grpc.add_RagServiceServicer_to_server(RagServiceHandler(), server)
