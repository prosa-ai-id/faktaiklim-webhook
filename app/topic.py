import json
from typing import List

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


def get_topic(text: str) -> str:
    # print(f"INPUT TEXT FOR /topic : {text[:100]}..")
    print(f"INPUT TEXT FOR /topic : {text}..")

    topic2score = predict_doc_multi_cls(settings.TOPIC_SERVING_URL, text)

    # subtopic_url = SUBTOPIC_SERVING_URL
    # subtopic_text = self.get_subtopic_text(topic2score.keys(), text)
    # subtopic2score = predict_doc_multi_cls(subtopic_url, subtopic_text)

    # result = {
    #     "topic": topic2score,
    #     "subtopic": subtopic2score
    # }
    # return result
    topics = topic2score.keys()
    if not topics:
        topics = ["unknown"]
    topics = [to_title_case(t) for t in topics]
    return ", ".join(topics)


if __name__ == "__main__":
    text = "Forum B20 dorong kolaborasi publik dan swasta jalankan transisi energi. Forum dialog antar komunitas bisnis global B20 mendorong kolaborasi sektor publik dan swasta untuk menjalankan program transisi energi dalam mengurangi emisi dan menahan kenaikan rata-rata suhu bumi agar tidak melewati ambang batas 1,5 derajat Celcius."
    topic = get_topic(text)
    print(topic)
