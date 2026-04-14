"""
gRPC client for Agents service.
"""
from __future__ import annotations

import os
from typing import AsyncGenerator, Dict, Optional

from grpcServices.clients.baseClient import BaseGrpcClient
from grpcServices.generated import agents_pb2, agents_pb2_grpc
from config.logger import logger


class AgentsGrpcClient(BaseGrpcClient):

    def __init__(self):
        super().__init__(
            serviceName="AgentsService",
            host=os.getenv("AGENTS_GRPC_HOST", "localhost"),
            port=int(os.getenv("AGENTS_GRPC_PORT", "50053")),
        )
        self.stub = None

    async def connect(self):
        await super().connect()
        self.stub = agents_pb2_grpc.AgentsServiceStub(self.channel)

    async def createTask(
        self,
        userId: str,
        goal: str,
        conversationId: Optional[str] = None,
        projectId: Optional[str] = None,
    ) -> Dict:
        request = agents_pb2.CreateTaskRequest(
            userId=userId,
            goal=goal,
            conversationId=conversationId or "",
            projectId=projectId or "",
        )
        response = await self.callWithRetry(
            self.stub.CreateTask, request, "createTask"
        )
        return {"taskId": response.taskId, "status": response.status}

    async def runFromCommand(
        self, userId: str, conversationId: Optional[str], command: str
    ) -> Dict:
        request = agents_pb2.RunCommandRequest(
            userId=userId,
            conversationId=conversationId or "",
            command=command,
        )
        response = await self.callWithRetry(
            self.stub.RunFromCommand, request, "runFromCommand"
        )
        return {"taskId": response.taskId, "status": response.status}

    async def streamTask(self, taskId: str, userId: str) -> AsyncGenerator[str, None]:
        request = agents_pb2.StreamTaskRequest(taskId=taskId, userId=userId)
        async for event in self.streamWithRetry(
            self.stub.StreamTask, request, "streamTask"
        ):
            import json
            yield f"data: {json.dumps({'type': event.type, 'agentType': event.agentType, 'status': event.status, 'output': event.output, 'finalReport': event.finalReport, 'taskId': event.taskId}, default=str)}\n\n"

    async def getTask(self, taskId: str, userId: str) -> Optional[Dict]:
        request = agents_pb2.GetTaskRequest(taskId=taskId, userId=userId)
        response = await self.callWithRetry(
            self.stub.GetTask, request, "getTask"
        )
        if not response.taskId:
            return None
        return {
            "id": response.taskId,
            "status": response.status,
            "goal": response.goal,
            "finalReport": response.finalReport,
            "errorMessage": response.errorMessage,
            "createdAt": response.createdAt,
            "updatedAt": response.updatedAt,
            "runs": [
                {
                    "agentType": r.agentType,
                    "status": r.status,
                    "output": r.output,
                    "timestamp": r.timestamp,
                }
                for r in response.runs
            ],
        }

    async def listTasks(self, userId: str) -> list:
        request = agents_pb2.ListTasksRequest(userId=userId)
        response = await self.callWithRetry(
            self.stub.ListTasks, request, "listTasks"
        )
        return [
            {
                "id": t.taskId,
                "status": t.status,
                "goal": t.goal,
                "finalReport": t.finalReport,
                "createdAt": t.createdAt,
            }
            for t in response.tasks
        ]

    async def cancelTask(self, taskId: str, userId: str) -> bool:
        request = agents_pb2.CancelTaskRequest(taskId=taskId, userId=userId)
        response = await self.callWithRetry(
            self.stub.CancelTask, request, "cancelTask"
        )
        return response.success


agentsGrpcClient = AgentsGrpcClient()
