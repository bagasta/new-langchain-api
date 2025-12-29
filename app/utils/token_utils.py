"""
Token Utilities
Utility functions for estimating and tracking token usage
"""

import tiktoken
from typing import Any, Dict, Optional
from app.core.logging import logger


def estimate_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """
    Estimate the number of tokens in a text string for a given model.
    
    Args:
        text: The text to estimate tokens for
        model: The model name to use for tokenization
        
    Returns:
        Estimated number of tokens
    """
    try:
        # Get encoding for the model
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback to cl100k_base encoding (used by GPT-3.5 and GPT-4)
        logger.warning(f"Model {model} not found in tiktoken, using cl100k_base encoding")
        encoding = tiktoken.get_encoding("cl100k_base")
    
    # Encode and count tokens
    tokens = encoding.encode(text)
    return len(tokens)


def estimate_tokens_from_messages(messages: list, model: str = "gpt-3.5-turbo") -> int:
    """
    Estimate tokens from a list of messages (chat format).
    
    Args:
        messages: List of message dictionaries with 'role' and 'content'
        model: The model name to use for tokenization
        
    Returns:
        Estimated number of tokens including message formatting overhead
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        logger.warning(f"Model {model} not found in tiktoken, using cl100k_base encoding")
        encoding = tiktoken.get_encoding("cl100k_base")
    
    num_tokens = 0
    
    # Different models have different token overheads
    tokens_per_message = 3  # Every message follows <|start|>{role/name}\n{content}<|end|>\n
    tokens_per_name = 1  # If there's a name field
    
    if model.startswith("gpt-3.5-turbo"):
        tokens_per_message = 4
        tokens_per_name = -1
    elif model.startswith("gpt-4"):
        tokens_per_message = 3
        tokens_per_name = 1
    
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            if isinstance(value, str):
                num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    
    num_tokens += 3  # Every reply is primed with <|start|>assistant<|message|>
    
    return num_tokens


def estimate_json_tokens(data: Dict[str, Any], model: str = "gpt-3.5-turbo") -> int:
    """
    Estimate tokens from a JSON/dict object.
    
    Args:
        data: Dictionary to estimate tokens for
        model: The model name to use for tokenization
        
    Returns:
        Estimated number of tokens
    """
    import json
    
    # Convert to JSON string for token estimation
    json_str = json.dumps(data)
    return estimate_tokens(json_str, model)


def format_token_count(count: int) -> str:
    """
    Format token count for display.
    
    Args:
        count: Number of tokens
        
    Returns:
        Formatted string (e.g., "1.2K" or "1.5M")
    """
    if count < 1000:
        return str(count)
    elif count < 1_000_000:
        return f"{count / 1000:.1f}K"
    else:
        return f"{count / 1_000_000:.1f}M"


def calculate_remaining_tokens(token_limit: Optional[int], tokens_used: int) -> Optional[int]:
    """
    Calculate remaining tokens for an agent.
    
    Args:
        token_limit: Maximum tokens allowed (None = unlimited)
        tokens_used: Tokens already used
        
    Returns:
        Remaining tokens or None if unlimited
    """
    if token_limit is None:
        return None
    
    remaining = token_limit - tokens_used
    return max(0, remaining)


def has_tokens_available(token_limit: Optional[int], tokens_used: int, required_tokens: int = 0) -> bool:
    """
    Check if agent has tokens available.
    
    Args:
        token_limit: Maximum tokens allowed (None = unlimited)
        tokens_used: Tokens already used
        required_tokens: Tokens needed for operation
        
    Returns:
        True if tokens available or unlimited, False otherwise
    """
    if token_limit is None:
        return True
    
    remaining = calculate_remaining_tokens(token_limit, tokens_used)
    return remaining >= required_tokens
