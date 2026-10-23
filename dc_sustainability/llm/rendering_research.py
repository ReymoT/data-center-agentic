"""Offline Qwen3 legacy-template research; NOT an adopted prompt counter.

Only the pinned artifact and strict system/user/assistant text histories are
supported. This reproduces one Go-template path, not proof that Ollama takes it.
The provider deliberately does not import this module. No downloads, Go process,
tokenizer dependency, network operation, weight loading or inference occur here.
"""

import hashlib

TEMPLATE_SHA256 = "ae370d884f108d16e7cc8fd5259ebc5773a0afa6e078b11f4ed7e39a27e0dfc4"
REQUEST_KEYS = {"model", "messages", "format", "stream", "think", "keep_alive", "options"}


def _render_text_history(messages: list[dict[str, str]]) -> str:
    """Pure text expansion; golden vectors come from the real Go template engine."""
    if not isinstance(messages, list) or len(messages) < 2:
        raise ValueError("research history needs system then user, with optional text turns")
    for index, message in enumerate(messages):
        role = "system" if index == 0 else "user" if index % 2 else "assistant"
        if (
            not isinstance(message, dict)
            or set(message) != {"role", "content"}
            or message["role"] != role
            or not isinstance(message["content"], str)
            or not message["content"]
        ):
            raise ValueError("unsupported research history; text-only alternating turns required")
        # Go JSON input and the tokenizer operate on UTF-8. Never silently replace
        # a lone surrogate and then claim byte equivalence with the Python string.
        message["content"].encode("utf-8")
    last_user = max(i for i, message in enumerate(messages) if message["role"] == "user")
    parts = ["<|im_start|>system\n\n", messages[0]["content"], "<|im_end|>\n"]
    for index, message in enumerate(messages[1:], 1):
        parts.extend((f"<|im_start|>{message['role']}\n", message["content"]))
        if message["role"] == "user":
            if index == last_user:
                parts.append(" /no_think")
            parts.append("<|im_end|>\n")
        elif index != len(messages) - 1:
            parts.append("<|im_end|>\n")
    if messages[-1]["role"] == "user":
        parts.append("<|im_start|>assistant\n<think>\n\n</think>\n\n")
    return "".join(parts)


def render_candidate(request: dict, *, template_bytes: bytes) -> str:
    """Render the accepted request shape against a hash-verified research artifact.

    The schema remains in the request, with its identity retained by the research
    validator. Its runtime/grammar effects are NOT established by this rendering.
    This returns text, never a validated production token count or approval.
    """
    if hashlib.sha256(template_bytes).hexdigest() != TEMPLATE_SHA256:
        raise ValueError("template differs from the pinned research artifact")
    _validate_request(request)
    return _render_text_history(request["messages"])


def _validate_request(request: dict) -> None:
    """Check candidate scope independently of artifact I/O, never supply a count."""
    if not isinstance(request, dict) or set(request) != REQUEST_KEYS:
        raise ValueError("unsupported request keys; tools and other extensions are not counted")
    if (
        request["model"] != "qwen3:8b"
        or request["stream"] is not False
        or request["think"] is not False
        or request["keep_alive"] != "30m"
        or not isinstance(request["format"], dict)
        or not request["format"]
    ):
        raise ValueError("unsupported research request mode")
    options = request["options"]
    if not isinstance(options, dict) or set(options) != {
        "temperature",
        "top_p",
        "seed",
        "num_ctx",
        "num_predict",
    }:
        raise ValueError("research options must be explicit and unchanged")
    if (
        type(options["seed"]) is not int
        or options["seed"] < 0
        or type(options["temperature"]) is not float
        or options["temperature"] != 0.2
        or type(options["top_p"]) is not int
        or options["top_p"] != 1
        or type(options["num_ctx"]) is not int
        or options["num_ctx"] != 16384
        or type(options["num_predict"]) is not int
        or options["num_predict"] != 1536
    ):
        raise ValueError("unsupported research options; no hidden defaults")
