from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BOT_TOKEN: str
    IIKO_API_KEY: str = ""
    IIKO_SERVER_URL: str = "https://mister-kruassan.iiko.it/resto/api"
    IIKO_LOGIN: str = "balandin"
    IIKO_PASSWORD: str = ""
    GEMINI_API_KEY: str
    DATABASE_URL: str
    BASE_URL: str
    SECRET_KEY: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
