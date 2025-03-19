#!/usr/bin/env python
import datetime as dt
import json
import os
import sys
import time
from multiprocessing import Pool
from urllib.parse import quote

import pika
import requests

from app.config import settings
from app.database import log_article_search
from app.topic import get_topic_combined

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
        cleaned_query = query.strip().rstrip("'")
        encoded_query = quote(cleaned_query)
        bing_url = f"https://bing.com/search?q={encoded_query}"
        # Format URL for Telegram HTML parsing while showing the URL
        return f'<a href="{bing_url}">{bing_url}</a>'

    def get_docstring(self, docs):
        result = ""
        for i, d in enumerate(docs):
            result += f"{str(i + 1)}. {d['title']}\n"
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
            verdict_str = ""
            if hoax_probability <= 0.01:
                verdict_str = "tidak terdeteksi sebagai hoaks"
            elif hoax_probability <= 0.5:
                verdict_str = "kemungkinan kecil berpotensi sebagai hoaks"
            elif hoax_probability <= 0.8:
                verdict_str = "cenderung berpotensi sebagai hoaks"
            else:
                verdict_str = "kemungkinan besar berpotensi sebagai hoaks"
            if verdict_flag == "FACT":
                answer_str = (
                    fact_message.format(
                        topic=topic, articles=articles, verdict_str=verdict_str
                    ),
                    "HTML",
                )
            elif verdict_flag == "HOAX":
                answer_str = (
                    hoax_message.format(
                        topic=topic, articles=articles, verdict_str=verdict_str
                    ),
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

        try:
            r = requests.post(
                settings.HOAX_CHECK_API, json.dumps({"text": text}), headers=headers
            )

            if r is None:
                log_article_search(
                    user_id=chat_id,
                    search_query=text,
                    status="error",
                    hoax_probability=None,
                    topic=None,
                    response_json=None,
                )
                return "Mohon maaf, Saya sedang tidak tersambung dengan Sistem Anti Hoax Climate, mohon tunggu beberapa saat lagi."

            result = r.json()

            # ChitChat
            if "chitchat_answer" in result and result["chitchat_answer"]:
                log_article_search(
                    user_id=chat_id,
                    search_query=text,
                    status="chitchat",
                    hoax_probability=None,
                    topic=None,
                    response_json=result,
                )
                return result["chitchat_answer"]

            if "relevant_items" not in result:
                print(f"ERROR: no 'relevant_items' IN HOAX API RESPONSE: {result}")
                result = {"relevant_items": [], "hoax_probability": 0}

            verdict = self.get_verdict_flag(result)

            # Get both topic string and data with a single API call
            topic, topic_data = get_topic_combined(text)

            # Log the successful API call
            log_article_search(
                user_id=chat_id,
                search_query=text,
                status="success",
                hoax_probability=result.get("hoax_probability", 0),
                topic=topic,
                response_json={"result": topic_data},
            )

            answer = self.generate_answer_str(result, verdict, text, topic)
            return answer

        except Exception as e:
            # Log the error
            log_article_search(
                user_id=chat_id,
                search_query=text,
                status="error",
                hoax_probability=None,
                topic=None,
                response_json={"error": str(e)},
            )
            print(f"Error in get_verdict: {e}")
            return "Mohon maaf, terjadi kesalahan dalam sistem kami. Silakan coba beberapa saat lagi."

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
    try:
        t = str(text)
        print(f"RECEIVED FROM QUEUE {t}")
        # Extract chat_id early for error handling
        chat_id = t.split("+++")[0][2:]

        answer_data = tr.prepare_data_for_answer(t)
        r = tr.send_message(answer_data)
        i = 0

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

    except Exception as e:
        print(f"Error: {e}")
        try:
            # Try to send error message to the user using the already extracted chat_id
            error_data = {
                "chat_id": chat_id,  # We extracted this at the start of the try block
                "text": "Maaf terjadi kesalahan dalam sistem kami, silakan coba beberapa saat lagi.",
                "parse_mode": None,
            }
            tr.send_message(error_data)

            # Log the error
            message_log_fname = "./logs/message_log.tsv"
            with open(message_log_fname, "a") as f:
                datetime = "T".join(str(dt.datetime.now()).split())
                error_row = (
                    f'{chat_id}\t"ERROR"\t"System Error: {str(e)}"\t500\t{datetime}\n'
                )
                f.write(error_row)

            failedcount += 1

        except Exception as inner_e:
            # If even error handling fails, just log it
            print(f"Failed to handle error: {inner_e}")
            failedcount += 1


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
