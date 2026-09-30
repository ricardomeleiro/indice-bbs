from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from dependencies import get_current_user_optional
from templating import templates
from routers import entries, dashboard, reports, admin, exports


app = FastAPI(
    title="Índice BBS por Embarcação",
    root_path=settings.ROOT_PATH,
    docs_url=None,
    redoc_url=None,
)

app.mount("/static", StaticFiles(directory="static"), name="static")


app.include_router(dashboard.router)
app.include_router(entries.router)
app.include_router(reports.router)
app.include_router(admin.router)
app.include_router(exports.router)


@app.get("/", response_class=HTMLResponse)
def root(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user:
        return PlainTextResponse(
            "Autenticação necessária.",
            status_code=401,
        )
    return RedirectResponse(request.url_for("dashboard_view"), status_code=302)


@app.get("/health", response_class=PlainTextResponse)
def health():
    return "ok"


@app.exception_handler(401)
async def unauthorized(request: Request, exc):
    return templates.TemplateResponse(
        "errors/401.html", {"request": request}, status_code=401
    )


@app.exception_handler(403)
async def forbidden(request: Request, exc):
    return templates.TemplateResponse(
        "errors/403.html", {"request": request, "detail": exc.detail},
        status_code=403,
    )


@app.exception_handler(404)
async def not_found(request: Request, exc):
    return templates.TemplateResponse(
        "errors/404.html", {"request": request}, status_code=404
    )
