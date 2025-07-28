"""
    Simple workaround script to get past TypeError: Type is not msgpack serializable 
    when adding memory to Agent
"""
from typing import Any

from langgraph.checkpoint.serde import jsonplus
from langgraph.checkpoint.serde.jsonplus import _msgpack_default
from langgraph.checkpoint.serde.jsonplus import _option
from langgraph.checkpoint.serde.jsonplus import ormsgpack


def message_to_dict(msg):
    # Handles HumanMessage, AIMessage, ToolMessage, etc.
    # https://github.com/langchain-ai/langgraph/issues/4956#issuecomment-2975362924
    if hasattr(msg, "to_dict"):
        return msg.to_dict()
    elif isinstance(msg, dict):
        return msg
    else:
        # Fallback: try to extract content and role
        return {"role": getattr(msg, "role", "user"), "content": str(getattr(msg, "content", msg))}


def _msgpack_enc(data: Any) -> bytes:
    return ormsgpack.packb(message_to_dict(data), default=_msgpack_default, option=_option)


def monkey_patch():
    setattr(jsonplus, "_msgpack_enc", _msgpack_enc)