from __future__ import annotations

from typing import Any, Optional
from datetime import datetime, timezone
from types import SimpleNamespace
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.adapters.db.deps import get_db
from src.adapters.repositories.tokens_repo import TokensRepository
from src.domain.settings.service import SettingsService
from src.adapters.services.dexscreener_client import DexScreenerClient
from src.domain.pools.pool_type_service import PoolTypeService


router = APIRouter(prefix="/tokens", tags=["tokens"])


class ComponentBreakdown(BaseModel):
    tx_accel: float
    vol_momentum: float
    token_freshness: float
    orderflow_imbalance: float


class SpamMetrics(BaseModel):
    spam_percentage: float
    risk_level: str
    total_instructions: int
    compute_budget_count: int
    analyzed_at: Optional[str] = None


class TokenItem(BaseModel):
    mint_address: str
    name: Optional[str] = None
    symbol: Optional[str] = None
    status: str
    score: Optional[float] = None
    liquidity_usd: Optional[float] = Field(default=None, description="L_tot")
    delta_p_5m: Optional[float] = None
    delta_p_15m: Optional[float] = None
    n_5m: Optional[int] = None
    primary_dex: Optional[str] = None
    primary_pool_type: Optional[str] = Field(default=None, description="Dominant classified pool type")
    pools: Optional[list[PoolItem]] = Field(default=None, description="List of DEX pools")
    fetched_at: Optional[str] = Field(default=None, description="Last time token data was fetched from external APIs")
    scored_at: Optional[str] = Field(default=None, description="Last time token score was calculated and saved")
    last_processed_at: Optional[str] = Field(default=None, description="Last time token was processed by scheduler")
    solscan_url: str
    image_url: Optional[str] = None
    raw_components: Optional[ComponentBreakdown] = None
    smoothed_components: Optional[ComponentBreakdown] = None
    scoring_model: Optional[str] = None
    created_at: Optional[str] = None
    spam_metrics: Optional[SpamMetrics] = None


class TokensMeta(BaseModel):
    total: int
    limit: int
    offset: int
    page: int
    page_size: int
    has_prev: bool
    has_next: bool
    sort: str
    min_score: Optional[float] = None


class TokensResponse(BaseModel):
    total: int
    items: list[TokenItem]
    meta: TokensMeta


class PoolItem(BaseModel):
    address: Optional[str] = Field(default=None)
    dex: Optional[str] = Field(default=None)
    quote: Optional[str] = Field(default=None)
    solscan_url: Optional[str] = Field(default=None)
    count: Optional[int] = Field(default=None)
    pool_type: Optional[str] = Field(default=None, description="Normalized pool type (e.g. raydium_clmm)")
    owner_program: Optional[str] = Field(default=None, description="Solana program owning the pool")


class TokenStats(BaseModel):
    total: int
    active: int
    monitoring: int
    archived: int


@router.get("/stats", response_model=TokenStats)
async def get_token_stats(db: Session = Depends(get_db)) -> TokenStats:
    """Get token count statistics by status."""
    repo = TokensRepository(db)
    
    from sqlalchemy import func
    from src.adapters.db.models import Token
    
    # Get counts by status
    status_counts = db.query(
        Token.status,
        func.count(Token.id).label('count')
    ).group_by(Token.status).all()
    
    counts = {status: count for status, count in status_counts}
    total = sum(counts.values())
    
    return TokenStats(
        total=total,
        active=counts.get('active', 0),
        monitoring=counts.get('monitoring', 0),
        archived=counts.get('archived', 0)
    )


@router.get("", response_model=TokensResponse)
@router.get("/", response_model=TokensResponse)
async def list_tokens(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    min_score: Optional[float] = Query(None, description="Minimum score filter (optional)"),
    sort: str = Query("score_desc", pattern="^(score_desc|score_asc)$"),
    statuses: Optional[str] = Query(None, description="Comma-separated: active,monitoring,archived"),
    status: Optional[str] = Query(None, description="Single status: active,monitoring,archived"),
) -> TokensResponse:
    repo = TokensRepository(db)
    settings = SettingsService(db)
    # Don't apply min_score filter by default - show all tokens
    # Users can explicitly pass min_score parameter if they want filtering
    # Note: min_score is still used for archival and other backend processes
    
    status_list: Optional[list[str]] = None
    # Handle both 'status' (single) and 'statuses' (comma-separated) parameters
    if status and status.strip() in ("active", "monitoring", "archived"):
        status_list = [status.strip()]
    elif statuses:
        status_list = [s.strip() for s in statuses.split(",") if s.strip() in ("active", "monitoring", "archived")]
        if not status_list:
            status_list = None

    rows = repo.list_non_archived_with_latest_scores(statuses=status_list, min_score=min_score, limit=limit, offset=offset, sort=sort)
    total = repo.count_non_archived_with_latest_scores(statuses=status_list, min_score=min_score)
    items: list[TokenItem] = []
    
    # Оптимизированная обработка - минимум операций
    for token, latest in rows:
        if isinstance(latest, dict):
            latest_data = SimpleNamespace(
                score=latest.get("latest_score"),
                smoothed_score=latest.get("latest_smoothed_score"),
                liquidity_usd=latest.get("latest_liquidity_usd"),
                delta_p_5m=latest.get("latest_delta_p_5m"),
                delta_p_15m=latest.get("latest_delta_p_15m"),
                n_5m=latest.get("latest_n_5m"),
                primary_dex=latest.get("latest_primary_dex"),
                pool_type=latest.get("latest_pool_type"),
                pool_type_counts=latest.get("latest_pool_type_counts"),
                image_url=latest.get("latest_image_url"),
                pool_counts=latest.get("latest_pool_counts"),
                fetched_at=latest.get("latest_fetched_at"),
                scoring_model=latest.get("latest_scoring_model"),
                created_at=latest.get("latest_created_at"),
            )
        elif latest is None:
            latest_data = SimpleNamespace()
        else:
            latest_data = latest

        raw_components = None
        smoothed_components = None

        pools = None
        pool_type_counts = getattr(latest_data, "pool_type_counts", None)
        if isinstance(pool_type_counts, dict) and pool_type_counts:
            try:
                pools = [
                    PoolItem.model_construct(
                        address=None,
                        dex=None,
                        quote=None,
                        solscan_url=None,
                        count=int(count) if count is not None else None,
                        pool_type=pool_type,
                    )
                    for pool_type, count in pool_type_counts.items()
                ]
            except Exception:
                pools = None

        if pools is None:
            pool_counts = getattr(latest_data, "pool_counts", None)
            if isinstance(pool_counts, dict):
                try:
                    pools = [
                        PoolItem.model_construct(
                            address=None,
                            dex=dex,
                            quote=None,
                            solscan_url=None,
                            count=int(count) if count is not None else None,
                        )
                        for dex, count in pool_counts.items()
                    ]
                except Exception:
                    pools = None

        liquidity_usd = getattr(latest_data, "liquidity_usd", None)
        delta_p_5m = getattr(latest_data, "delta_p_5m", None)
        delta_p_15m = getattr(latest_data, "delta_p_15m", None)
        n_5m = getattr(latest_data, "n_5m", None)

        score_value = None
        if latest_data:
            smoothed = getattr(latest_data, "smoothed_score", None)
            score_raw = getattr(latest_data, "score", None)
            if smoothed is not None:
                score_value = float(smoothed)
            elif score_raw is not None:
                score_value = float(score_raw)

        fetched_at_value = getattr(latest_data, "fetched_at", None)
        fetched_at = fetched_at_value.isoformat() if isinstance(fetched_at_value, datetime) else fetched_at_value

        items.append(
            TokenItem.model_construct(
                mint_address=token.mint_address,
                name=token.name,
                symbol=token.symbol,
                status=token.status,
                score=score_value,
                liquidity_usd=float(liquidity_usd) if liquidity_usd is not None else None,
                delta_p_5m=float(delta_p_5m) if delta_p_5m is not None else None,
                delta_p_15m=float(delta_p_15m) if delta_p_15m is not None else None,
                n_5m=int(n_5m) if n_5m is not None else None,
                primary_dex=getattr(latest_data, "primary_dex", None),
                primary_pool_type=getattr(latest_data, "pool_type", None),
                image_url=getattr(latest_data, "image_url", None),
                pools=pools,
                fetched_at=fetched_at,
                scored_at=getattr(latest_data, "created_at", None).isoformat() if getattr(latest_data, "created_at", None) else None,
                last_processed_at=token.last_updated_at.replace(tzinfo=timezone.utc).isoformat() if token.last_updated_at else None,
                solscan_url=f"https://solscan.io/token/{token.mint_address}",
                raw_components=raw_components,
                smoothed_components=smoothed_components,
                scoring_model=getattr(latest_data, "scoring_model", None),
                created_at=token.created_at.replace(tzinfo=timezone.utc).isoformat() if token.created_at else None,
                spam_metrics=None,
            )
        )

    page_size = limit
    page = (offset // page_size) + 1 if page_size else 1
    meta = TokensMeta(
        total=total,
        limit=limit,
        offset=offset,
        page=page,
        page_size=page_size,
        has_prev=offset > 0,
        has_next=(offset + limit) < total,
        sort=sort,
        min_score=float(min_score) if min_score is not None else None,
    )
    return TokensResponse(total=total, items=items, meta=meta)


class TokenHistoryItem(BaseModel):
    created_at: str
    score: Optional[float] = None
    metrics: Optional[dict] = None


class TokenDetail(BaseModel):
    mint_address: str
    name: Optional[str] = None
    symbol: Optional[str] = None
    status: str
    score: Optional[float] = None
    liquidity_usd: Optional[float] = Field(default=None, description="L_tot")
    metrics: Optional[dict] = None
    score_history: list[TokenHistoryItem]
    pools: Optional[list[PoolItem]] = None
    solscan_url: str
    image_url: Optional[str] = None


@router.get("/{mint}", response_model=TokenDetail)
async def get_token_detail(mint: str, db: Session = Depends(get_db), history_limit: int = Query(20, ge=1, le=200)) -> TokenDetail:
    repo = TokensRepository(db)
    token = repo.get_by_mint(mint)
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="token not found")
    snap = repo.get_latest_snapshot(token.id)
    history = repo.get_score_history(token.id, limit=history_limit)
    pools: list[PoolItem] | None = None
    if snap and snap.metrics and isinstance(snap.metrics, dict) and "pools" in snap.metrics:
        # Исключаем только classic pumpfun; допускаем pumpfun-amm и pumpswap
        exclude = {"pumpfun"}
        pools = [
            PoolItem(
                address=p.get("address"),
                dex=p.get("dex"),
                quote=p.get("quote"),
                solscan_url=(f"https://solscan.io/address/{p.get('address')}" if p.get('address') else None),
                pool_type=p.get("pool_type"),
                owner_program=p.get("owner_program"),
            )
            for p in (snap.metrics.get("pools") or [])
            if isinstance(p, dict) and p.get("is_wsol") and str(p.get("dex") or "") not in exclude
        ]
    return TokenDetail(
        mint_address=token.mint_address,
        name=token.name,
        symbol=token.symbol,
        status=token.status,
        score=float(snap.smoothed_score) if (snap and snap.smoothed_score is not None) else (float(snap.score) if (snap and snap.score is not None) else None),
        liquidity_usd=(float(snap.metrics.get("L_tot")) if snap and snap.metrics and snap.metrics.get("L_tot") is not None else None),
        metrics=(snap.metrics if (snap and snap.metrics) else None),
        score_history=[
            TokenHistoryItem(created_at=ts.created_at.isoformat(), score=(float(ts.score) if ts.score is not None else None), metrics=ts.metrics)
            for ts in history
        ],
        pools=pools,
        solscan_url=f"https://solscan.io/token/{token.mint_address}",
        image_url=(snap.metrics.get("image_url") if snap and snap.metrics else None),
    )


class RefreshResult(BaseModel):
    updated_snapshot_id: int
    score: Optional[float] = None


@router.post("/{mint}/refresh", response_model=RefreshResult)
async def refresh_token(mint: str, db: Session = Depends(get_db)) -> RefreshResult:
    repo = TokensRepository(db)
    token = repo.get_by_mint(mint)
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="token not found")
    # Fetch pairs using resilient client with rate limiting
    from src.adapters.services.resilient_dexscreener_client import ResilientDexScreenerClient
    import time
    time.sleep(1.0)  # Rate limiting: 1s delay
    resilient_client = ResilientDexScreenerClient(timeout=3.0, cache_ttl=300)  # 5 min cache
    pairs = resilient_client.get_pairs(mint)
    if pairs is None:
        raise HTTPException(status_code=503, detail="dexscreener unavailable")
    
    # Get settings (legacy scoring endpoint)
    settings = SettingsService(db)
    smoothing_alpha = float(settings.get("score_smoothing_alpha") or 0.3)
    min_pool_liquidity = float(settings.get("min_pool_liquidity_usd") or 500)
    max_price_change = 0.5  # Fixed value for legacy compatibility
    
    weights = {
        "weight_s": float(settings.get("weight_s") or 0.35),
        "weight_l": float(settings.get("weight_l") or 0.25),
        "weight_m": float(settings.get("weight_m") or 0.20),
        "weight_t": float(settings.get("weight_t") or 0.20),
    }
    
    # Get previous smoothed score
    previous_smoothed_score = repo.get_previous_smoothed_score(token.id)
    
    # Aggregate metrics with data filtering
    from src.domain.metrics.dex_aggregator import aggregate_wsol_metrics
    pool_service = PoolTypeService(db)
    try:
        enriched_pairs = pool_service.enrich_pairs(pairs)
        if not enriched_pairs:
            raise HTTPException(status_code=422, detail="no classified pools")

        metrics = aggregate_wsol_metrics(
            mint,
            enriched_pairs,
            min_liquidity_usd=min_pool_liquidity,
            max_price_change=max_price_change
        )
        pool_service.insert_primary_pool_type(metrics)
    finally:
        pool_service.close()
    
    from src.domain.scoring.scorer import compute_score, compute_smoothed_score
    score, _ = compute_score(metrics, weights)
    smoothed_score = compute_smoothed_score(score, previous_smoothed_score, smoothing_alpha)
    
    # Insert snapshot with both scores
    snap_id = repo.insert_score_snapshot(
        token_id=token.id, 
        metrics=metrics, 
        score=score, 
        smoothed_score=smoothed_score
    )
    
    return RefreshResult(updated_snapshot_id=snap_id, score=smoothed_score)


@router.get("/{mint}/pools", response_model=list[PoolItem])
async def get_token_pools(mint: str, db: Session = Depends(get_db)) -> list[PoolItem]:
    repo = TokensRepository(db)
    token = repo.get_by_mint(mint)
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="token not found")

    snap = repo.get_latest_snapshot(token.id)
    pools = []
    if snap and snap.metrics and isinstance(snap.metrics, dict) and "pools" in snap.metrics:
        exclude = {"pumpfun"}
        pools = [
            p for p in (snap.metrics.get("pools") or [])
            if isinstance(p, dict) and str(p.get("dex") or "") not in exclude and (p.get("is_wsol") or p.get("is_usdc"))
        ]
    else:
        # Фолбэк: получить актуальные пары через resilient client с агрессивным кешированием
        from src.adapters.services.resilient_dexscreener_client import ResilientDexScreenerClient
        import time
        time.sleep(1.0)  # Rate limiting: 1s delay
        resilient_client = ResilientDexScreenerClient(timeout=3.0, cache_ttl=300)  # 5 min cache
        pairs = resilient_client.get_pairs(mint)
        if pairs:
            pools = []
            _WSOL = {"WSOL", "SOL", "W_SOL", "W-SOL", "Wsol", "wSOL"}
            _USDC = {"USDC", "usdc"}
            exclude = {"pumpfun"}
            for p in pairs:
                try:
                    base = (p.get("baseToken") or {})
                    quote = (p.get("quoteToken") or {})
                    dex_id = str(p.get("dexId") or "")
                    if str(base.get("address")) == mint and str(quote.get("symbol", "")).upper() in (_WSOL | _USDC) and dex_id not in exclude:
                        pools.append(
                            {
                                "address": p.get("pairAddress") or p.get("address"),
                                "dex": dex_id,
                                "quote": quote.get("symbol"),
                            }
                        )
                except Exception:
                    continue
    items: list[PoolItem] = []
    for p in pools:
        addr = p.get("address") if isinstance(p, dict) else None
        items.append(
            PoolItem(
                address=addr,
                dex=p.get("dex") if isinstance(p, dict) else None,
                quote=p.get("quote") if isinstance(p, dict) else None,
                solscan_url=(f"https://solscan.io/address/{addr}" if addr else None),
                pool_type=p.get("pool_type") if isinstance(p, dict) else None,
                owner_program=p.get("owner_program") if isinstance(p, dict) else None,
            )
        )
    return items
