"""
Token processing performance monitoring system.

This module provides comprehensive monitoring of token status transitions,
processing performance, and activation bottlenecks.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque

from src.adapters.db.base import SessionLocal
from src.adapters.repositories.tokens_repo import TokensRepository

log = logging.getLogger("token_monitor")


@dataclass
class TokenStatusTransition:
    """Record of a token status transition."""
    mint_address: str
    from_status: str
    to_status: str
    timestamp: datetime
    processing_time_seconds: Optional[float] = None
    reason: Optional[str] = None


@dataclass
class TokenProcessingMetrics:
    """Token processing performance metrics."""
    timestamp: datetime
    
    # Status counts
    monitoring_count: int
    active_count: int
    archived_count: int
    
    # Processing rates
    tokens_processed_per_minute: float
    activations_per_hour: float
    
    # Timing metrics
    avg_time_to_activation_minutes: Optional[float]
    tokens_stuck_over_3m: int
    
    # Performance indicators
    processing_backlog: int
    activation_success_rate: float
    
    # Issues
    failed_activations_last_hour: int
    stalled_tokens: List[str]


@dataclass
class TokenActivationAnalysis:
    """Analysis of token activation process."""
    mint_address: str
    status: str
    created_at: datetime
    last_processed_at: datetime
    
    # Timing
    time_in_monitoring_hours: float
    time_since_last_process_minutes: float
    
    # Activation readiness
    meets_activation_criteria: bool
    blocking_conditions: List[str]
    
    # Pool information
    pool_count: int
    total_liquidity_usd: float
    external_pools_with_liquidity: int


class TokenProcessingMonitor:
    """
    Comprehensive token processing performance monitor.
    
    Tracks token status transitions, identifies bottlenecks,
    and provides detailed analysis of processing performance.
    """
    
    def __init__(self):
        # Transition history for analysis
        self.transition_history: deque = deque(maxlen=1000)
        
        # Performance metrics history
        self.metrics_history: deque = deque(maxlen=100)
        
        # Stuck token tracking
        self.stuck_tokens_tracker: Dict[str, datetime] = {}
        
        # Processing rate tracking
        self.processing_rate_samples: deque = deque(maxlen=20)
        
    def record_status_transition(
        self, 
        mint_address: str, 
        from_status: str, 
        to_status: str,
        processing_time_seconds: Optional[float] = None,
        reason: Optional[str] = None
    ):
        """Record a token status transition."""
        transition = TokenStatusTransition(
            mint_address=mint_address,
            from_status=from_status,
            to_status=to_status,
            timestamp=datetime.utcnow(),
            processing_time_seconds=processing_time_seconds,
            reason=reason
        )
        
        self.transition_history.append(transition)
        
        # Update stuck tokens tracker
        if to_status != "monitoring":
            # Token is no longer stuck
            self.stuck_tokens_tracker.pop(mint_address, None)
        elif from_status != "monitoring" and to_status == "monitoring":
            # Token entered monitoring status
            self.stuck_tokens_tracker[mint_address] = transition.timestamp
        
        log.info(
            "token_status_transition",
            extra={
                "mint_address": mint_address,
                "from_status": from_status,
                "to_status": to_status,
                "processing_time_seconds": processing_time_seconds,
                "reason": reason
            }
        )
    
    def collect_current_metrics(self) -> TokenProcessingMetrics:
        """Collect current token processing metrics."""
        try:
            with SessionLocal() as db:
                repo = TokensRepository(db)
                
                # Get status counts
                status_counts = self._get_status_counts(repo)
                
                # Calculate processing rates
                processing_rate = self._calculate_processing_rate()
                activation_rate = self._calculate_activation_rate()
                
                # Get timing metrics
                avg_activation_time = self._calculate_avg_activation_time()
                stuck_tokens = self._get_stuck_tokens_count()
                
                # Get performance indicators
                backlog = status_counts.get("monitoring", 0)
                success_rate = self._calculate_activation_success_rate()
                
                # Get recent issues
                failed_activations = self._count_failed_activations()
                stalled_tokens = self._identify_stalled_tokens(repo)
                
                metrics = TokenProcessingMetrics(
                    timestamp=datetime.utcnow(),
                    monitoring_count=status_counts.get("monitoring", 0),
                    active_count=status_counts.get("active", 0),
                    archived_count=status_counts.get("archived", 0),
                    tokens_processed_per_minute=processing_rate,
                    activations_per_hour=activation_rate,
                    avg_time_to_activation_minutes=avg_activation_time,
                    tokens_stuck_over_3m=stuck_tokens,
                    processing_backlog=backlog,
                    activation_success_rate=success_rate,
                    failed_activations_last_hour=failed_activations,
                    stalled_tokens=stalled_tokens
                )
                
                # Store in history
                self.metrics_history.append(metrics)
                
                return metrics
                
        except Exception as e:
            log.error(f"Error collecting token metrics: {e}", exc_info=True)
            # Return empty metrics on error
            return TokenProcessingMetrics(
                timestamp=datetime.utcnow(),
                monitoring_count=0,
                active_count=0,
                archived_count=0,
                tokens_processed_per_minute=0.0,
                activations_per_hour=0.0,
                avg_time_to_activation_minutes=None,
                tokens_stuck_over_3m=0,
                processing_backlog=0,
                activation_success_rate=0.0,
                failed_activations_last_hour=0,
                stalled_tokens=[]
            )
    
    def analyze_stuck_tokens(self, limit: int = 20) -> List[TokenActivationAnalysis]:
        """Analyze tokens stuck in monitoring status."""
        try:
            with SessionLocal() as db:
                repo = TokensRepository(db)
                
                # Get tokens in monitoring status for >3 minutes
                cutoff_time = datetime.utcnow() - timedelta(minutes=3)
                
                # This would need to be implemented in the repository
                # For now, we'll use a simple query approach
                stuck_tokens = []
                
                # Get all monitoring tokens
                monitoring_tokens = repo.get_tokens_by_status("monitoring", limit=100)
                
                for token in monitoring_tokens:
                    if token.created_at < cutoff_time:
                        analysis = self._analyze_token_activation(token, repo)
                        stuck_tokens.append(analysis)
                
                # Sort by time in monitoring (longest first)
                stuck_tokens.sort(key=lambda x: x.time_in_monitoring_hours, reverse=True)
                
                return stuck_tokens[:limit]
                
        except Exception as e:
            log.error(f"Error analyzing stuck tokens: {e}", exc_info=True)
            return []
    
    def _get_status_counts(self, repo: TokensRepository) -> Dict[str, int]:
        """Get count of tokens by status."""
        try:
            # This would ideally be a single query, but we'll use multiple calls
            counts = {}
            
            for status in ["monitoring", "active", "archived"]:
                tokens = repo.get_tokens_by_status(status, limit=1000)  # Get a large sample
                counts[status] = len(tokens)
            
            return counts
            
        except Exception as e:
            log.error(f"Error getting status counts: {e}")
            return {}
    
    def _calculate_processing_rate(self) -> float:
        """Calculate tokens processed per minute based on recent transitions."""
        if len(self.transition_history) < 2:
            return 0.0
        
        # Look at transitions in the last 10 minutes
        cutoff_time = datetime.utcnow() - timedelta(minutes=10)
        recent_transitions = [
            t for t in self.transition_history 
            if t.timestamp >= cutoff_time
        ]
        
        if not recent_transitions:
            return 0.0
        
        # Calculate rate
        time_span_minutes = 10.0
        return len(recent_transitions) / time_span_minutes
    
    def _calculate_activation_rate(self) -> float:
        """Calculate activations per hour based on recent transitions."""
        if len(self.transition_history) < 1:
            return 0.0
        
        # Look at activations in the last hour
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        activations = [
            t for t in self.transition_history 
            if t.timestamp >= cutoff_time and t.to_status == "active"
        ]
        
        return len(activations)
    
    def _calculate_avg_activation_time(self) -> Optional[float]:
        """Calculate average time to activation in minutes."""
        activation_times = []
        
        for transition in self.transition_history:
            if (transition.to_status == "active" and 
                transition.processing_time_seconds is not None):
                activation_times.append(transition.processing_time_seconds / 60.0)
        
        if not activation_times:
            return None
        
        return sum(activation_times) / len(activation_times)
    
    def _get_stuck_tokens_count(self) -> int:
        """Get count of tokens stuck for >3 minutes."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=3)
        
        stuck_count = 0
        for mint_address, stuck_since in self.stuck_tokens_tracker.items():
            if stuck_since < cutoff_time:
                stuck_count += 1
        
        return stuck_count
    
    def _calculate_activation_success_rate(self) -> float:
        """Calculate activation success rate based on recent history."""
        if len(self.transition_history) < 10:
            return 0.0
        
        # Look at recent transitions to monitoring and their outcomes
        recent_monitoring_entries = [
            t for t in self.transition_history 
            if t.to_status == "monitoring"
        ]
        
        if not recent_monitoring_entries:
            return 0.0
        
        # Count how many eventually activated
        activated_count = 0
        for entry in recent_monitoring_entries:
            # Look for subsequent activation
            for later_transition in self.transition_history:
                if (later_transition.mint_address == entry.mint_address and
                    later_transition.timestamp > entry.timestamp and
                    later_transition.to_status == "active"):
                    activated_count += 1
                    break
        
        return (activated_count / len(recent_monitoring_entries)) * 100.0
    
    def _count_failed_activations(self) -> int:
        """Count failed activations in the last hour."""
        # This would need to be implemented based on how failures are tracked
        # For now, return 0 as we don't have explicit failure tracking
        return 0
    
    def _identify_stalled_tokens(self, repo: TokensRepository) -> List[str]:
        """Identify tokens that appear to be stalled in processing."""
        try:
            stalled = []
            
            # Get tokens that haven't been processed recently
            cutoff_time = datetime.utcnow() - timedelta(minutes=5)
            
            monitoring_tokens = repo.get_tokens_by_status("monitoring", limit=50)
            
            for token in monitoring_tokens:
                if token.last_processed_at and token.last_processed_at < cutoff_time:
                    stalled.append(token.mint_address)
            
            return stalled[:10]  # Limit to 10 for readability
            
        except Exception as e:
            log.error(f"Error identifying stalled tokens: {e}")
            return []
    
    def _analyze_token_activation(self, token, repo: TokensRepository) -> TokenActivationAnalysis:
        """Analyze why a specific token hasn't activated."""
        now = datetime.utcnow()
        
        # Calculate timing
        time_in_monitoring = (now - token.created_at).total_seconds() / 3600.0
        time_since_process = (now - token.last_processed_at).total_seconds() / 60.0 if token.last_processed_at else 0
        
        # Analyze activation criteria (simplified)
        meets_criteria = False
        blocking_conditions = []
        
        # Check basic conditions
        if not token.liquidity_usd or token.liquidity_usd < 50:
            blocking_conditions.append("insufficient_liquidity")
        
        if time_since_process > 5:
            blocking_conditions.append("not_recently_processed")
        
        # If no blocking conditions, it should meet criteria
        meets_criteria = len(blocking_conditions) == 0
        
        # Get pool information (simplified)
        pool_count = 1  # Placeholder
        external_pools = 0  # Placeholder
        
        return TokenActivationAnalysis(
            mint_address=token.mint_address,
            status=token.status,
            created_at=token.created_at,
            last_processed_at=token.last_processed_at or now,
            time_in_monitoring_hours=time_in_monitoring,
            time_since_last_process_minutes=time_since_process,
            meets_activation_criteria=meets_criteria,
            blocking_conditions=blocking_conditions,
            pool_count=pool_count,
            total_liquidity_usd=token.liquidity_usd or 0.0,
            external_pools_with_liquidity=external_pools
        )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        current_metrics = self.collect_current_metrics()
        
        # Calculate trends if we have history
        trend_analysis = {}
        if len(self.metrics_history) >= 2:
            prev_metrics = list(self.metrics_history)[-2]
            
            trend_analysis = {
                "monitoring_trend": current_metrics.monitoring_count - prev_metrics.monitoring_count,
                "processing_rate_trend": current_metrics.tokens_processed_per_minute - prev_metrics.tokens_processed_per_minute,
                "activation_rate_trend": current_metrics.activations_per_hour - prev_metrics.activations_per_hour
            }
        
        return {
            "current_metrics": {
                "monitoring_count": current_metrics.monitoring_count,
                "active_count": current_metrics.active_count,
                "archived_count": current_metrics.archived_count,
                "processing_rate": current_metrics.tokens_processed_per_minute,
                "activation_rate": current_metrics.activations_per_hour,
                "avg_activation_time": current_metrics.avg_time_to_activation_minutes,
                "stuck_tokens": current_metrics.tokens_stuck_over_3m,
                "backlog": current_metrics.processing_backlog,
                "success_rate": current_metrics.activation_success_rate
            },
            "trends": trend_analysis,
            "issues": {
                "failed_activations": current_metrics.failed_activations_last_hour,
                "stalled_tokens": current_metrics.stalled_tokens
            },
            "transition_history_size": len(self.transition_history),
            "last_updated": current_metrics.timestamp.isoformat()
        }


# Global token monitor instance
_token_monitor = None


def get_token_monitor() -> TokenProcessingMonitor:
    """Get the global token processing monitor instance."""
    global _token_monitor
    if _token_monitor is None:
        _token_monitor = TokenProcessingMonitor()
    return _token_monitor