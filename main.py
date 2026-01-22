from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import logging
from mcp_server import handle_tool_call, TOOLS
from database import create_tables

# --- Logging setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FastAPI app ---
app = FastAPI(title="Todo AI Chatbot API", version="1.0.0")

# --- CORS middleware (updated for Vercel frontend) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://phase-iii-frontend.vercel.app"  # <-- deployed frontend URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Startup event to create tables ---
@app.on_event("startup")
async def startup_event():
    create_tables()
    logger.info("Database tables created/verified")

# --- Request/Response models ---
class ChatRequest(BaseModel):
    conversation_id: Optional[int] = None
    message: str

class ChatResponse(BaseModel):
    conversation_id: int
    response: str

# --- Health check and root ---
@app.get("/")
def read_root():
    return {"message": "Todo AI Chatbot API", "status": "running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# --- Chat endpoint ---
@app.post("/api/{user_id}/chat")
async def chat_with_bot(user_id: str, request: ChatRequest):
    try:
        message = request.message.lower()

        # --- Add task ---
        if "add" in message or "create" in message:
            title = extract_task_title(message)
            if title:
                result = handle_tool_call(
                    "add_task",
                    user_id=user_id,
                    title=title,
                    description=f"Added via chat: {request.message}"
                )
                response = f"✅ Task added: {result.get('title', 'Unknown')}"
            else:
                response = "❌ Could not extract task title. Please specify what task to add."

        # --- List tasks ---
        elif "list" in message or "show" in message:
            status = "all"
            if "pending" in message:
                status = "pending"
            elif "completed" in message or "done" in message:
                status = "completed"
            tasks = handle_tool_call("list_tasks", user_id=user_id, status=status)
            if tasks:
                response = f"📋 Your {status} tasks:\n" + "\n".join([
                    f"• {task['id']}: {task['title']} ({'✅' if task['completed'] else '⏳'})"
                    for task in tasks
                ])
            else:
                response = f"📭 No {status} tasks found."

        # --- Complete task ---
        elif "complete" in message or "done" in message or "finish" in message:
            task_id = extract_task_id(message)
            if task_id:
                result = handle_tool_call("complete_task", user_id=user_id, task_id=task_id)
                response = f"✅ Task completed: {result.get('title', 'Unknown')}" if "task_id" in result else f"❌ {result.get('error', 'Unknown error')}"
            else:
                response = "❌ Could not identify task ID. Please specify which task to complete."

        # --- Delete task ---
        elif "delete" in message or "remove" in message:
            task_id = extract_task_id(message)
            if task_id:
                result = handle_tool_call("delete_task", user_id=user_id, task_id=task_id)
                response = f"🗑️ Task deleted: {result.get('title', 'Unknown')}" if "task_id" in result else f"❌ {result.get('error', 'Unknown error')}"
            else:
                response = "❌ Could not identify task ID. Please specify which task to delete."

        # --- Update task ---
        elif "update" in message or "change" in message:
            task_id = extract_task_id(message)
            new_title = extract_task_title(message)
            if task_id and new_title:
                result = handle_tool_call("update_task", user_id=user_id, task_id=task_id, title=new_title)
                response = f"✏️ Task updated: {result.get('title', 'Unknown')}" if "task_id" in result else f"❌ {result.get('error', 'Unknown error')}"
            else:
                response = "❌ Could not identify task ID or new title."

        # --- Default response ---
        else:
            response = """🤖 I'm your Todo AI assistant! I can help you manage tasks. Try:
• "Add a task to buy groceries"
• "Show me all my tasks"
• "Mark task 1 as complete"
• "Delete task 2"
• "What's pending?" """

        return ChatResponse(conversation_id=request.conversation_id or 1, response=response)

    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# --- Helper functions ---
def extract_task_title(message: str) -> Optional[str]:
    import re
    patterns = [
        r"add\s+(?:a\s+)?task\s+(?:to\s+)?(.+)",
        r"create\s+(?:a\s+)?task\s+(?:to\s+)?(.+)",
        r"(.+)\s+to\s+(?:my\s+)?(?:todo|task)"
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return message.strip()

def extract_task_id(message: str) -> Optional[int]:
    import re
    match = re.search(r'(?:task\s+)?(\d+)', message, re.IGNORECASE)
    return int(match.group(1)) if match else None
