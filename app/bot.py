import pika
from bottle import Bottle
from bottle import request as bottle_request
from bottle import response

from app.config import settings

print("**", settings)


class BotHandlerMixin:
    def get_chat_id(self, data):
        """
        Method to extract chat id from telegram request.
        """
        chat_id = data["message"]["chat"]["id"]
        return str(chat_id)

    def get_message(self, data):
        """
        Method to extract message id from telegram request.
        """
        msg = data["message"]
        text = ""
        if "text" in msg:
            text = data["message"]["text"]
        else:
            if "photo" in msg:
                img_id = msg["photo"][-1]["file_id"]
                text = "TELEPHOTO-" + img_id
            elif "document" in msg:
                doc_id = msg["document"]["file_id"]
                text = "TELEFILE-" + doc_id
            elif "video" in msg:
                vid_id = msg["video"]["file_id"]
                text = "TELEVIDEO-" + vid_id
        return text


class TelegramBot(BotHandlerMixin, Bottle):
    def __init__(self):
        super(TelegramBot, self).__init__()
        self.route("/", callback=self.post_handler, method="POST")

    def post_handler(self):
        data = bottle_request.json
        chat_id = self.get_chat_id(data)
        message = self.get_message(data)
        qdata = chat_id + "+++" + message

        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST, port=settings.RABBITMQ_PORT
            )
        )
        channel = connection.channel()
        channel.queue_declare(queue="hoaxintel")

        channel.basic_publish(exchange="", routing_key="hoaxintel", body=qdata.encode())
        connection.close()
        print(f"PUSH TO QUEUE hoaxintel {qdata}")

        return response


if __name__ == "__main__":
    app = TelegramBot()
    app.run(host="0.0.0.0", port=8711, server="waitress")
