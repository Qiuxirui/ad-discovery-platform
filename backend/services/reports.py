"""举报服务：24h 合并、举报码生成、终态追加、管理员处置联动广告状态。

状态只进不退（pending → reviewing → resolved / dismissed）；
举报码 ``RP-`` + 8 位大写字母数字（去掉 I/L/O/0/1），全局唯一且不可枚举。
"""

from __future__ import annotations

import json
import logging
import secrets
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..constants import REPORT_DAILY_LIMIT, REPORT_REASON_LABELS, REPORT_STATUS_USER_TEXT
from ..models import Ad, Report, ReportFollowup
from ..services.ads import AdService, api_error, log_review
from ..services.events import EventService
from ..utils.timeutil import now_utc, today_cst_range_utc, utc_to_iso_z
from ..visitor import ensure_visitor

__all__ = ["ReportService"]

audit_log = logging.getLogger("adx.audit")

CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_PREFIX = "RP-"
CODE_LENGTH = 8
MERGE_WINDOW_HOURS = 24
FOLLOWUP_WINDOW_DAYS = 7
TERMINAL_STATUSES = ("resolved", "dismissed")


def _generate_code(db: Session) -> str:
    """生成唯一举报码（冲突重试 5 次）。"""
    for _ in range(5):
        body = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        code = f"{CODE_PREFIX}{body}"
        exists = db.execute(select(func.count()).select_from(Report).where(Report.code == code)).scalar_one()
        if not exists:
            return code
    raise api_error(500, "CODE_GENERATION_FAILED", "举报码生成失败，请稍后重试")


def _snapshot(ad: Ad) -> str:
    """举报时的广告快照（举报卡展示用）。"""
    payload = {
        "ad_id": ad.id,
        "title": ad.title,
        "merchant_name": ad.merchant.name if ad.merchant is not None else "",
        "status": ad.status,
        "image_path": ad.image_path,
    }
    return json.dumps(payload, ensure_ascii=False)


class ReportService:
    """举报领域服务。"""

    @staticmethod
    def create(
        db: Session,
        visitor_id: str,
        ad_id: int,
        reason_code: str,
        detail: str | None,
    ) -> tuple[Report, bool]:
        """创建举报；同访客对同一广告 24h 内合并为 1 条。"""
        ad = db.get(Ad, ad_id)
        if ad is None:
            raise api_error(404, "AD_NOT_FOUND", "该广告不存在或已被删除")
        ensure_visitor(db, visitor_id)

        current = now_utc()
        window_start = current - timedelta(hours=MERGE_WINDOW_HOURS)
        existing = db.execute(
            select(Report)
            .where(Report.visitor_id == visitor_id, Report.ad_id == ad_id, Report.created_at >= window_start)
            .order_by(Report.created_at.desc())
        ).scalars().first()
        if existing is not None:
            return existing, True

        start, end = today_cst_range_utc(current)
        today_count = db.execute(
            select(func.count())
            .select_from(Report)
            .where(
                Report.visitor_id == visitor_id,
                Report.created_at >= start,
                Report.created_at < end,
            )
        ).scalar_one()
        if today_count >= REPORT_DAILY_LIMIT:
            raise api_error(
                429,
                "REPORT_DAILY_LIMIT",
                f"今日举报已达 {REPORT_DAILY_LIMIT} 条上限，请明日再提交",
            )

        report = Report(
            code=_generate_code(db),
            ad_id=ad_id,
            visitor_id=visitor_id,
            reason_code=reason_code,
            detail=detail,
            status="pending",
            ad_snapshot=_snapshot(ad),
            created_at=current,
            updated_at=current,
        )
        db.add(report)
        EventService.insert_single(
            db,
            visitor_id=visitor_id,
            event_type="report",
            ad_id=ad_id,
            page="detail",
            meta={"reason_code": reason_code},
        )
        db.commit()
        db.refresh(report)
        audit_log.info("report_create code=%s ad_id=%s", report.code, ad_id)
        return report, False

    @staticmethod
    def lookup(db: Session, code: str) -> Report | None:
        """按举报码查询（大小写不敏感）。"""
        normalized = (code or "").strip().upper()
        if not normalized:
            return None
        return db.execute(select(Report).where(Report.code == normalized)).scalars().first()

    @staticmethod
    def mine(db: Session, visitor_id: str) -> list[Report]:
        """本设备提交过的举报（按时间倒序）。"""
        return list(
            db.execute(
                select(Report).where(Report.visitor_id == visitor_id).order_by(Report.created_at.desc())
            )
            .scalars()
            .all()
        )

    @staticmethod
    def add_followup(db: Session, report: Report, visitor_id: str, note: str) -> ReportFollowup:
        """终态 7 天内可追加说明；不改状态。"""
        if report.status not in TERMINAL_STATUSES:
            raise api_error(409, "REPORT_NOT_TERMINAL", "该举报仍在处理中，无需追加说明")
        if report.handled_at is None or report.handled_at < now_utc() - timedelta(days=FOLLOWUP_WINDOW_DAYS):
            raise api_error(409, "FOLLOWUP_WINDOW_EXPIRED", "该举报已超过 7 天补充说明期限")
        followup = ReportFollowup(
            report_id=report.id,
            visitor_id=visitor_id,
            note=note,
            created_at=now_utc(),
        )
        db.add(followup)
        db.commit()
        db.refresh(followup)
        return followup

    @staticmethod
    def start_review(db: Session, report: Report) -> Report:
        """``pending`` → ``reviewing``。"""
        if report.status != "pending":
            raise api_error(409, "INVALID_TRANSITION", "只有待处理的举报可以开始处理")
        report.status = "reviewing"
        report.updated_at = now_utc()
        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def resolve(db: Session, report: Report, admin_id: int, action: str, note: str) -> Report:
        """判定成立：举报 ``resolved``，广告下架（或记录整改要求）。"""
        if report.status in TERMINAL_STATUSES:
            raise api_error(409, "INVALID_TRANSITION", "该举报已处理完毕")
        text = (note or "").strip()
        if not text:
            raise api_error(422, "REASON_REQUIRED", "请填写处理结论", [
                {"field": "note", "message": "请填写处理结论"}
            ])
        action_key = (action or "offline").strip()
        if action_key not in ("offline", "rectify"):
            raise api_error(422, "ACTION_INVALID", "处置动作只能是下架或要求整改")

        ad = db.get(Ad, report.ad_id)
        if ad is not None and action_key == "offline":
            if ad.status in ("active", "scheduled"):
                AdService.offline(db, ad, admin_id, text)
            else:
                log_review(db, ad, "offline", "admin", admin_id, reason=text)

        current = now_utc()
        report.status = "resolved"
        report.admin_note = text
        report.handled_by = admin_id
        report.handled_at = current
        report.updated_at = current
        db.commit()
        db.refresh(report)
        audit_log.info("report_resolve code=%s action=%s", report.code, action_key)
        return report

    @staticmethod
    def dismiss(db: Session, report: Report, admin_id: int, note: str) -> Report:
        """判定不成立：举报 ``dismissed``，广告不变。"""
        if report.status in TERMINAL_STATUSES:
            raise api_error(409, "INVALID_TRANSITION", "该举报已处理完毕")
        text = (note or "").strip()
        if not text:
            raise api_error(422, "REASON_REQUIRED", "请填写处理结论", [
                {"field": "note", "message": "请填写处理结论"}
            ])
        current = now_utc()
        report.status = "dismissed"
        report.admin_note = text
        report.handled_by = admin_id
        report.handled_at = current
        report.updated_at = current
        db.commit()
        db.refresh(report)
        audit_log.info("report_dismiss code=%s", report.code)
        return report

    @staticmethod
    def to_lookup_dict(report: Report) -> dict[str, object]:
        """用户侧查询视图（不含 visitor_id / 处理人）。"""
        ad_title = ""
        if report.ad_snapshot:
            try:
                ad_title = str(json.loads(report.ad_snapshot).get("title", ""))
            except (json.JSONDecodeError, AttributeError):
                ad_title = ""
        if not ad_title and report.ad is not None:
            ad_title = report.ad.title
        return {
            "code": report.code,
            "ad_id": report.ad_id,
            "ad_title": ad_title,
            "reason_label": REPORT_REASON_LABELS.get(report.reason_code, report.reason_code),
            "status": report.status,
            "status_text": REPORT_STATUS_USER_TEXT.get(report.status, ""),
            "created_at": utc_to_iso_z(report.created_at),
            "handled_at": utc_to_iso_z(report.handled_at),
            "conclusion": report.admin_note,
        }
