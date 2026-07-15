
import asyncio
from datetime import datetime

from config import get_config
from database import get_engine
from logger import get_logger
from core.runtime.session import get_agent_pool


logger = get_logger(__name__)


async def check_database() -> dict:
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            result.scalar_one()
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)[:500]}


async def check_agent_pool() -> dict:
    try:
        pool = get_agent_pool()
        return {"status": "ok", **pool.get_pool_health()}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)[:500]}


def check_config_sanity() -> dict:
    issues: list[str] = []
    cfg = get_config()

    for code, agent_cfg in cfg.agents.items():
        if agent_cfg.context_window > cfg.session_health.context_window_sanity_cap:
            issues.append(
                f"agent '{code}' context_window={agent_cfg.context_window} exceeds sanity_cap={cfg.session_health.context_window_sanity_cap}"
            )

    if cfg.agent_runtime.context_compression_trigger_ratio >= 1.0:
        issues.append("trigger_ratio >= 1.0, compaction will never trigger")

    if cfg.agent_runtime.context_compression_hard_stop_ratio <= cfg.agent_runtime.context_compression_trigger_ratio:
        issues.append("hard_stop_ratio <= trigger_ratio, hard stop fires before compaction")

    return {
        "status": "ok" if not issues else "warn",
        "issues": issues,
        "agent_count": len(cfg.agents),
        "max_messages_per_session": cfg.session_health.max_messages_per_session,
        "context_window_sanity_cap": cfg.session_health.context_window_sanity_cap,
        "trigger_ratio": cfg.agent_runtime.context_compression_trigger_ratio,
        "hard_stop_ratio": cfg.agent_runtime.context_compression_hard_stop_ratio,
    }


async def full_health_check() -> dict:
    db_result, pool_result = await asyncio.gather(
        check_database(),
        check_agent_pool(),
    )
    config_result = check_config_sanity()

    all_ok = (
        db_result["status"] == "ok"
        and pool_result["status"] == "ok"
        and config_result["status"] in ("ok", "warn")
    )

    return {
        "status": "ok" if all_ok else "error",
        "timestamp": datetime.now().isoformat(),
        "database": db_result,
        "agent_pool": pool_result,
        "config": config_result,
    }
