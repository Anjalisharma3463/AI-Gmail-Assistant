# /agent/agent_router.py

from fastapi import APIRouter, Request
from pydantic import BaseModel

from .agent_runner import get_agent

router = APIRouter()

class AgentQueryRequest(BaseModel):
    query: str

@router.post("/agent_query")
async def agent_query(request: Request, body: AgentQueryRequest):
    agent = get_agent()
    result = agent.invoke({"input": body.query})
    return {"response": result}
