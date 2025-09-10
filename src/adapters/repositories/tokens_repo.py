from __future__ import annotations

import logging
from typing import Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.adapters.db.models import Token
from src.adapters.db.models import TokenScore
from sqlalchemy import select, func
from typing import Optional, Tuple, List


class TokensRepository:
    def __init__(self, db: Session):
        self.db = db
        self._log = logging.getLogger("tokens_repo")

    def get_by_mint(self, mint: str) -> Optional[Token]:
        return self.db.query(Token).filter(Token.mint_address == mint).first()

    def insert_monitoring(self, mint: str, name: Optional[str], symbol: Optional[str]) -> bool:
        """Попытаться добавить токен со статусом monitoring. Возвращает True, если добавлен."""
        t = Token(mint_address=mint, name=name, symbol=symbol, status="monitoring")
        self.db.add(t)
        try:
            self.db.commit()
            self._log.info(
                "token_inserted",
                extra={"extra": {"mint": mint, "name": name, "symbol": symbol, "status": "monitoring"}},
            )
            return True
        except IntegrityError:
            self.db.rollback()
            self._log.info(
                "token_duplicate",
                extra={"extra": {"mint": mint}},
            )
            return False

    def list_by_status(self, status: str, limit: int = 100, offset: int = 0) -> list[Token]:
        q = self.db.query(Token).filter(Token.status == status).order_by(Token.id.asc())
        if offset:
            q = q.offset(offset)
        if limit:
            q = q.limit(limit)
        return list(q.all())

    def set_active(self, token: Token) -> None:
        from datetime import datetime, timezone

        token.status = "active"
        token.last_updated_at = datetime.now(tz=timezone.utc)
        self.db.add(token)
        self.db.commit()

    def set_monitoring(self, token: Token) -> None:
        from datetime import datetime, timezone

        token.status = "monitoring"
        token.last_updated_at = datetime.now(tz=timezone.utc)
        self.db.add(token)
        self.db.commit()

    def update_token_fields(self, token: Token, name: Optional[str] = None, symbol: Optional[str] = None) -> None:
        updated = False
        if name and not token.name:
            token.name = name
            updated = True
        if symbol and not token.symbol:
            token.symbol = symbol
            updated = True
        if updated:
            self.db.add(token)
            self.db.commit()

    def insert_score_snapshot(self, token_id: int, metrics: dict, score: Optional[float] = None) -> int:
        from datetime import datetime, timezone

        snap = TokenScore(token_id=token_id, score=score, metrics=metrics, created_at=datetime.now(tz=timezone.utc))
        self.db.add(snap)
        self.db.commit()
        self.db.refresh(snap)
        logging.getLogger("tokens_repo").info(
            "score_snapshot_inserted", extra={"extra": {"token_id": token_id, "score": score}}
        )
        return snap.id

    def get_latest_snapshot(self, token_id: int) -> Optional[TokenScore]:
        return (
            self.db.query(TokenScore)
            .filter(TokenScore.token_id == token_id)
            .order_by(TokenScore.created_at.desc(), TokenScore.id.desc())
            .first()
        )

    def update_snapshot_score(self, snapshot_id: int, score: float) -> None:
        snap = self.db.query(TokenScore).get(snapshot_id)
        if snap is None:
            return
        snap.score = score
        # try to stamp scored_at inside metrics JSON for UI/UX
        try:
            from datetime import datetime, timezone
            if isinstance(snap.metrics, dict):
                m = dict(snap.metrics)
                m["scored_at"] = datetime.now(tz=timezone.utc).isoformat()
                snap.metrics = m
        except Exception:
            pass
        self.db.add(snap)
        self.db.commit()
        logging.getLogger("tokens_repo").info(
            "score_snapshot_updated", extra={"extra": {"snapshot_id": snapshot_id, "score": score}}
        )

    # --- Архивация ---
    def has_score_ge_since(self, token_id: int, min_score: float, since_dt) -> bool:
        q = (
            self.db.query(TokenScore)
            .filter(TokenScore.token_id == token_id)
            .filter(TokenScore.created_at >= since_dt)
            .filter(TokenScore.score.isnot(None))
            .filter(TokenScore.score >= min_score)
        )
        return self.db.query(q.exists()).scalar()  # type: ignore[arg-type]

    def archive_token(self, token: Token, reason: str) -> None:
        from datetime import datetime, timezone

        token.status = "archived"
        token.last_updated_at = datetime.now(tz=timezone.utc)
        self.db.add(token)
        self.db.commit()
        logging.getLogger("tokens_repo").info(
            "token_archived", extra={"extra": {"token_id": token.id, "mint": token.mint_address, "reason": reason}}
        )

    def list_monitoring_older_than_hours(self, hours: int, limit: int = 500) -> list[Token]:
        from datetime import datetime, timedelta, timezone

        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=hours)
        q = (
            self.db.query(Token)
            .filter(Token.status == "monitoring")
            .filter(Token.created_at < cutoff)
            .order_by(Token.created_at.asc())
            .limit(limit)
        )
        return list(q.all())

    def list_non_archived_with_latest_scores(
        self,
        statuses: Optional[List[str]] = None,
        min_score: Optional[float] = None,
        limit: int = 50,
        offset: int = 0,
        sort: str = "score_desc",
    ) -> List[Tuple[Token, Optional[TokenScore]]]:
        # Подзапрос на последний снапшот per token
        subq = (
            self.db.query(
                TokenScore.token_id.label("token_id"), func.max(TokenScore.created_at).label("max_created_at")
            )
            .group_by(TokenScore.token_id)
            .subquery()
        )
        # Соединяем с последними снапшотами
        q = (
            self.db.query(Token, TokenScore)
            .join(subq, subq.c.token_id == Token.id, isouter=True)
            .join(
                TokenScore,
                (TokenScore.token_id == subq.c.token_id) & (TokenScore.created_at == subq.c.max_created_at),
                isouter=True,
            )
        )
        # По умолчанию скрываем archived. Если явный фильтр статусов задан — используем его как есть
        if statuses is None:
            q = q.filter(Token.status != "archived")
        else:
            q = q.filter(Token.status.in_(statuses))
        # min_score применяется только к active; monitoring не фильтруем по скору
        if min_score is not None:
            q = q.filter(((Token.status != "active") | (TokenScore.score >= min_score)))
        # Сортировка: по умолчанию score DESC NULLS LAST
        if sort == "score_asc":
            q = q.order_by(TokenScore.score.asc().nullsfirst(), Token.id.desc())
        else:
            q = q.order_by(TokenScore.score.desc().nullslast(), Token.id.desc())
        if offset:
            q = q.offset(offset)
        if limit:
            q = q.limit(limit)
        return list(q.all())

    def count_non_archived_with_latest_scores(self, statuses: Optional[List[str]] = None, min_score: Optional[float] = None) -> int:
        # Подзапрос на последний снапшот per token
        subq = (
            self.db.query(
                TokenScore.token_id.label("token_id"), func.max(TokenScore.created_at).label("max_created_at")
            )
            .group_by(TokenScore.token_id)
            .subquery()
        )
        q = (
            self.db.query(func.count(Token.id))
            .join(subq, subq.c.token_id == Token.id, isouter=True)
            .join(
                TokenScore,
                (TokenScore.token_id == subq.c.token_id) & (TokenScore.created_at == subq.c.max_created_at),
                isouter=True,
            )
        )
        if statuses is None:
            q = q.filter(Token.status != "archived")
        else:
            q = q.filter(Token.status.in_(statuses))
        if min_score is not None:
            q = q.filter(((Token.status != "active") | (TokenScore.score >= min_score)))
        return int(q.scalar() or 0)

    def get_score_history(self, token_id: int, limit: int = 20) -> List[TokenScore]:
        q = (
            self.db.query(TokenScore)
            .filter(TokenScore.token_id == token_id)
            .order_by(TokenScore.created_at.desc(), TokenScore.id.desc())
            .limit(limit)
        )
        return list(q.all())
