from typing import List, Optional
from backend.api import session_manager
from backend.schemas import SessionResponse

class SessionService:
    @staticmethod
    def create_session(workspace: str) -> dict:
        return session_manager.create_session(workspace)

    @staticmethod
    def list_sessions(workspace: Optional[str] = None) -> List[dict]:
        return session_manager.list_sessions(workspace)

    @staticmethod
    def get_session(session_id: str) -> Optional[dict]:
        return session_manager.get_session(session_id)

    @staticmethod
    def delete_session(session_id: str):
        session_manager.delete_session(session_id)

    @staticmethod
    def rename_session(session_id: str, title: str):
        session_manager.update_session_title(session_id, title)
