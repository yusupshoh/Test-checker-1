from dataclasses import dataclass

from dotenv import load_dotenv

from .base import getenv, ImproperlyConfigured


@dataclass
class TelegramBotConfig:
    token: str
    channel_id: int
    admin_contact_name: str  
    admin_username: str     
    admin_phone: str 

@dataclass
class DatabaseConfig:
    host: str
    port: int
    name: str
    user: str
    password: str

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


@dataclass
class Config:
    tg_bot: TelegramBotConfig
    db: DatabaseConfig  


def load_config() -> Config:
    load_dotenv()

    return Config(
        tg_bot=TelegramBotConfig(
            token=getenv("BOT_TOKEN"),
            channel_id=int(getenv("CHANNEL_ID")),
            admin_contact_name=getenv("ADMIN_CONTACT_NAME"),
            admin_username=getenv("ADMIN_USERNAME"),
            admin_phone=getenv("ADMIN_PHONE"),),
        db=DatabaseConfig(
            host=getenv("DB_HOST"),
            port=int(getenv("DB_PORT")),
            name=getenv("DB_NAME"),
            user=getenv("DB_USER"),
            password=getenv("DB_PASSWORD"),
        )
    )