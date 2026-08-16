from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://indicebbs:indicebbs@db:5432/indicebbs"
    BASE_URL: str = "https://hub.c-innovation.com.br/bbs"
    ROOT_PATH: str = "/bbs"
    SECRET_KEY: str = "change-me"

    AUTHENTIK_HEADER_EMAIL: str = "x-authentik-email"
    AUTHENTIK_HEADER_USERNAME: str = "x-authentik-username"
    AUTHENTIK_HEADER_NAME: str = "x-authentik-name"
    AUTHENTIK_HEADER_GROUPS: str = "x-authentik-groups"

    BBS_ADMIN_GROUP: str = "bbs-admin"
    BBS_EDITOR_GROUP: str = "bbs-editor"

    DEV_MODE: int = 0
    DEV_USER_EMAIL: str = "dev@c-innovation.com.br"
    DEV_USER_NAME: str = "Dev User"
    DEV_USER_ROLE: str = "admin"

    TZ: str = "America/Sao_Paulo"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
