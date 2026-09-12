from collections import deque

from langchain_core.messages import AIMessage, HumanMessage


class ConversationMemory:
    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self._history: deque = deque(maxlen=max_turns * 2)

    def add_user_message(self, content: str) -> None:
        self._history.append(HumanMessage(content=content))

    def add_ai_message(self, content: str) -> None:
        self._history.append(AIMessage(content=content))

    def get_history(self) -> list:
        return list(self._history)

    def clear(self) -> None:
        self._history.clear()

    def get_formatted_history(self) -> str:
        lines = []
        for msg in self._history:
            role = "Human" if isinstance(msg, HumanMessage) else "Assistant"
            lines.append(f"{role}: {msg.content}")
        return "\n".join(lines)


class SessionManager:
    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self._sessions: dict[str, ConversationMemory] = {}

    def get_memory(self, session_id: str) -> ConversationMemory:
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationMemory(self.max_turns)
        return self._sessions[session_id]

    def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def list_sessions(self) -> list[str]:
        return list(self._sessions.keys())
