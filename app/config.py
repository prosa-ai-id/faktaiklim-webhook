from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    TELEGRAM_API_ADDRESS: str = "https://api.telegram.org"
    TELEGRAM_TOKEN: SecretStr
    HOAX_CHECK_API: str
    HOAX_API_KEY: SecretStr

    RABBITMQ_HOST: str
    RABBITMQ_PORT: int

    TOPIC_SERVING_URL: str
    SUBTOPIC_SERVING_URL: str

    DB_PATH: str

    class Config:
        env_file = ".env"


settings = Config()  # type: ignore

__import__("pprint").pprint(settings.__dict__)
