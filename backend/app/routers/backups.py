"""
备份查看 API — 让管理员在后台看一眼备份是不是在跑
"""
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from ..core.deps import require_admin

router = APIRouter(prefix="/api", tags=["backups"])

BACKUP_ROOT = Path.home() / "backups"


class BackupItem(BaseModel):
    name: str            # 目录名 yyyymmdd_HHMMSS
    timestamp: datetime
    db_size: int
    uploads_size: int
    has_manifest: bool


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except Exception:
            pass
    return total


@router.get("/admin/backups", response_model=List[BackupItem], dependencies=[Depends(require_admin)])
def list_backups():
    if not BACKUP_ROOT.exists():
        return []
    items = []
    for d in sorted(BACKUP_ROOT.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        try:
            ts = datetime.strptime(d.name, "%Y%m%d_%H%M%S")
        except ValueError:
            continue
        db = d / "studio.db"
        up = d / "uploads"
        items.append(BackupItem(
            name=d.name,
            timestamp=ts,
            db_size=db.stat().st_size if db.exists() else 0,
            uploads_size=_dir_size(up),
            has_manifest=(d / "MANIFEST.txt").exists(),
        ))
    return items


@router.get("/admin/backups/{name}/db", dependencies=[Depends(require_admin)])
def download_backup_db(name: str):
    """下载某次备份的 studio.db"""
    target = BACKUP_ROOT / name / "studio.db"
    if not target.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "备份不存在")
    return FileResponse(target, media_type="application/octet-stream", filename=f"studio-{name}.db")
