#!/usr/bin/env python
import datetime as dt
import json
import os
import random
import sys
import time
from multiprocessing import Pool

import pika
import requests

from app.config import settings
from app.topic import get_topic

with open("./app/resources/welcome.html") as f:
    welcome_message = f.read().strip()
with open("./app/resources/hoax.html") as f:
    hoax_message = f.read().strip()
with open("./app/resources/fact.html") as f:
    fact_message = f.read().strip()
with open("./app/resources/unknown.html") as f:
    unknown_message = f.read().strip()


class TelegramReceive:
    def __init__(self):
        self.BOT_URL = (
            settings.TELEGRAM_API_ADDRESS
            + "/bot"
            + settings.TELEGRAM_TOKEN.get_secret_value()
            + "/"
        )

    def rehtml(self, text):
        text = str(text)
        return "<br>".join(text.split("\\n"))

    def get_file(self, fid):
        # get file path using getFile api
        r = requests.get(self.BOT_URL + "getFile?file_id=" + fid)
        if r is None:
            print("failed to get address")
            return "failed to get address"
        address = None
        if "result" in r.json():
            address = r.json()["result"]["file_path"]
        else:
            print(f"no result field : {r.json()}")
            return "failed to get address"
        # get file using get
        file_path = (
            settings.TELEGRAM_API_ADDRESS
            + "/file/bot"
            + settings.TELEGRAM_TOKEN.get_secret_value()
            + "/"
            + address
        )
        return file_path

    def get_bing(self, query):
        q = "+".join(query.split())
        bing_url = f"https://bing.com/search?q={q}"
        return bing_url

    def get_docstring(self, docs):
        result = ""
        for i, d in enumerate(docs):
            verdict = "FACT"
            if "classification" in d:
                verdict = d["classification"]
            result += f"{str(i+1)}. ({verdict}) {d['title']}\n"
            if "url" in d:
                url = d["url"]
            else:
                url = ""
            result += "url : " + url + "\n\n"
        return result

    def generate_answer_str(self, result, verdict_flag, query, topic):
        hoax_probability = result["hoax_probability"]
        articles = self.get_docstring(result["relevant_items"])
        answer_str = "empty answer"

        if verdict_flag == "UNKNOWN":
            articles = self.get_bing(query)
            answer_str = (
                unknown_message.format(topic=topic, articles=articles),
                "HTML",
            )
        else:
            answer_str = f"Climate Category: {topic}\n"
            if verdict_flag == "FACT":
                answer_str = (
                    fact_message.format(topic=topic, articles=articles),
                    "HTML",
                )
            elif verdict_flag == "HOAX":
                answer_str = (
                    hoax_message.format(topic=topic, articles=articles),
                    "HTML",
                )
            # answer_str += "\n" + docstring
        return answer_str

    def get_verdict_flag(self, result):
        hoax_probability = result["hoax_probability"]
        verdict = "UNKNOWN"
        if len(result["relevant_items"]):
            verdict = "FACT" if hoax_probability == 0 else "HOAX"
        return verdict

    def get_verdict(self, text, chat_id):
        if len(text.strip().split()) == 1 and "help" in text or "start" in text:
            return (welcome_message, "HTML")

        # handle non-text type input
        is_text = (
            len(set(["TELEPHOTO", "TELEFILE", "TELEVIDEO"]) & set(text.split("-"))) == 0
        )
        if not is_text:
            # file_address = self.get_file(text.split("-")[1][:-1])
            return "Untuk saat ini saya belum bisa menganalisa input berbentuk gambar / file / video. mohon sertakan deskripsi dari file terkait agar bisa dianalisis hoax intel"

        # handle text input
        headers = {
            "content-type": "application/json",
            "x-api-key": settings.HOAX_API_KEY.get_secret_value(),
        }
        r = requests.post(
            settings.HOAX_CHECK_API, json.dumps({"text": text}), headers=headers
        )
        if r is None:
            return "mohon maaf, saya sedang tidak tersambung dengan Sistem Anti Hoax Climate, mohon tunggu beberapa saat lagi"
        result = r.json()

        if "relevant_items" not in result:
            print(f"ERROR: no 'relevant_items' IN HOAX API RESPONSE: {result}")
            result = {"relevant_items": [], "hoax_probability": 0}

        verdict = self.get_verdict_flag(result)
        topic = get_topic(text)
        answer = self.generate_answer_str(result, verdict, text, topic)
        return answer

    def prepare_data_for_answer(self, data):
        chat_id = int(data.split("+++")[0][2:])
        print("prepare_data_for_answer")
        answer = self.get_verdict(data.split("+++")[1], chat_id)

        if isinstance(answer, tuple):
            answer, parse_mode = answer
        else:
            parse_mode = None

        json_data = {
            "chat_id": chat_id,
            "text": answer,
            "parse_mode": parse_mode,
        }
        return json_data

    def send_message(self, prepared_data):
        """
        Prepared data should be json which includes at least `chat_id` and `text`
        """

        message_url = (
            self.BOT_URL
            + f"sendMessage?chat_id={prepared_data['chat_id']}&text={prepared_data['text']}"
        )

        if "parse_mode" in prepared_data and prepared_data["parse_mode"] is not None:
            message_url = message_url + f"&parse_mode={prepared_data['parse_mode']}"
        r = requests.get(message_url)
        return r


failedcount, successcount = 0, 0


def callback(ch, method, properties, text):
    global failedcount, successcount
    tr = TelegramReceive()
    t = str(text)
    print(f"RECEIVED FROM QUEUE {t}")
    answer_data = tr.prepare_data_for_answer(t)
    r = tr.send_message(answer_data)
    i = 0
    # ch.basic_ack(delivery_tag = method.delivery_tag)
    while r.status_code == 429 and i <= 2:
        print("resend")
        time.sleep(0.1)
        r = tr.send_message(answer_data)
        i += 1
    else:
        if r.status_code == 429:
            # repush message to queue
            print("repush")
            failedcount += 1
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=settings.RABBITMQ_HOST,
                    port=settings.RABBITMQ_PORT,
                )
            )
            channel = connection.channel()
            channel.queue_declare(queue="hoaxintel")
            channel.basic_publish(exchange="", routing_key="hoaxintel", body=text)
            connection.close()
        else:
            successcount += 1
    # Write query to log
    message_log_fname = "./logs/message_log.tsv"
    f = None
    if not os.path.exists(f"{message_log_fname}"):
        row = "chat_id\tmessage\tanswer\tstatus_code\tdatetime\n"
        f = open(message_log_fname, "a")
        f.write(row)
    else:
        f = open(message_log_fname, "a")

    chat_id = t.split("+++")[0][2:]
    message = '"' + t.split("+++")[1][:-1] + '"'
    answer = '"' + answer_data["text"] + '"'
    datetime = "T".join(str(dt.datetime.now()).split())
    row = (
        chat_id
        + "\t"
        + message
        + "\t"
        + answer
        + "\t"
        + str(r.status_code)
        + "\t"
        + datetime
        + "\n"
    )
    f.write(row)
    f.close()
    print(f"success count {successcount}, failed count {failedcount}")


def receiver(callback):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
        )
    )
    channel = connection.channel()
    channel.queue_declare(queue="hoaxintel")
    # channel.basic_consume(callback, queue='hoaxintel', no_ack=True)
    channel.basic_consume(
        on_message_callback=callback, queue="hoaxintel", auto_ack=True
    )
    print(" [*] Waiting for messages. To exit press CTRL+C")
    channel.start_consuming()


if __name__ == "__main__":
    numprocess = int(sys.argv[1])
    pool = Pool(processes=numprocess)
    pool.map(receiver, [callback] * numprocess)
