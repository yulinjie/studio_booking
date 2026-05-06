from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .config import settings
from .database import init_db
from .routers import auth, members, cards, courses, bookings, admin, payroll, growth, coupons, reports, evaluations, topup


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True, "name": settings.app_name}


app.include_router(auth.router)
app.include_router(members.router)
app.include_router(cards.router)
app.include_router(courses.router)
app.include_router(bookings.router)
app.include_router(admin.router)
app.include_router(payroll.router)
app.include_router(growth.router)
app.include_router(coupons.router)
app.include_router(reports.router)
app.include_router(reports.practice_router)
app.include_router(evaluations.router)
app.include_router(topup.router)


# ===== 用户上传文件目录 =====
_uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
_uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_uploads_dir), name="uploads")


# ===== 前端静态文件 =====
# 前端 vite 构建到 backend/static/，由 FastAPI 直接提供。
# 路由用 hash 模式，所以根路径返回 index.html 即可，不需要 SPA fallback。
_static_dir = Path(__file__).resolve().parent.parent / "static"
if _static_dir.exists():
    app.mount("/assets", StaticFiles(directory=_static_dir / "assets"), name="assets")

    @app.get("/")
    def _index():
        return FileResponse(_static_dir / "index.html")

    @app.get("/{full_path:path}")
    def _spa(full_path: str):
        # /api/** 已经被前面的 router 拦截了；这里兜底所有其他路径
        target = _static_dir / full_path
        if target.is_file():
            return FileResponse(target)
        return FileResponse(_static_dir / "index.html")
