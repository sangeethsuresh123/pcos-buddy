from langchain_core.messages import HumanMessage

from backend.chat.prompts import (
    PCOS_SYSTEM_PROMPT,
    get_chat_prompt,
    get_condense_prompt,
    get_rag_chain_prompt,
    get_rag_prompt,
)


def test_chat_prompt_includes_history_and_input():
    prompt = get_chat_prompt()
    messages = prompt.format_messages(
        input="What should I eat?",
        chat_history=[HumanMessage(content="I have PCOS")],
    )

    assert messages[0].content == PCOS_SYSTEM_PROMPT
    assert messages[1].content == "I have PCOS"
    assert messages[2].content == "What should I eat?"


def test_rag_chain_prompt_injects_context():
    prompt = get_rag_chain_prompt()
    messages = prompt.format_messages(
        input="question",
        chat_history=[],
        context="PCOS context here",
    )

    assert "PCOS context here" in messages[-1].content
    assert "Relevant medical context" in messages[-1].content


def test_rag_prompt_renders_context_and_question():
    rendered = get_rag_prompt().format(context="ctx", input="q")

    assert "ctx" in rendered
    assert "Question: q" in rendered


def test_condense_prompt_renders_history_and_input():
    rendered = get_condense_prompt().format(chat_history="Human: hi", input="and?")

    assert "Human: hi" in rendered
    assert "Follow Up Input: and?" in rendered
