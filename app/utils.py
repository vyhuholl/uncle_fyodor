"""Various utility functions."""

import re
from typing import Any, Tuple

import openai
import requests
from emoji import replace_emoji
from requests import Response
from tenacity import retry, stop_after_attempt, wait_random_exponential

from app import config

openai.api_key = config.OPENAI_API_KEY

HASHTAG_RE = re.compile(r"#[\wа-яА-ЯёЁ]+")


def break_text(text: str) -> Tuple[str, str]:
    """
    Break a text into two approximately equal-sized parts.
    """
    words = text.split()
    break_index = len(words) // 2
    return " ".join(words[:break_index]), " ".join(words[break_index:])


def clean_text(text: str) -> str:
    """
    Remove hashtags, start and end quotes and ending punctuation.

    Args:
        text: a text

    Returns:
        cleaned text
    """
    return (
        HASHTAG_RE.sub("", replace_emoji(text.strip('"')))
        .strip()
        .rstrip(".")
        .rstrip("!")
    )


@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def completion_with_backoff(**kwargs: Any) -> openai.ChatCompletion:
    """
    Create OpenAI chat completion with backoff (to avoid rate limit error).
    (see https://platform.openai.com/docs/guides/rate-limits/error-mitigation)

    Args:
        **kwargs: keyword arguments for chat completion

    Returns:
        chat completion with backoff
    """
    return openai.ChatCompletion.create(**kwargs)


@retry(
    wait=wait_random_exponential(min=1, max=300), stop=stop_after_attempt(6)
)
def post_request_with_backoff(url: str, **kwargs: Any) -> Response:
    """
    Make POST request with 6 retries.

    Args:
        url: request
        **kwargs: keyword arguments for response

    Returns:
        response
    """
    response = requests.post(url, **kwargs)  # pylint: disable=missing-timeout
    response.raise_for_status()
    return response
