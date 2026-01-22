from typing import Any, Dict, List
from models import Task
from database import get_db_session
from sqlmodel import select
from datetime import datetime

# --- MCP Tool class ---
class Tool:
    def __init__(self, name: str, description: str, inputSchema: dict, func):
        self.name = name
        self.description = description
        self.inputSchema = inputSchema
        self.func = func

# --- Tools List ---
TOOLS: List[Tool] = []

# --- Add Task Tool ---
def add_task_tool(user_id: str, title: str, description: str = "") -> Dict[str, Any]:
    with get_db_session() as session:
        task = Task(user_id=user_id, title=title, description=description, completed=False)
        session.add(task)
        session.commit()
        session.refresh(task)
        return {"task_id": task.id, "status": "created", "title": task.title}

TOOLS.append(Tool(
    name="add_task",
    description="Create a new task",
    inputSchema={
        "type": "object",
        "properties": {
            "user_id": {"type": "string"},
            "title": {"type": "string"},
            "description": {"type": "string"}
        },
        "required": ["user_id", "title"]
    },
    func=add_task_tool
))

# --- List Tasks Tool ---
def list_tasks_tool(user_id: str, status: str = "all") -> List[Dict[str, Any]]:
    with get_db_session() as session:
        query = select(Task).where(Task.user_id == user_id)
        tasks = session.exec(query).all()
        if status == "pending":
            tasks = [t for t in tasks if not t.completed]
        elif status == "completed":
            tasks = [t for t in tasks if t.completed]
        return [{"id": t.id, "title": t.title, "completed": t.completed} for t in tasks]

TOOLS.append(Tool(
    name="list_tasks",
    description="Retrieve tasks",
    inputSchema={
        "type": "object",
        "properties": {
            "user_id": {"type": "string"},
            "status": {"type": "string", "enum": ["all", "pending", "completed"]}
        },
        "required": ["user_id"]
    },
    func=list_tasks_tool
))

# --- Complete Task Tool ---
def complete_task_tool(user_id: str, task_id: int) -> Dict[str, Any]:
    with get_db_session() as session:
        task = session.get(Task, task_id)
        if not task or task.user_id != user_id:
            raise ValueError("Task not found")
        task.completed = True
        task.updated_at = datetime.utcnow()
        session.add(task)
        session.commit()
        session.refresh(task)
        return {"task_id": task.id, "status": "completed", "title": task.title}

TOOLS.append(Tool(
    name="complete_task",
    description="Mark task as complete",
    inputSchema={
        "type": "object",
        "properties": {
            "user_id": {"type": "string"},
            "task_id": {"type": "integer"}
        },
        "required": ["user_id", "task_id"]
    },
    func=complete_task_tool
))

# --- Update Task Tool ---
def update_task_tool(user_id: str, task_id: int, title: str = None, description: str = None) -> Dict[str, Any]:
    with get_db_session() as session:
        task = session.get(Task, task_id)
        if not task or task.user_id != user_id:
            raise ValueError("Task not found")
        if title:
            task.title = title
        if description:
            task.description = description
        task.updated_at = datetime.utcnow()
        session.add(task)
        session.commit()
        session.refresh(task)
        return {"task_id": task.id, "status": "updated", "title": task.title}

TOOLS.append(Tool(
    name="update_task",
    description="Update task title or description",
    inputSchema={
        "type": "object",
        "properties": {
            "user_id": {"type": "string"},
            "task_id": {"type": "integer"},
            "title": {"type": "string"},
            "description": {"type": "string"}
        },
        "required": ["user_id", "task_id"]
    },
    func=update_task_tool
))

# --- Delete Task Tool ---
def delete_task_tool(user_id: str, task_id: int) -> Dict[str, Any]:
    with get_db_session() as session:
        task = session.get(Task, task_id)
        if not task or task.user_id != user_id:
            raise ValueError("Task not found")
        session.delete(task)
        session.commit()
        return {"task_id": task.id, "status": "deleted", "title": task.title}

TOOLS.append(Tool(
    name="delete_task",
    description="Delete a task",
    inputSchema={
        "type": "object",
        "properties": {
            "user_id": {"type": "string"},
            "task_id": {"type": "integer"}
        },
        "required": ["user_id", "task_id"]
    },
    func=delete_task_tool
))

# --- Handle Tool Call ---
def handle_tool_call(tool_name: str, **kwargs) -> Any:
    """
    Call the appropriate MCP tool by name.
    """
    for tool in TOOLS:
        if tool.name == tool_name:
            return tool.func(**kwargs)
    raise ValueError(f"Tool '{tool_name}' not found")
