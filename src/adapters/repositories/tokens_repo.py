from __future__ import annotations

import logging
from typing import Optional
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from src.adapters.db.models import Token
from src.adapters.db.models import TokenScore
from sqlalchemy import select, func, text
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
            
            # Record status transition for monitoring
            try:
                from src.monitoring.token_monitor import get_token_monitor
                token_monitor = get_token_monitor()
                token_monitor.record_status_transition(
                    mint_address=mint,
                    from_status="new",
                    to_status="monitoring",
                    reason="initial_processing"
                )
            except Exception as e:
                self._log.warning(f"Failed to record token creation transition: {e}")
            
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
    
    def list_monitoring_for_activation(self, limit: int = 100) -> list[Token]:
        """
        Get monitoring tokens ordered by score (highest first) for activation task.
        This ensures tokens with high scores (likely to have sufficient liquidity) 
        are checked first for activation.
        
        For now, use the same logic as list_by_status but prioritize by last_updated_at DESC
        to check tokens that were recently scored first.
        """
        q = (
            self.db.query(Token)
            .filter(Token.status == "monitoring")
            .order_by(
                Token.last_updated_at.asc().nullsfirst(),  # Older updates first to avoid starvation
                Token.created_at.desc()
            )
        )
        if limit:
            q = q.limit(limit)
        return list(q.all())

    def set_active(self, token: Token) -> None:
        from datetime import datetime, timezone

        old_status = token.status
        token.status = "active"
        token.last_updated_at = datetime.now(tz=timezone.utc)
        self.db.add(token)
        self.db.commit()
        
        # Record status transition for monitoring
        try:
            from src.monitoring.token_monitor import get_token_monitor
            token_monitor = get_token_monitor()
            token_monitor.record_status_transition(
                mint_address=token.mint_address,
                from_status=old_status,
                to_status="active",
                reason="activation_successful"
            )
        except Exception as e:
            self._log.warning(f"Failed to record token activation transition: {e}")

    def set_monitoring(self, token: Token) -> None:
        from datetime import datetime, timezone

        old_status = token.status
        token.status = "monitoring"
        token.last_updated_at = datetime.now(tz=timezone.utc)
        self.db.add(token)
        self.db.commit()
        
        # Record status transition for monitoring
        try:
            from src.monitoring.token_monitor import get_token_monitor
            token_monitor = get_token_monitor()
            token_monitor.record_status_transition(
                mint_address=token.mint_address,
                from_status=old_status,
                to_status="monitoring",
                reason="status_change"
            )
        except Exception as e:
            self._log.warning(f"Failed to record token monitoring transition: {e}")

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

        # TODO: Re-enable spam_metrics after PostgreSQL migration adds spam_metrics column
        # Preserve spam_metrics from previous snapshot
        # previous_spam_metrics = None
        # try:
        #     latest = self.get_latest_snapshot(token_id)
        #     if latest and latest.spam_metrics:
        #         previous_spam_metrics = latest.spam_metrics
        # except Exception:
        #     pass

        snap = TokenScore(
            token_id=token_id, 
            score=score, 
            smoothed_score=smoothed_score,
            metrics=metrics,
            raw_components=raw_components,
            smoothed_components=smoothed_components,
            scoring_model=scoring_model,
            # spam_metrics=previous_spam_metrics,  # Preserve spam metrics - disabled for PostgreSQL migration
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

        old_status = token.status
        token.status = "archived"
        token.last_updated_at = datetime.now(tz=timezone.utc)
        self.db.add(token)
        self.db.commit()
        logging.getLogger("tokens_repo").info(
            "token_archived", extra={"extra": {"token_id": token.id, "mint": token.mint_address, "reason": reason}}
        )
        
        # Record status transition for monitoring
        try:
            from src.monitoring.token_monitor import get_token_monitor
            token_monitor = get_token_monitor()
            token_monitor.record_status_transition(
                mint_address=token.mint_address,
                from_status=old_status,
                to_status="archived",
                reason=reason
            )
        except Exception as e:
            self._log.warning(f"Failed to record token archive transition: {e}")

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
        try:
            # Используем materialized view для быстрого доступа к последним scores
            latest_scores_table = text("""
                SELECT * FROM latest_token_scores
            """).columns(
                id=TokenScore.id,
                token_id=TokenScore.token_id,
                score=TokenScore.score,
                smoothed_score=TokenScore.smoothed_score,
                metrics=TokenScore.metrics,
                raw_components=TokenScore.raw_components,
                smoothed_components=TokenScore.smoothed_components,
                scoring_model=TokenScore.scoring_model,
                created_at=TokenScore.created_at
            ).alias("latest_scores")
            
            # Основной запрос с JOIN к materialized view
            q = (
                self.db.query(Token, TokenScore)
                .outerjoin(
                    latest_scores_table,
                    Token.id == latest_scores_table.c.token_id
                )
                .outerjoin(
                    TokenScore,
                    TokenScore.id == latest_scores_table.c.id
                )
            )
            
            # По умолчанию скрываем archived
            if statuses is None:
                q = q.filter(Token.status != "archived")
            else:
                q = q.filter(Token.status.in_(statuses))
            
            # min_score применяется только к токенам в мониторинге, активные показываем всегда
            if min_score is not None:
                if statuses and len(statuses) == 1 and statuses[0] == "active":
                    pass  # Не фильтруем активные токены по скору
                else:
                    q = q.filter(((Token.status == "active") | (TokenScore.score >= min_score)))
            
            # Сортировка
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
        except ProgrammingError as exc:
            # materialized view отсутствует (например, не применён sql-скрипт) — откатываем и используем безопасный фолбэк
            self.db.rollback()
            if "latest_token_scores" not in str(exc.orig).lower():  # type: ignore[attr-defined]
                raise
            self._log.warning(
                "latest_token_scores_view_missing_fallback",
                exc_info=exc,
            )
            return self._list_non_archived_with_latest_scores_fallback(
                statuses=statuses,
                min_score=min_score,
                limit=limit,
                offset=offset,
                sort=sort,
            )

    def _list_non_archived_with_latest_scores_fallback(
        self,
        statuses: Optional[List[str]] = None,
        min_score: Optional[float] = None,
        limit: int = 50,
        offset: int = 0,
        sort: str = "score_desc",
    ) -> List[Tuple[Token, Optional[TokenScore]]]:
        # Фолбэк без materialized view: определяем последние снапшоты через агрегаты
        latest_score_ids = (
            self.db.query(
                TokenScore.token_id.label("token_id"),
                func.max(TokenScore.created_at).label("max_created_at"),
                func.max(TokenScore.id).label("max_id"),
            )
            .group_by(TokenScore.token_id)
            .subquery()
        )

        q = (
            self.db.query(Token, TokenScore)
            .outerjoin(latest_score_ids, Token.id == latest_score_ids.c.token_id)
            .outerjoin(TokenScore, TokenScore.id == latest_score_ids.c.max_id)
        )

        if statuses is None:
            q = q.filter(Token.status != "archived")
        else:
            q = q.filter(Token.status.in_(statuses))

        if min_score is not None:
            if statuses and len(statuses) == 1 and statuses[0] == "active":
                pass
            else:
                q = q.filter(((Token.status == "active") | (TokenScore.score >= min_score)))

        if sort == "score_asc":
            q = q.order_by(
                func.coalesce(TokenScore.smoothed_score, TokenScore.score).asc().nullsfirst(),
                Token.id.desc(),
            )
        else:
            q = q.order_by(
                func.coalesce(TokenScore.smoothed_score, TokenScore.score).desc().nullslast(),
                Token.id.desc(),
            )

        if offset:
            q = q.offset(offset)
        if limit:
            q = q.limit(limit)

        return list(q.all())

    def count_non_archived_with_latest_scores(self, statuses: Optional[List[str]] = None, min_score: Optional[float] = None) -> int:
        # Оптимизированный count без сложных JOIN если min_score не задан
        if min_score is None:
            # Простой count по статусу без JOIN
            q = self.db.query(func.count(Token.id))
            if statuses is None:
                q = q.filter(Token.status != "archived")
            else:
                q = q.filter(Token.status.in_(statuses))
            return int(q.scalar() or 0)

        try:
            # Если min_score задан, используем materialized view
            latest_scores_table = text("""
                SELECT * FROM latest_token_scores
            """).columns(
                id=TokenScore.id,
                token_id=TokenScore.token_id,
                score=TokenScore.score
            ).alias("latest_scores")
            
            q = (
                self.db.query(func.count(Token.id))
                .outerjoin(
                    latest_scores_table,
                    Token.id == latest_scores_table.c.token_id
                )
                .outerjoin(
                    TokenScore,
                    TokenScore.id == latest_scores_table.c.id
                )
            )
            
            if statuses is None:
                q = q.filter(Token.status != "archived")
            else:
                q = q.filter(Token.status.in_(statuses))
            
            # min_score применяется только к токенам в мониторинге, активные показываем всегда
            if statuses and len(statuses) == 1 and statuses[0] == "active":
                pass  # Не фильтруем активные токены по скору
            else:
                q = q.filter(((Token.status == "active") | (TokenScore.score >= min_score)))
            
            return int(q.scalar() or 0)
        except ProgrammingError as exc:
            self.db.rollback()
            if "latest_token_scores" not in str(exc.orig).lower():  # type: ignore[attr-defined]
                raise
            self._log.warning(
                "latest_token_scores_view_missing_fallback_count",
                exc_info=exc,
            )
            return self._count_non_archived_with_latest_scores_fallback(
                statuses=statuses,
                min_score=min_score,
            )

    def _count_non_archived_with_latest_scores_fallback(
        self,
        statuses: Optional[List[str]] = None,
        min_score: Optional[float] = None,
    ) -> int:
        latest_score_ids = (
            self.db.query(
                TokenScore.token_id.label("token_id"),
                func.max(TokenScore.id).label("max_id"),
            )
            .group_by(TokenScore.token_id)
            .subquery()
        )

        q = (
            self.db.query(func.count(Token.id))
            .outerjoin(latest_score_ids, Token.id == latest_score_ids.c.token_id)
            .outerjoin(TokenScore, TokenScore.id == latest_score_ids.c.max_id)
        )

        if statuses is None:
            q = q.filter(Token.status != "archived")
        else:
            q = q.filter(Token.status.in_(statuses))

        if statuses and len(statuses) == 1 and statuses[0] == "active":
            pass
        else:
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
    
    def get_tokens_by_status(self, status: str, limit: int = 100) -> List[Token]:
        """Get tokens by status for monitoring and analysis."""
        return (
            self.db.query(Token)
            .filter(Token.status == status)
            .order_by(Token.created_at.desc())
            .limit(limit)
            .all()
        )
    def get_active_tokens_above_score(self, min_score: float, limit: int = 100) -> List[Token]:
        """Get active tokens with latest score above threshold for spam monitoring."""
        from sqlalchemy import func
        
        # Subquery to get the latest score for each token
        subq = (
            self.db.query(
                TokenScore.token_id.label("token_id"), 
                func.max(TokenScore.created_at).label("max_created_at")
            )
            .group_by(TokenScore.token_id)
            .subquery()
        )
        
        # Join with latest scores and filter
        q = (
            self.db.query(Token)
            .join(subq, subq.c.token_id == Token.id)
            .join(
                TokenScore,
                (TokenScore.token_id == subq.c.token_id) & 
                (TokenScore.created_at == subq.c.max_created_at)
            )
            .filter(Token.status == "active")
            .filter(
                (TokenScore.smoothed_score >= min_score) | 
                (TokenScore.score >= min_score)
            )
            .order_by(
                func.coalesce(TokenScore.smoothed_score, TokenScore.score).desc()
            )
            .limit(limit)
        )
        
        return list(q.all())

    def update_spam_metrics(self, token_id: int, spam_metrics: dict) -> None:
        """Update spam metrics for the latest token score.
        
        TODO: Re-enable after PostgreSQL migration adds spam_metrics column.
        For now, just log the metrics without storing them.
        """
        from datetime import datetime, timezone
        
        # Temporarily disabled - spam_metrics column not in PostgreSQL schema yet
        logging.getLogger("tokens_repo").info(
            "spam_metrics_skipped_postgresql_migration", 
            extra={
                "extra": {
                    "token_id": token_id, 
                    "spam_percentage": spam_metrics.get("spam_percentage", 0),
                    "risk_level": spam_metrics.get("risk_level", "unknown")
                }
            }
        )
        return
        
        # # Get the latest score record
        # latest_score = self.get_latest_snapshot(token_id)
        # 
        # if latest_score:
        #     # Update existing record
        #     latest_score.spam_metrics = spam_metrics
        #     self.db.add(latest_score)
        #     self.db.commit()
        #     
        #     logging.getLogger("tokens_repo").info(
        #         "spam_metrics_updated", 
        #         extra={
        #             "extra": {
        #                 "token_id": token_id, 
        #                 "spam_percentage": spam_metrics.get("spam_percentage", 0),
        #                 "risk_level": spam_metrics.get("risk_level", "unknown")
        #             }
        #         }
        #     )
        # else:
        #     # Create new score record with just spam metrics
        #     snap = TokenScore(
        #         token_id=token_id,
        #         spam_metrics=spam_metrics,
        #         created_at=datetime.now(tz=timezone.utc)
        #     )
        #     self.db.add(snap)
        #     self.db.commit()
        #     
        #     logging.getLogger("tokens_repo").info(
        #         "spam_metrics_created", 
        #         extra={
        #             "extra": {
        #                 "token_id": token_id, 
        #                 "spam_percentage": spam_metrics.get("spam_percentage", 0),
        #                 "risk_level": spam_metrics.get("risk_level", "unknown")
        #             }
        #         }
        #     )
