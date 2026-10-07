from langchain_core.messages import AIMessage, HumanMessage

from backend.chat.memory import ConversationMemory, SessionManager


def test_memory_stores_messages_in_order():
    memory = ConversationMemory(max_turns=10)
    memory.add_user_message("hello")
    memory.add_ai_message("hi there")

    history = memory.get_history()
    assert len(history) == 2
    assert isinstance(history[0], HumanMessage)
    assert history[0].content == "hello"
    assert isinstance(history[1], AIMessage)
    assert history[1].content == "hi there"


def test_memory_trims_to_max_turns():
    memory = ConversationMemory(max_turns=2)

    memory.add_user_message("q1")
    memory.add_ai_message("a1")
    memory.add_user_message("q2")
    memory.add_ai_message("a2")
    memory.add_user_message("q3")
    memory.add_ai_message("a3")

    history = memory.get_history()
    assert len(history) == 4
    assert history[0].content == "q2"
    assert history[-1].content == "a3"


def test_memory_clear():
    memory = ConversationMemory()
    memory.add_user_message("hello")
    memory.clear()
    assert memory.get_history() == []


def test_formatted_history_uses_role_labels():
    memory = ConversationMemory()
    memory.add_user_message("q")
    memory.add_ai_message("a")

    formatted = memory.get_formatted_history()
    assert formatted == "Human: q\nAssistant: a"


def test_session_manager_reuses_and_deletes_sessions():
    manager = SessionManager(max_turns=5)

    memory = manager.get_memory("abc")
    memory.add_user_message("hello")
    assert manager.get_memory("abc") is memory
    assert manager.list_sessions() == ["abc"]

    assert manager.delete_session("abc") is True
    assert manager.delete_session("abc") is False
    assert manager.list_sessions() == []


def test_session_manager_isolates_sessions():
    manager = SessionManager()
    manager.get_memory("a").add_user_message("from a")
    manager.get_memory("b").add_user_message("from b")

    assert manager.get_memory("a").get_history()[0].content == "from a"
    assert manager.get_memory("b").get_history()[0].content == "from b"
