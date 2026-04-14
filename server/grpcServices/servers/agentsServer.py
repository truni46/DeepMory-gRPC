"""
gRPC server implementation for Agents service.
Includes server streaming for StreamTask.
"""
from __future__ import annotations

import asyncio
import json
import os

import grpc

from grpcServices.servers.baseServer import BaseGrpcServer
from grpcServices.generated import agents_pb2, agents_pb2_grpc
from config.logger import logger


class AgentsServiceHandler(agents_pb2_grpc.AgentsServiceServicer):

    def __init__(self):
        from modules.agents.service import agentService
        self.agentService = agentService

    async def CreateTask(self, request, context):
        try:
            result = await self.agentService.createTask(
                userId=request.userId,
                goal=request.goal,
                conversationId=request.conversationId or None,
                projectId=request.projectId or None,
            )
            return agents_pb2.CreateTaskResponse(
                taskId=result.get("id", ""),
                status=result.get("status", "pending"),
            )
        except Exception as e:
            logger.error(f"AgentsServer.CreateTask failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agents_pb2.CreateTaskResponse()

    async def RunFromCommand(self, request, context):
        try:
            result = await self.agentService.runFromCommand(
                userId=request.userId,
                conversationId=request.conversationId or None,
                command=request.command,
            )
            if "error" in result:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(result["error"])
                return agents_pb2.CreateTaskResponse()
            return agents_pb2.CreateTaskResponse(
                taskId=result.get("id", ""),
                status=result.get("status", "pending"),
            )
        except Exception as e:
            logger.error(f"AgentsServer.RunFromCommand failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agents_pb2.CreateTaskResponse()

    async def StreamTask(self, request, context):
        try:
            async for sseChunk in self.agentService.streamTask(
                taskId=request.taskId,
                userId=request.userId,
            ):
                if context.cancelled():
                    logger.info(f"StreamTask {request.taskId} cancelled by client")
                    return

                parsed = self._parseSseChunk(sseChunk)
                if parsed:
                    yield agents_pb2.TaskEvent(
                        type=parsed.get("type", ""),
                        agentType=parsed.get("agentType", ""),
                        status=parsed.get("status", ""),
                        output=json.dumps(parsed.get("output", ""), default=str)
                            if not isinstance(parsed.get("output", ""), str)
                            else str(parsed.get("output", "")),
                        finalReport=str(parsed.get("finalReport", "") or ""),
                        taskId=request.taskId,
                    )
        except asyncio.CancelledError:
            logger.info(f"StreamTask {request.taskId} cancelled")
        except Exception as e:
            logger.error(f"AgentsServer.StreamTask failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))

    def _parseSseChunk(self, chunk: str) -> dict | None:
        if not chunk or not chunk.startswith("data: "):
            return None
        try:
            return json.loads(chunk[6:].strip())
        except (json.JSONDecodeError, TypeError):
            return None

    async def GetTask(self, request, context):
        try:
            task = await self.agentService.getTask(
                taskId=request.taskId, userId=request.userId
            )
            if not task:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Task {request.taskId} not found")
                return agents_pb2.TaskResponse()
            return agents_pb2.TaskResponse(
                taskId=task.get("id", ""),
                status=task.get("status", ""),
                goal=task.get("goal", ""),
                finalReport=task.get("finalReport", "") or "",
                errorMessage=task.get("errorMessage", "") or "",
                createdAt=str(task.get("createdAt", "")),
                updatedAt=str(task.get("updatedAt", "")),
                runs=[
                    agents_pb2.TaskRun(
                        agentType=r.get("agentType", ""),
                        status=r.get("status", ""),
                        output=json.dumps(r.get("output", ""), default=str)
                            if not isinstance(r.get("output", ""), str)
                            else str(r.get("output", "")),
                        timestamp=str(r.get("timestamp", "")),
                    )
                    for r in task.get("runs", [])
                ],
            )
        except Exception as e:
            logger.error(f"AgentsServer.GetTask failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agents_pb2.TaskResponse()

    async def ListTasks(self, request, context):
        try:
            tasks = await self.agentService.listTasks(userId=request.userId)
            return agents_pb2.ListTasksResponse(
                tasks=[
                    agents_pb2.TaskResponse(
                        taskId=t.get("id", ""),
                        status=t.get("status", ""),
                        goal=t.get("goal", ""),
                        createdAt=str(t.get("createdAt", "")),
                    )
                    for t in tasks
                ]
            )
        except Exception as e:
            logger.error(f"AgentsServer.ListTasks failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agents_pb2.ListTasksResponse()

    async def CancelTask(self, request, context):
        try:
            success = await self.agentService.cancelTask(
                taskId=request.taskId, userId=request.userId
            )
            return agents_pb2.CancelTaskResponse(success=success)
        except Exception as e:
            logger.error(f"AgentsServer.CancelTask failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return agents_pb2.CancelTaskResponse(success=False)


class AgentsGrpcServer(BaseGrpcServer):
    def __init__(self):
        super().__init__(
            serviceName="AgentsService",
            port=int(os.getenv("AGENTS_GRPC_PORT", "50053")),
        )

    def registerServices(self, server):
        agents_pb2_grpc.add_AgentsServiceServicer_to_server(
            AgentsServiceHandler(), server
        )
