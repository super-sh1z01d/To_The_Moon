"""
NotArb integration API endpoints
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.adapters.db.deps import get_db
from src.integrations.notarb_pools import NotArbPoolsGenerator

router = APIRouter(prefix="/notarb", tags=["notarb"])


@router.get("/pools", response_model=List[List[str]])
async def get_token_pools(db: Session = Depends(get_db)) -> List[List[str]]:
    """
    Get token pools from file (for NotArb bot) - backward compatibility
    
    Returns list where each inner list contains all pool addresses for one token.
    File is updated automatically by scheduler.
    """
    try:
        import json
        from pathlib import Path
        from src.core.config import get_config
        
        config = get_config()
        file_path = Path(getattr(config, 'notarb_config_path', 'markets.json'))
        
        if not file_path.exists():
            # Generate file if it doesn't exist
            generator = NotArbPoolsGenerator(str(file_path))
            generator.export_pools_config()
        
        # Read from file with retry on corruption
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                break
            except (json.JSONDecodeError, IOError) as e:
                if attempt == max_retries - 1:
                    raise HTTPException(status_code=500, detail=f"File corrupted or locked: {str(e)}")
                # Wait a bit and retry
                import time
                time.sleep(0.1)
        
        # Extract just pools for backward compatibility
        if isinstance(data, dict) and "tokens" in data:
            return [token["pools"] for token in data["tokens"]]
        else:
            # Old format fallback
            return data if isinstance(data, list) else []
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read token pools file: {str(e)}")


@router.get("/config", response_model=Dict[str, Any])
async def get_notarb_config(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get NotArb configuration with metadata (for debugging/monitoring)
    
    Returns configuration including tokens, pools, and metadata.
    """
    try:
        generator = NotArbPoolsGenerator()
        tokens_data = generator.get_top_tokens_with_pools(limit=3)
        
        if not tokens_data:
            return {
                "metadata": {
                    "min_score_threshold": generator.get_notarb_min_score(),
                    "total_tokens": 0,
                    "total_pool_groups": 0
                },
                "tokens": [],
                "token_pools": []
            }
        
        token_pools = generator.generate_token_pools(tokens_data)
        
        return {
            "metadata": {
                "min_score_threshold": generator.get_notarb_min_score(),
                "total_tokens": len(tokens_data),
                "total_pool_groups": len(token_pools)
            },
            "tokens": tokens_data,
            "token_pools": token_pools
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate config: {str(e)}")


@router.get("/markets", response_model=Dict[str, Any])
async def get_markets_json(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get markets.json with full metadata from file
    
    Returns complete data with token metadata and pools.
    File is updated automatically by scheduler.
    """
    try:
        import json
        from pathlib import Path
        from src.core.config import get_config
        
        config = get_config()
        file_path = Path(getattr(config, 'notarb_config_path', 'markets.json'))
        
        if not file_path.exists():
            # Generate file if it doesn't exist
            generator = NotArbPoolsGenerator(str(file_path))
            generator.export_pools_config()
        
        # Read from file with retry on corruption
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                break
            except (json.JSONDecodeError, IOError) as e:
                if attempt == max_retries - 1:
                    raise HTTPException(status_code=500, detail=f"File corrupted or locked: {str(e)}")
                # Wait a bit and retry
                import time
                time.sleep(0.1)
        
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read markets file: {str(e)}")


@router.get("/markets/pools-only", response_model=List[List[str]])
async def get_markets_pools_only(db: Session = Depends(get_db)) -> List[List[str]]:
    """
    Get markets in old format (just pools arrays)
    
    Returns array where each inner array contains all pools for one token.
    """
    try:
        import json
        from pathlib import Path
        from src.core.config import get_config
        
        config = get_config()
        file_path = Path(getattr(config, 'notarb_config_path', 'markets.json'))
        
        if not file_path.exists():
            # Generate file if it doesn't exist
            generator = NotArbPoolsGenerator(str(file_path))
            generator.export_pools_config()
        
        # Read from file with retry on corruption
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                break
            except (json.JSONDecodeError, IOError) as e:
                if attempt == max_retries - 1:
                    raise HTTPException(status_code=500, detail=f"File corrupted or locked: {str(e)}")
                # Wait a bit and retry
                import time
                time.sleep(0.1)
        
        # Extract just pools
        if isinstance(data, dict) and "tokens" in data:
            return [token["pools"] for token in data["tokens"]]
        else:
            # Old format fallback
            return data if isinstance(data, list) else []
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read markets file: {str(e)}")


@router.post("/export")
async def export_pools_config(output_path: str = "markets.json", db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Force update of NotArb pools file
    
    Args:
        output_path: Path to output file
        
    Returns:
        Export status and metadata
    """
    try:
        generator = NotArbPoolsGenerator(output_path)
        success = generator.export_pools_config()
        
        if success:
            tokens_data = generator.get_top_tokens_with_pools(limit=3)
            token_pools = generator.generate_token_pools(tokens_data)
            
            return {
                "success": True,
                "output_path": output_path,
                "metadata": {
                    "min_score_threshold": generator.get_notarb_min_score(),
                    "total_tokens": len(tokens_data),
                    "total_pool_groups": len(token_pools)
                }
            }
        else:
            return {
                "success": False,
                "error": "Export failed"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/file-info")
async def get_file_info(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get information about the NotArb pools file
    
    Returns:
        File status and metadata
    """
    try:
        import os
        from pathlib import Path
        from datetime import datetime, timezone
        from src.core.config import get_config
        
        config = get_config()
        file_path = Path(getattr(config, 'notarb_config_path', 'markets.json'))
        
        if file_path.exists():
            stat = file_path.stat()
            modified_time = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            
            # Try to read file content for metadata
            try:
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    pool_count = sum(len(group) for group in content) if isinstance(content, list) else 0
            except:
                pool_count = 0
            
            return {
                "file_exists": True,
                "file_path": str(file_path),
                "file_size": stat.st_size,
                "last_modified": modified_time.isoformat(),
                "total_pool_groups": len(content) if isinstance(content, list) else 0,
                "total_pools": pool_count
            }
        else:
            return {
                "file_exists": False,
                "file_path": str(file_path),
                "message": "File will be created by scheduler or manual export"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file info: {str(e)}")