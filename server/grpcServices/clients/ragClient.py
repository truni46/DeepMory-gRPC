"""
gRPC client for RAG service.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional

from grpcServices.clients.baseClient import BaseGrpcClient
from grpcServices.generated import rag_pb2, rag_pb2_grpc
from config.logger import logger


class RagGrpcClient(BaseGrpcClient):

    def __init__(self):
        super().__init__(
            serviceName="RagService",
            host=os.getenv("RAG_GRPC_HOST", "localhost"),
            port=int(os.getenv("RAG_GRPC_PORT", "50051")),
        )
        self.stub = None

    async def connect(self):
        await super().connect()
        self.stub = rag_pb2_grpc.RagServiceStub(self.channel)

    async def searchContext(
        self, query: str, projectId: str, limit: int = 5, rerank: bool = False, mode: str = None
    ) -> List[Dict]:
        request = rag_pb2.SearchContextRequest(
            projectId=projectId,
            query=query,
            topK=limit,
            useReranking=rerank,
            mode=mode or "",
        )
        response = await self.callWithRetry(
            self.stub.SearchContext, request, "searchContext"
        )
        return [
            {
                "content": r.content,
                "score": r.score,
                "documentId": r.documentId,
                "fileName": r.fileName,
                "metadata": dict(r.metadata),
            }
            for r in response.results
        ]

    async def searchMemoryVectors(self, userId: str, query: str, limit: int = 5) -> List[Dict]:
        request = rag_pb2.SearchMemoryRequest(
            userId=userId, query=query, topK=limit
        )
        response = await self.callWithRetry(
            self.stub.SearchMemoryVectors, request, "searchMemoryVectors"
        )
        return [
            {"memoryId": r.memoryId, "content": r.content, "score": r.score}
            for r in response.results
        ]

    async def indexDocument(
        self, filePath: str, projectId: str, documentId: str, userId: str
    ) -> None:
        request = rag_pb2.IndexDocumentRequest(
            projectId=projectId,
            documentId=documentId,
            filePath=filePath,
            userId=userId,
        )
        await self.callWithRetry(
            self.stub.IndexDocument, request, "indexDocument"
        )

    async def deleteDocumentChunks(self, projectId: str, documentId: str) -> None:
        request = rag_pb2.DeleteChunksRequest(
            projectId=projectId, documentId=documentId
        )
        await self.callWithRetry(
            self.stub.DeleteDocumentChunks, request, "deleteDocumentChunks"
        )

    async def upsertMemoryVector(
        self, userId: str, memoryId: str, content: str, metadata: Optional[Dict] = None
    ) -> None:
        request = rag_pb2.UpsertMemoryRequest(
            userId=userId,
            memoryId=memoryId,
            content=content,
            metadata={k: str(v) for k, v in (metadata or {}).items()},
        )
        await self.callWithRetry(
            self.stub.UpsertMemoryVector, request, "upsertMemoryVector"
        )

    async def deleteMemoryVector(self, userId: str, memoryId: str) -> None:
        request = rag_pb2.DeleteMemoryRequest(
            userId=userId, memoryId=memoryId
        )
        await self.callWithRetry(
            self.stub.DeleteMemoryVector, request, "deleteMemoryVector"
        )


ragGrpcClient = RagGrpcClient()
