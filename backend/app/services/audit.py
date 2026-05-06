"""统一的审计日志写入。每个关键 mutation 都应该调一次。"""
import json
from typing import Optional, Any
from sqlmodel import Session
from ..models import User, AuditLog


def log(
    session: Session,
    operator: Optional[User],
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    detail: Optional[Any] = None,
) -> AuditLog:
    """
    action 命名规范：模块.动作。例如：
      booking.cancel / booking.check_in / session.cancel / session.no_show
      card.issue / card.refund / card.adjust / card.freeze / card.unfreeze
      user.deactivate / user.activate / user.change_password / user.reset_password
    """
    try:
        detail_str = json.dumps(detail, ensure_ascii=False, default=str) if detail else None
    except Exception:
        detail_str = str(detail)
    al = AuditLog(
        operator_id=operator.id if operator else None,
        operator_name=operator.name if operator else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail_str,
    )
    session.add(al)
    return al
