# pylint: disable=invalid-name
"""Various utility functions."""

import re
from typing import Any, Tuple

import openai
import requests
from emoji import replace_emoji
from PIL.ImageDraw import ImageDraw
from PIL.ImageFont import FreeTypeFont
from requests import Response
from tenacity import retry, stop_after_attempt, wait_random_exponential

from app import config

openai.api_key = config.OPENAI_API_KEY

HASHTAG_RE = re.compile(r"#[\wа-яА-ЯёЁ]+")


def break_text(text: str) -> Tuple[str, str]:
    """
    Break a text into two approximately equal-sized parts.

    Args:
        text: a text

    Return:
        text broken into two strings
    """
    middle_index = len(text) // 2
    left_words = text[:middle_index].strip().split()
    right_words = text[middle_index:].strip().split()

    if text[middle_index] != " ":
        middle_word = left_words[-1] + right_words[0]
        left_words, right_words = left_words[:-1], right_words[1:]

        if len(left_words[-1]) < len(right_words[0]):
            right_words = [middle_word] + right_words
        else:
            left_words.append(middle_word)

    return " ".join(left_words), " ".join(right_words)


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


def outline_text(
    draw: ImageDraw, font: FreeTypeFont, text: str, x: int, y: int
) -> None:
    """
    Write white text with a black outline on an image.

    Args:
        draw: Pillow ImageDraw object
        font: Pillow font object
        text: text to write
        x: x text coordinate
        y: y text coordinate
    """
    draw.text((x - 1, y), text, fill="black", font=font, anchor="ms")
    draw.text((x + 1, y), text, fill="black", font=font, anchor="ms")
    draw.text((x, y - 1), text, fill="black", font=font, anchor="ms")
    draw.text((x, y + 1), text, fill="black", font=font, anchor="ms")

    draw.text((x - 1, y - 1), text, fill="black", font=font, anchor="ms")
    draw.text((x + 1, y - 1), text, fill="black", font=font, anchor="ms")
    draw.text((x - 1, y - 1), text, fill="black", font=font, anchor="ms")
    draw.text((x + 1, y + 1), text, fill="black", font=font, anchor="ms")

    draw.text((x, y), text, fill="white", font=font, anchor="ms")
