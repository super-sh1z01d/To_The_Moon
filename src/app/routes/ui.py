from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, FileResponse


router = APIRouter()

FRONTEND_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"


def _resolve_dist_file(name: str) -> Path:
    file_path = FRONTEND_DIST / name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"{name} not found")
    return file_path


@router.get("/", include_in_schema=False)
async def landing_page():
    index_file = FRONTEND_DIST / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Landing page not built")
    return FileResponse(index_file, media_type="text/html")


@router.get("/favicon.ico", include_in_schema=False)
@router.get("/favicon.svg", include_in_schema=False)
async def favicon() -> FileResponse:
    file_path = _resolve_dist_file("favicon.svg")
    return FileResponse(file_path, media_type="image/svg+xml")


@router.get("/ui", response_class=HTMLResponse, include_in_schema=False)
async def ui_page() -> str:
    return """
<!doctype html>
<html lang=ru>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>To The Moon — Дашборд</title>
    <style>
      body{font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin:20px;}
      table{border-collapse:collapse; width:100%;}
      th,td{border:1px solid #ddd; padding:6px 8px; font-size:14px}
      th{background:#f8f8f8; text-align:left}
      .pill{display:inline-block; padding:2px 6px; border-radius:10px; background:#eef}
      .muted{color:#666}
      .btn{padding:4px 8px; font-size:12px; cursor:pointer}
      .pool{font-size:12px; margin-right:8px}
    </style>
  </head>
  <body>
    <h1>To The Moon — Активные токены</h1>
    <div>
      Минимальный скор: <input id="minScore" type="number" step="0.01" value="0.0" style="width:80px"/>
      <button class="btn" onclick="loadTokens()">Обновить</button>
    </div>
    <table id="tbl">
      <thead>
        <tr>
          <th>Название (Символ)</th>
          <th>Скор</th>
          <th>Ликвидность (USD)</th>
          <th>Δ 5м / 15м</th>
          <th>Транз. 5м</th>
          <th>Пулы</th>
          <th>Solscan</th>
        </tr>
      </thead>
      <tbody></tbody>
    </table>
    <script>
      async function loadTokens(){
        const min = document.getElementById('minScore').value || '0';
        const res = await fetch(`/tokens?limit=50&min_score=${encodeURIComponent(min)}`);
        const data = await res.json();
        const tbody = document.querySelector('#tbl tbody');
        tbody.innerHTML = '';
        for(const it of data.items){
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td>${(it.name||'—')} <span class="muted">(${it.symbol||''})</span></td>
            <td>${it.score ?? '—'}</td>
            <td>${it.liquidity_usd ? ('$'+Number(it.liquidity_usd).toLocaleString()) : '—'}</td>
            <td>${fmtPct(it.delta_p_5m)} / ${fmtPct(it.delta_p_15m)}</td>
            <td>${it.n_5m ?? '—'}</td>
            <td><button class="btn" onclick="showPools('${it.mint_address}', this)">Показать пулы</button><div class="muted"></div></td>
            <td><a href="${it.solscan_url}" target="_blank">Открыть</a></td>`;
          tbody.appendChild(tr);
        }
      }
      function fmtPct(x){
        if (x==null) return '—';
        const p = (Number(x)*100).toFixed(2)+'%';
        return p;
      }
      async function showPools(mint, btn){
        const host = btn.parentElement.querySelector('div');
        host.textContent = 'Загрузка...';
        try{
          const res = await fetch(`/tokens/${mint}/pools`);
          const pools = await res.json();
          if(!Array.isArray(pools) || pools.length===0){ host.textContent = 'Нет данных'; return; }
          host.innerHTML = pools.map(p => {
            const link = p.solscan_url ? `<a href="${p.solscan_url}" target="_blank">${p.address||'—'}</a>` : (p.address||'—');
            const dex = p.dex || '—';
            return `<span class="pool">${link} <span class="pill">${dex}</span></span>`;
          }).join('');
        }catch(e){ host.textContent = 'Ошибка'; }
      }
      loadTokens();
    </script>
  </body>
 </html>
    """
