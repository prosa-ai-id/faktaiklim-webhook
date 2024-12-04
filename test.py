import pika
from app.config import settings

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host=settings.RABBITMQ_HOST, port=settings.RABBITMQ_PORT)
)
print(connection)
