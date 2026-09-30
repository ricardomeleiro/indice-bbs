from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://indicebbs:indicebbs@db:5432/indicebbs"
    BASE_URL: str = "https://teste/bbs"
    ROOT_PATH: str = "/bbs"
    SECRET_KEY: str = "change-me"

    DEFAULT_USER_EMAIL: str = "admin@c-innovation.com.br"
    DEFAULT_USER_NAME: str = "Administrador"
    DEFAULT_USER_ROLE: str = "admin"

    TZ: str = "America/Sao_Paulo"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
