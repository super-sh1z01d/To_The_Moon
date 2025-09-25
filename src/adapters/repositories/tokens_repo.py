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
        # Order by last_updated_at ASC (oldest updates first) to prioritize stale tokens,
        # then by created_at DESC (newest tokens first) for tokens never updated
        q = (
            self.db.query(Token)
            .filter(Token.status == status)
            .order_by(
                Token.last_updated_at.asc().nullsfirst(),  # Prioritize never-updated tokens
                Token.created_at.desc()  # Then newest tokens first
            )
        )
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

    def insert_score_snapshot(
        self, 
        token_id: int, 
        metrics: dict, 
        score: Optional[float] = None, 
        smoothed_score: Optional[float] = None,
        raw_components: Optional[dict] = None,
        smoothed_components: Optional[dict] = None,
        scoring_model: str = "hybrid_momentum"
    ) -> int:
        from datetime import datetime, timezone

        # Add scored_at timestamp to metrics for UI display
        try:
            if isinstance(metrics, dict):
                metrics_with_timestamp = dict(metrics)
                metrics_with_timestamp["scored_at"] = datetime.now(tz=timezone.utc).isoformat()
                metrics = metrics_with_timestamp
        except Exception:
            pass

        snap = TokenScore(
            token_id=token_id, 
            score=score, 
            smoothed_score=smoothed_score,
            metrics=metrics,
            raw_components=raw_components,
            smoothed_components=smoothed_components,
            scoring_model=scoring_model,
            created_at=datetime.now(tz=timezone.utc)
        )
        self.db.add(snap)
        
        # Update token's last_updated_at timestamp
        token = self.db.query(Token).filter(Token.id == token_id).first()
        if token:
            token.last_updated_at = datetime.now(tz=timezone.utc)
            self.db.add(token)
        
        self.db.commit()
        self.db.refresh(snap)
        logging.getLogger("tokens_repo").info(
            "score_snapshot_inserted", 
            extra={"extra": {"token_id": token_id, "score": score, "smoothed_score": smoothed_score, "scoring_model": scoring_model}}
        )
        return snap.id

    def get_latest_snapshot(self, token_id: int) -> Optional[TokenScore]:
        return (
            self.db.query(TokenScore)
            .filter(TokenScore.token_id == token_id)
            .order_by(TokenScore.created_at.desc(), TokenScore.id.desc())
            .first()
        )

    def get_latest_snapshots_batch(self, token_ids: list[int]) -> dict[int, Optional[TokenScore]]:
        """Get latest snapshots for multiple tokens in a single query to avoid N+1 pattern."""
        if not token_ids:
            return {}
        
        # Subquery to get the latest snapshot ID for each token
        from sqlalchemy import func
        subq = (
            self.db.query(
                TokenScore.token_id,
                func.max(TokenScore.created_at).label('max_created_at')
            )
            .filter(TokenScore.token_id.in_(token_ids))
            .group_by(TokenScore.token_id)
            .subquery()
        )
        
        # Get the actual latest snapshots
        snapshots = (
            self.db.query(TokenScore)
            .join(
                subq,
                (TokenScore.token_id == subq.c.token_id) & 
                (TokenScore.created_at == subq.c.max_created_at)
            )
            .all()
        )
        
        # Create mapping
        result = {token_id: None for token_id in token_ids}
        for snap in snapshots:
            result[snap.token_id] = snap
        
        return result

    def update_token_timestamp(self, token_id: int) -> None:
        """Update token's last_updated_at timestamp without changing other fields."""
        from datetime import datetime, timezone
        
        token = self.db.query(Token).filter(Token.id == token_id).first()
        if token:
            token.last_updated_at = datetime.now(tz=timezone.utc)
            self.db.add(token)
            self.db.commit()

    def get_previous_smoothed_score(self, token_id: int) -> Optional[float]:
        """Получить предыдущий сглаженный скор для вычисления нового сглаженного значения."""
        latest = (
            self.db.query(TokenScore)
            .filter(TokenScore.token_id == token_id)
            .filter(TokenScore.smoothed_score.isnot(None))
            .order_by(TokenScore.created_at.desc(), TokenScore.id.desc())
            .first()
        )
        return float(latest.smoothed_score) if latest and latest.smoothed_score is not None else None

    def update_snapshot_score(self, snapshot_id: int, score: float, smoothed_score: Optional[float] = None) -> None:
        snap = self.db.query(TokenScore).get(snapshot_id)
        if snap is None:
            return
        snap.score = score
        if smoothed_score is not None:
            snap.smoothed_score = smoothed_score
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
            "score_snapshot_updated", 
            extra={"extra": {"snapshot_id": snapshot_id, "score": score, "smoothed_score": smoothed_score}}
        )

    # --- Архивация ---
    def has_score_ge_since(self, token_id: int, min_score: float, since_dt) -> bool:
        # For hybrid model, check both raw and smoothed scores
        # Token should NOT be archived if EITHER score is above threshold
        raw_score_query = (
            self.db.query(TokenScore)
            .filter(TokenScore.token_id == token_id)
            .filter(TokenScore.created_at >= since_dt)
            .filter(TokenScore.score.isnot(None))
            .filter(TokenScore.score >= min_score)
        )
        
        smoothed_score_query = (
            self.db.query(TokenScore)
            .filter(TokenScore.token_id == token_id)
            .filter(TokenScore.created_at >= since_dt)
            .filter(TokenScore.smoothed_score.isnot(None))
            .filter(TokenScore.smoothed_score >= min_score)
        )
        
        # Return True if EITHER raw OR smoothed score meets threshold
        has_raw_score = self.db.query(raw_score_query.exists()).scalar()  # type: ignore[arg-type]
        has_smoothed_score = self.db.query(smoothed_score_query.exists()).scalar()  # type: ignore[arg-type]
        
        return has_raw_score or has_smoothed_score

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
            .order_by(Token.created_at.desc())  # Newest first - more likely to be relevant
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
        # min_score применяется только к токенам в мониторинге, активные показываем всегда
        if min_score is not None:
            # Если запрашиваются только активные токены - не применяем фильтр по скору
            if statuses and len(statuses) == 1 and statuses[0] == "active":
                pass  # Не фильтруем активные токены по скору
            else:
                # Для смешанных запросов или токенов в мониторинге применяем фильтр
                q = q.filter(((Token.status == "active") | (TokenScore.score >= min_score)))
        # Сортировка: приоритет smoothed_score с fallback на score (как в отображении)
        if sort == "score_asc":
            q = q.order_by(
                func.coalesce(TokenScore.smoothed_score, TokenScore.score).asc().nullsfirst(), 
                Token.id.desc()
            )
        else:
            q = q.order_by(
                func.coalesce(TokenScore.smoothed_score, TokenScore.score).desc().nullslast(), 
                Token.id.desc()
            )
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
        # min_score применяется только к токенам в мониторинге, активные показываем всегда
        if min_score is not None:
            # Если запрашиваются только активные токены - не применяем фильтр по скору
            if statuses and len(statuses) == 1 and statuses[0] == "active":
                pass  # Не фильтруем активные токены по скору
            else:
                # Для смешанных запросов или токенов в мониторинге применяем фильтр
                q = q.filter(((Token.status == "active") | (TokenScore.score >= min_score)))
        return int(q.scalar() or 0)

    def get_score_history(self, token_id: int, limit: int = 20) -> List[TokenScore]:
        q = (
            self.db.query(TokenScore)
            .filter(TokenScore.token_id == token_id)
            .order_by(TokenScore.created_at.desc(), TokenScore.id.desc())
            .limit(limit)
        )
        return list(q.all())

    def get_latest_score(self, token_id: int) -> Optional[TokenScore]:
        """Get the most recent score record for a token (for EWMA service)."""
        return (
            self.db.query(TokenScore)
            .filter(TokenScore.token_id == token_id)
            .order_by(TokenScore.created_at.desc(), TokenScore.id.desc())
            .first()
        )
