from sqlmodel import create_engine, Session
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./todo_chatbot.db")

engine = create_engine(DATABASE_URL, echo=True)

def get_db_session():
    return Session(engine)

def create_tables():
    from models import Task, Conversation, Message
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(engine)
