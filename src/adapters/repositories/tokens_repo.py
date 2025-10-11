from __future__ import annotations

import json
import logging
from typing import Optional
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session, noload

from src.adapters.db.models import Token
from src.adapters.db.models import TokenScore
from sqlalchemy import select, func, text, Integer, Numeric, DateTime, String, JSON
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional, Tuple, List, Any


class TokensRepository:
    _latest_table_ready: bool = False

    def __init__(self, db: Session):
        self.db = db
        self._log = logging.getLogger("tokens_repo")
        self._ensure_latest_scores_table()

    def get_by_mint(self, mint: str) -> Optional[Token]:
        return self.db.query(Token).filter(Token.mint_address == mint).first()

    def _ensure_latest_scores_table(self) -> None:
        """Создаёт вспомогательную таблицу latest_token_scores, если её нет."""
        if type(self)._latest_table_ready:
            return

        drop_view_sql = text("DROP MATERIALIZED VIEW IF EXISTS latest_token_scores;")
        ddl = text(
            """
            CREATE TABLE IF NOT EXISTS latest_token_scores (
                token_id INTEGER PRIMARY KEY REFERENCES tokens(id) ON DELETE CASCADE,
                score NUMERIC(10, 4),
                smoothed_score NUMERIC(10, 4),
                liquidity_usd NUMERIC(20, 2),
                delta_p_5m NUMERIC(10, 4),
                delta_p_15m NUMERIC(10, 4),
                n_5m NUMERIC(20, 2),
                primary_dex TEXT,
                image_url TEXT,
                pool_counts JSONB,
                fetched_at TIMESTAMPTZ,
                scoring_model VARCHAR(50),
                created_at TIMESTAMPTZ
            );
            """
        )
        alter_sql = text(
            """
            ALTER TABLE latest_token_scores
            ADD COLUMN IF NOT EXISTS image_url TEXT;
            """
        )
        index_sql = text(
            """
            CREATE INDEX IF NOT EXISTS idx_latest_scores_smoothed
                ON latest_token_scores (smoothed_score DESC NULLS LAST);
            CREATE INDEX IF NOT EXISTS idx_latest_scores_score
                ON latest_token_scores (score DESC NULLS LAST);
            """
        )
        try:
            try:
                self.db.execute(drop_view_sql)
            except ProgrammingError as exc:
                # Если latest_token_scores уже таблица, DROP MATERIALIZED VIEW упадёт — игнорируем
                self.db.rollback()
                if "is not a materialized view" not in str(exc.orig).lower():  # type: ignore[attr-defined]
                    raise
            self.db.execute(ddl)
            self.db.execute(alter_sql)
            self.db.execute(index_sql)
            self.db.commit()
        except Exception as exc:
            self._log.error("failed_to_prepare_latest_token_scores_table", exc_info=exc)
            self.db.rollback()
        else:
            type(self)._latest_table_ready = True

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

        now = datetime.now(tz=timezone.utc)

        # Add scored_at timestamp to metrics for UI display
        try:
            if isinstance(metrics, dict):
                metrics_with_timestamp = dict(metrics)
                metrics_with_timestamp["scored_at"] = now.isoformat()
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
            created_at=now
        )
        self.db.add(snap)
        
        # Update token's last_updated_at timestamp
        token = self.db.query(Token).filter(Token.id == token_id).first()
        if token:
            token.last_updated_at = now
            self.db.add(token)

        # Prepare aggregated values for latest_token_scores
        liquidity_usd = None
        delta_p_5m = None
        delta_p_15m = None
        n_5m = None
        primary_dex = None
        fetched_at = None
        image_url = None
        pool_counts_json = None

        if isinstance(metrics, dict):
            def _as_float(value: Optional[float]) -> Optional[float]:
                try:
                    return float(value) if value is not None else None
                except Exception:
                    return None

            liquidity_usd = _as_float(metrics.get("L_tot"))
            delta_p_5m = _as_float(metrics.get("delta_p_5m"))
            delta_p_15m = _as_float(metrics.get("delta_p_15m"))
            tx_count_5m = metrics.get("tx_count_5m")
            n_5m = _as_float(tx_count_5m if tx_count_5m is not None else metrics.get("n_5m"))
            primary_dex = metrics.get("primary_dex")
            fetched_at_raw = metrics.get("fetched_at")
            fetched_at = None
            if fetched_at_raw:
                try:
                    if isinstance(fetched_at_raw, str):
                        fetched_at = datetime.fromisoformat(
                            fetched_at_raw.replace("Z", "+00:00")
                        )
                    else:
                        fetched_at = fetched_at_raw
                except Exception:
                    fetched_at = None
            image_candidate = metrics.get("image_url")
            if isinstance(image_candidate, str):
                image_candidate = image_candidate.strip()
                if image_candidate:
                    image_url = image_candidate

            pools_metric = metrics.get("pools")
            if isinstance(pools_metric, list):
                counts: dict[str, int] = {}
                for pool in pools_metric:
                    if not isinstance(pool, dict):
                        continue
                    dex_value = pool.get("dex")
                    dex_key = str(dex_value) if dex_value is not None else "unknown"
                    counts[dex_key] = counts.get(dex_key, 0) + 1
                if counts:
                    pool_counts_json = json.dumps(counts)

        upsert_sql = text(
            """
            INSERT INTO latest_token_scores (
                token_id,
                score,
                smoothed_score,
                liquidity_usd,
                delta_p_5m,
                delta_p_15m,
                n_5m,
                primary_dex,
                image_url,
                pool_counts,
                fetched_at,
                scoring_model,
                created_at
            )
            VALUES (
                :token_id,
                :score,
                :smoothed_score,
                :liquidity_usd,
                :delta_p_5m,
                :delta_p_15m,
                :n_5m,
                :primary_dex,
                :image_url,
                :pool_counts,
                :fetched_at,
                :scoring_model,
                :created_at
            )
            ON CONFLICT (token_id) DO UPDATE SET
                score = EXCLUDED.score,
                smoothed_score = EXCLUDED.smoothed_score,
                liquidity_usd = EXCLUDED.liquidity_usd,
                delta_p_5m = EXCLUDED.delta_p_5m,
                delta_p_15m = EXCLUDED.delta_p_15m,
                n_5m = EXCLUDED.n_5m,
                primary_dex = EXCLUDED.primary_dex,
                image_url = EXCLUDED.image_url,
                pool_counts = EXCLUDED.pool_counts,
                fetched_at = EXCLUDED.fetched_at,
                scoring_model = EXCLUDED.scoring_model,
                created_at = EXCLUDED.created_at
            """
        )
        self.db.execute(
            upsert_sql,
            {
                "token_id": token_id,
                "score": score,
                "smoothed_score": smoothed_score,
                "liquidity_usd": liquidity_usd,
                "delta_p_5m": delta_p_5m,
                "delta_p_15m": delta_p_15m,
                "n_5m": n_5m,
                "primary_dex": primary_dex,
                "image_url": image_url,
                "pool_counts": pool_counts_json,
                "fetched_at": fetched_at,
                "scoring_model": scoring_model,
                "created_at": now,
            },
        )
        
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
    ) -> List[Tuple[Token, Optional[Any]]]:
        try:
            # Используем materialized view для быстрого доступа к последним scores
            latest_scores_table = text("""
                SELECT token_id, score, smoothed_score, liquidity_usd, delta_p_5m, delta_p_15m,
                       n_5m, primary_dex, image_url, pool_counts, fetched_at, scoring_model, created_at
                FROM latest_token_scores
            """).columns(
                token_id=Integer(),
                score=Numeric(),
                smoothed_score=Numeric(),
                liquidity_usd=Numeric(),
                delta_p_5m=Numeric(),
                delta_p_15m=Numeric(),
                n_5m=Numeric(),
                primary_dex=String(),
                image_url=String(),
                pool_counts=JSON().with_variant(JSONB, "postgresql"),
                fetched_at=DateTime(timezone=True),
                scoring_model=String(),
                created_at=DateTime(timezone=True),
            ).alias("latest_scores")

            latest_columns = {
                "latest_score": latest_scores_table.c.score.label("latest_score"),
                "latest_smoothed_score": latest_scores_table.c.smoothed_score.label("latest_smoothed_score"),
                "latest_liquidity_usd": latest_scores_table.c.liquidity_usd.label("latest_liquidity_usd"),
                "latest_delta_p_5m": latest_scores_table.c.delta_p_5m.label("latest_delta_p_5m"),
                "latest_delta_p_15m": latest_scores_table.c.delta_p_15m.label("latest_delta_p_15m"),
                "latest_n_5m": latest_scores_table.c.n_5m.label("latest_n_5m"),
                "latest_primary_dex": latest_scores_table.c.primary_dex.label("latest_primary_dex"),
                "latest_image_url": latest_scores_table.c.image_url.label("latest_image_url"),
                "latest_pool_counts": latest_scores_table.c.pool_counts.label("latest_pool_counts"),
                "latest_fetched_at": latest_scores_table.c.fetched_at.label("latest_fetched_at"),
                "latest_scoring_model": latest_scores_table.c.scoring_model.label("latest_scoring_model"),
                "latest_created_at": latest_scores_table.c.created_at.label("latest_created_at"),
            }

            q = (
                self.db.query(Token, *latest_columns.values())
                .options(noload(Token.scores))
                .outerjoin(
                    latest_scores_table,
                    Token.id == latest_scores_table.c.token_id
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
                    q = q.filter(((Token.status == "active") | (latest_scores_table.c.score >= min_score)))
            
            score_expr = func.coalesce(latest_scores_table.c.smoothed_score, latest_scores_table.c.score)
            if sort == "score_asc":
                q = q.order_by(
                    score_expr.asc(),
                    Token.id.desc(),
                )
            else:
                q = q.order_by(
                    score_expr.desc(),
                    Token.id.desc(),
                )
            
            if offset:
                q = q.offset(offset)
            if limit:
                q = q.limit(limit)

            results: List[Tuple[Token, Optional[Any]]] = []
            for row in q.all():
                token = row[0]
                latest_dict = {key: getattr(row, key) for key in latest_columns}
                results.append((token, latest_dict))

            return results
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
    ) -> List[Tuple[Token, Optional[Any]]]:
        latest_score_id_subq = (
            select(TokenScore.id)
            .where(TokenScore.token_id == Token.id)
            .order_by(TokenScore.created_at.desc(), TokenScore.id.desc())
            .limit(1)
            .correlate(Token)
            .scalar_subquery()
        )

        q = (
            self.db.query(Token, TokenScore)
            .options(noload(Token.scores))
            .outerjoin(TokenScore, TokenScore.id == latest_score_id_subq)
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

        score_expr = func.coalesce(TokenScore.smoothed_score, TokenScore.score)
        if sort == "score_asc":
            q = q.order_by(
                score_expr.asc(),
                Token.id.desc(),
            )
        else:
            q = q.order_by(
                score_expr.desc(),
                Token.id.desc(),
            )

        if offset:
            q = q.offset(offset)
        if limit:
            q = q.limit(limit)

        results: List[Tuple[Token, Optional[Any]]] = []
        for token, score_row in q.all():
            if score_row is None:
                results.append((token, None))
                continue

            metrics = score_row.metrics if isinstance(score_row.metrics, dict) else {}
            pool_counts = None
            pools_metric = metrics.get("pools") if isinstance(metrics, dict) else None
            if isinstance(pools_metric, list):
                counts: dict[str, int] = {}
                for item in pools_metric:
                    if not isinstance(item, dict):
                        continue
                    dex_key = str(item.get("dex")) if item.get("dex") is not None else "unknown"
                    counts[dex_key] = counts.get(dex_key, 0) + 1
                if counts:
                    pool_counts = counts
            latest_dict = {
                "latest_score": score_row.score,
                "latest_smoothed_score": score_row.smoothed_score,
                "latest_liquidity_usd": metrics.get("L_tot"),
                "latest_delta_p_5m": metrics.get("delta_p_5m"),
                "latest_delta_p_15m": metrics.get("delta_p_15m"),
                "latest_n_5m": metrics.get("n_5m"),
                "latest_primary_dex": metrics.get("primary_dex"),
                "latest_image_url": metrics.get("image_url"),
                "latest_pool_counts": pool_counts,
                "latest_fetched_at": metrics.get("fetched_at"),
                "latest_scoring_model": score_row.scoring_model,
                "latest_created_at": score_row.created_at,
            }
            results.append((token, latest_dict))

        return results

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
                SELECT token_id, score, smoothed_score
                FROM latest_token_scores
            """).columns(
                token_id=Integer(),
                score=Numeric(),
                smoothed_score=Numeric(),
            ).alias("latest_scores")
            
            q = (
                self.db.query(func.count(Token.id))
                .outerjoin(
                    latest_scores_table,
                    Token.id == latest_scores_table.c.token_id
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
                score_for_filter = func.coalesce(latest_scores_table.c.smoothed_score, latest_scores_table.c.score)
                q = q.filter(((Token.status == "active") | (score_for_filter >= min_score)))
            
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
        latest_score_id_subq = (
            select(TokenScore.id)
            .where(TokenScore.token_id == Token.id)
            .order_by(TokenScore.created_at.desc(), TokenScore.id.desc())
            .limit(1)
            .correlate(Token)
            .scalar_subquery()
        )

        q = (
            self.db.query(func.count(Token.id))
            .outerjoin(TokenScore, TokenScore.id == latest_score_id_subq)
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
