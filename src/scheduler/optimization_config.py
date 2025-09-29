"""
Configuration for scheduler optimizations.
Allows fine-tuning of parallel processing parameters.
"""

from dataclasses import dataclass
from typing import Dict, Any
import os


@dataclass
class ParallelProcessingConfig:
    """Configuration for parallel processing."""
    
    # Concurrency limits
    max_concurrent_hot: int = 8
    max_concurrent_cold: int = 12
    max_concurrent_under_load: int = 4
    
    # Timeout settings
    timeout_hot: float = 3.0
    timeout_cold: float = 2.0
    timeout_under_load: float = 1.5
    
    # Adaptive batch sizing
    enable_adaptive_batching: bool = True
    min_batch_size: int = 10
    max_batch_size: int = 100
    batch_size_adjustment_factor: float = 0.2
    
    # Performance thresholds
    high_cpu_threshold: float = 80.0
    medium_cpu_threshold: float = 60.0
    low_cpu_threshold: float = 30.0
    
    high_memory_threshold: float = 85.0
    medium_memory_threshold: float = 70.0
    low_memory_threshold: float = 50.0
    
    # API performance thresholds (milliseconds)
    slow_api_threshold: float = 2000.0
    fast_api_threshold: float = 500.0
    
    # Circuit breaker settings
    enable_circuit_breaker: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout: float = 60.0
    
    # Caching settings
    enable_caching: bool = True
    cache_ttl_hot: int = 15
    cache_ttl_cold: int = 30
    
    # Retry settings
    enable_retry: bool = True
    max_retries: int = 3
    retry_backoff_factor: float = 1.5


@dataclass
class OptimizationConfig:
    """Main optimization configuration."""
    
    # Feature flags
    enable_parallel_processing: bool = True
    enable_adaptive_batching: bool = True
    enable_dynamic_timeouts: bool = True
    enable_performance_monitoring: bool = True
    
    # Parallel processing config
    parallel_processing: ParallelProcessingConfig = None
    
    # Performance monitoring
    performance_history_size: int = 10
    performance_log_interval: int = 100  # Log every N processed tokens
    
    # Load balancing
    enable_load_balancing: bool = True
    load_check_interval: float = 5.0  # seconds
    
    def __post_init__(self):
        if self.parallel_processing is None:
            self.parallel_processing = ParallelProcessingConfig()


def load_optimization_config() -> OptimizationConfig:
    """Load optimization configuration from environment variables."""
    config = OptimizationConfig()
    
    # Load feature flags from environment
    config.enable_parallel_processing = os.getenv("ENABLE_PARALLEL_PROCESSING", "true").lower() == "true"
    config.enable_adaptive_batching = os.getenv("ENABLE_ADAPTIVE_BATCHING", "true").lower() == "true"
    config.enable_dynamic_timeouts = os.getenv("ENABLE_DYNAMIC_TIMEOUTS", "true").lower() == "true"
    config.enable_performance_monitoring = os.getenv("ENABLE_PERFORMANCE_MONITORING", "true").lower() == "true"
    
    # Load parallel processing settings
    parallel_config = ParallelProcessingConfig()
    
    # Concurrency settings
    parallel_config.max_concurrent_hot = int(os.getenv("MAX_CONCURRENT_HOT", "8"))
    parallel_config.max_concurrent_cold = int(os.getenv("MAX_CONCURRENT_COLD", "12"))
    parallel_config.max_concurrent_under_load = int(os.getenv("MAX_CONCURRENT_UNDER_LOAD", "4"))
    
    # Timeout settings
    parallel_config.timeout_hot = float(os.getenv("TIMEOUT_HOT", "3.0"))
    parallel_config.timeout_cold = float(os.getenv("TIMEOUT_COLD", "2.0"))
    parallel_config.timeout_under_load = float(os.getenv("TIMEOUT_UNDER_LOAD", "1.5"))
    
    # Batch sizing
    parallel_config.min_batch_size = int(os.getenv("MIN_BATCH_SIZE", "10"))
    parallel_config.max_batch_size = int(os.getenv("MAX_BATCH_SIZE", "100"))
    
    # Performance thresholds
    parallel_config.high_cpu_threshold = float(os.getenv("HIGH_CPU_THRESHOLD", "80.0"))
    parallel_config.medium_cpu_threshold = float(os.getenv("MEDIUM_CPU_THRESHOLD", "60.0"))
    parallel_config.low_cpu_threshold = float(os.getenv("LOW_CPU_THRESHOLD", "30.0"))
    
    parallel_config.high_memory_threshold = float(os.getenv("HIGH_MEMORY_THRESHOLD", "85.0"))
    parallel_config.medium_memory_threshold = float(os.getenv("MEDIUM_MEMORY_THRESHOLD", "70.0"))
    parallel_config.low_memory_threshold = float(os.getenv("LOW_MEMORY_THRESHOLD", "50.0"))
    
    # Cache settings
    parallel_config.cache_ttl_hot = int(os.getenv("CACHE_TTL_HOT", "15"))
    parallel_config.cache_ttl_cold = int(os.getenv("CACHE_TTL_COLD", "30"))
    
    config.parallel_processing = parallel_config
    
    return config


def get_optimization_config() -> OptimizationConfig:
    """Get cached optimization configuration."""
    global _optimization_config
    if _optimization_config is None:
        _optimization_config = load_optimization_config()
    return _optimization_config


def update_optimization_config(updates: Dict[str, Any]):
    """Update optimization configuration at runtime."""
    global _optimization_config
    config = get_optimization_config()
    
    for key, value in updates.items():
        if hasattr(config, key):
            setattr(config, key, value)
        elif hasattr(config.parallel_processing, key):
            setattr(config.parallel_processing, key, value)
    
    return config


def reset_optimization_config():
    """Reset optimization configuration to defaults."""
    global _optimization_config
    _optimization_config = None


# Global configuration instance
_optimization_config: OptimizationConfig = None


# Environment-based configuration
def is_optimization_enabled() -> bool:
    """Check if optimizations are enabled based on environment."""
    # Disable optimizations in development by default
    app_env = os.getenv("APP_ENV", "dev")
    if app_env == "dev":
        return os.getenv("ENABLE_SCHEDULER_OPTIMIZATION", "false").lower() == "true"
    
    # Enable optimizations in production by default
    return os.getenv("ENABLE_SCHEDULER_OPTIMIZATION", "true").lower() == "true"


def get_performance_profile() -> str:
    """Get performance profile based on environment and server specs."""
    app_env = os.getenv("APP_ENV", "dev")
    
    # Check if we're on the new powerful server
    import psutil
    cpu_count = psutil.cpu_count()
    memory_gb = psutil.virtual_memory().total / (1024**3)
    
    if cpu_count >= 4 and memory_gb >= 8:
        return "high_performance"
    elif cpu_count >= 2 and memory_gb >= 4:
        return "medium_performance"
    else:
        return "low_performance"


def apply_performance_profile(config: OptimizationConfig, profile: str):
    """Apply performance profile to configuration."""
    if profile == "high_performance":
        # Aggressive settings for powerful servers
        config.parallel_processing.max_concurrent_hot = 12
        config.parallel_processing.max_concurrent_cold = 16
        config.parallel_processing.max_batch_size = 150
        config.parallel_processing.timeout_hot = 4.0
        config.parallel_processing.timeout_cold = 3.0
        
    elif profile == "medium_performance":
        # Balanced settings
        config.parallel_processing.max_concurrent_hot = 8
        config.parallel_processing.max_concurrent_cold = 12
        config.parallel_processing.max_batch_size = 100
        config.parallel_processing.timeout_hot = 3.0
        config.parallel_processing.timeout_cold = 2.0
        
    elif profile == "low_performance":
        # Conservative settings for limited resources
        config.parallel_processing.max_concurrent_hot = 4
        config.parallel_processing.max_concurrent_cold = 6
        config.parallel_processing.max_batch_size = 50
        config.parallel_processing.timeout_hot = 2.0
        config.parallel_processing.timeout_cold = 1.5