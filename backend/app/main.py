from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .config import settings
from .database import init_db
from .routers import auth, members, cards, courses, bookings, admin, payroll, growth, share, coupons, reports, evaluations, topup, birthday, backups, selfserve, staff


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

# 响应压缩 — 对 ≥1KB 的响应自动 gzip。前端 JS/CSS 实测能压到 1/4 大小
app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=6)


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
app.include_router(share.router)
app.include_router(coupons.router)
app.include_router(reports.router)
app.include_router(reports.practice_router)
app.include_router(evaluations.router)
app.include_router(topup.router)
app.include_router(birthday.router)
app.include_router(backups.router)
app.include_router(selfserve.router)
app.include_router(staff.router)


# ===== 用户上传文件目录 =====
# 也走 CachedStatic，享受同样的 gzip + 强缓存（图片 hash 文件名 = uuid，不会变）
_uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
_uploads_dir.mkdir(exist_ok=True)


# ===== 前端静态文件 =====
# 前端 vite 构建到 backend/static/，由 FastAPI 直接提供。
# 路由用 hash 模式，所以根路径返回 index.html 即可，不需要 SPA fallback。
import gzip as _gzip
from fastapi import Response as _Response


class CachedStatic(StaticFiles):
    """vite 的 /assets/* 文件名带内容 hash，可永久强缓存。
    同时按需 gzip 压缩（Starlette GZipMiddleware 对 mount 的 StaticFiles 不可靠）。
    """
    _gzip_cache = {}    # path -> bytes

    async def get_response(self, path, scope):
        # 检查客户端是否接受 gzip
        accept = ""
        for k, v in scope.get("headers", []):
            if k == b"accept-encoding":
                accept = v.decode().lower()
                break
        wants_gzip = "gzip" in accept

        # 仅对 .js / .css 这类文本资源压缩（lucide hash 文件 ≥1KB 的）
        is_text = path.endswith((".js", ".css", ".html", ".json", ".svg", ".map", ".txt"))

        if wants_gzip and is_text:
            cache_key = (path, "gz")
            if cache_key not in self._gzip_cache:
                # 一次性读文件并压缩，缓存内存
                full = self.directory / path
                try:
                    raw = full.read_bytes()
                    if len(raw) >= 1024:
                        self._gzip_cache[cache_key] = _gzip.compress(raw, compresslevel=6)
                    else:
                        self._gzip_cache[cache_key] = None
                except Exception:
                    self._gzip_cache[cache_key] = None
            compressed = self._gzip_cache.get(cache_key)
            if compressed:
                # 推断 content-type
                ext = path.rsplit(".", 1)[-1].lower()
                ctype = {
                    "js": "application/javascript", "css": "text/css", "html": "text/html",
                    "json": "application/json", "svg": "image/svg+xml", "map": "application/json",
                    "txt": "text/plain",
                }.get(ext, "application/octet-stream")
                return _Response(
                    content=compressed,
                    headers={
                        "Content-Type": ctype + "; charset=utf-8" if ctype.startswith("text") or "javascript" in ctype or "json" in ctype else ctype,
                        "Content-Encoding": "gzip",
                        "Cache-Control": "public, max-age=31536000, immutable",
                        "Vary": "Accept-Encoding",
                    },
                )

        # 不压缩 / 不命中缓存的兜底
        resp = await super().get_response(path, scope)
        if resp.status_code == 200:
            resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            resp.headers["Vary"] = "Accept-Encoding"
        return resp


app.mount("/uploads", CachedStatic(directory=_uploads_dir), name="uploads")

_static_dir = Path(__file__).resolve().parent.parent / "static"
if _static_dir.exists():
    app.mount("/assets", CachedStatic(directory=_static_dir / "assets"), name="assets")

    @app.get("/")
    def _index():
        return FileResponse(_static_dir / "index.html", headers={"Cache-Control": "no-cache"})

    @app.get("/{full_path:path}")
    def _spa(full_path: str):
        # /api/** 已经被前面的 router 拦截了；这里兜底所有其他路径
        target = _static_dir / full_path
        if target.is_file():
            return FileResponse(target, headers={"Cache-Control": "public, max-age=86400"})
        return FileResponse(_static_dir / "index.html", headers={"Cache-Control": "no-cache"})
