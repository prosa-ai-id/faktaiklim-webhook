import json
from typing import Dict, List, Tuple

from requests import post

from app.config import settings


def predict_doc_multi_cls(url: str, text: str) -> dict:
    data = {"inputs": [text]}
    r = {}
    try:
        r = post(url, data=json.dumps(data)).json()
        r = r["output"][0]
    except Exception as e:
        print(f"FAILED DURING API CALL (predict_doc_multi_cls). url: {url}")
        print(e)
    return r


def get_subtopic_text(topics: List[str], text: str) -> str:
    if not topics:
        return text
    topics_str = "\n".join(topics)
    subtopic_text = f"TOPIK ARTIKEL:\n{topics_str}\nTEKS BERITA:\n{text}"
    # print(f"\nSUBTOPIC TEXT:\n{subtopic_text[:200]}..")
    return subtopic_text


def to_title_case(text: str) -> str:
    if not text:
        return text

    return " ".join(word[0].upper() + word[1:].lower() for word in text.split())


def get_topic_combined(text: str) -> Tuple[str, Dict]:
    """
    Get both formatted topic string and raw topic data with a single API call

    Returns:
        Tuple containing (formatted_topic_string, raw_topic_data)
    """
    print(f"INPUT TEXT FOR /topic : {text}..")

    # Make topic API call once
    topic2score = predict_doc_multi_cls(settings.TOPIC_SERVING_URL, text)

    # Get subtopic data
    subtopic_text = get_subtopic_text(topic2score.keys(), text)
    subtopic2score = predict_doc_multi_cls(settings.SUBTOPIC_SERVING_URL, subtopic_text)

    # Format the topic string
    topics = topic2score.keys()
    if not topics:
        topics = ["unknown"]
    formatted_topics = [to_title_case(t) for t in topics]
    topic_string = ", ".join(formatted_topics)

    # Create the raw topic data dictionary
    topic_data = {"topic": topic2score, "subtopic": subtopic2score}

    return topic_string, topic_data
