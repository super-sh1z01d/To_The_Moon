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
@router.get("/markets.json", response_model=Dict[str, Any])  # Alias with .json
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
            result_data = generator.generate_token_pools_with_metadata(tokens_data)
            
            return {
                "success": True,
                "output_path": output_path,
                "metadata": {
                    "min_score_threshold": generator.get_notarb_min_score(),
                    "total_tokens": len(tokens_data),
                    "total_pool_groups": len(result_data.get("tokens", []))
                }
            }
        else:
            return {
                "success": False,
                "error": "Export failed"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/pool-types")
async def get_pool_types_info(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get information about pool types in current top tokens
    
    Returns:
        Pool type classification and statistics
    """
    try:
        from src.domain.pools.pool_types import (
            PoolType, get_pool_type, get_pool_type_description, 
            classify_pools_by_type, DEX_POOL_TYPE_MAPPING
        )
        
        generator = NotArbPoolsGenerator()
        tokens_data = generator.get_top_tokens_with_pools(limit=10)  # Get more for analysis
        
        all_pools = []
        for token in tokens_data:
            all_pools.extend(token.get("pools", []))
        
        # Classify pools by type
        classified = classify_pools_by_type(all_pools)
        
        # Build response
        pool_type_info = {}
        total_pools = 0
        
        for pool_type, pools in classified.items():
            if pools:  # Only include non-empty categories
                pool_type_info[pool_type.value] = {
                    "count": len(pools),
                    "description": get_pool_type_description(pool_type),
                    "dexes": list(set(pool.get("dex", "") for pool in pools)),
                    "examples": [
                        {
                            "address": pool.get("address"),
                            "dex": pool.get("dex"),
                            "quote": pool.get("quote")
                        }
                        for pool in pools[:3]  # Show up to 3 examples
                    ]
                }
                total_pools += len(pools)
        
        return {
            "total_pools": total_pools,
            "total_tokens": len(tokens_data),
            "pool_types": pool_type_info,
            "supported_dexes": list(DEX_POOL_TYPE_MAPPING.keys()),
            "type_mapping": {dex: pool_type.value for dex, pool_type in DEX_POOL_TYPE_MAPPING.items()}
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze pool types: {str(e)}")


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