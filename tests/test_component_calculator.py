"""
Unit tests for ComponentCalculator class.

Tests all scoring components with normal cases, edge cases, and error conditions.
"""
import math
import pytest

from src.domain.scoring.component_calculator import ComponentCalculator


class TestComponentCalculator:
    """Test suite for ComponentCalculator class."""
    
    def test_calculate_tx_accel_normal_cases(self):
        """Test transaction acceleration calculation with normal inputs."""
        # Test case: equal rates (no acceleration)
        # 100 tx in 5m = 20 tx/min, 1200 tx in 1h = 20 tx/min
        result = ComponentCalculator.calculate_tx_accel(100, 1200)
        assert result == pytest.approx(1.0, rel=1e-6)
        
        # Test case: 2x acceleration
        # 200 tx in 5m = 40 tx/min, 1200 tx in 1h = 20 tx/min
        result = ComponentCalculator.calculate_tx_accel(200, 1200)
        assert result == pytest.approx(2.0, rel=1e-6)
        
        # Test case: deceleration
        # 50 tx in 5m = 10 tx/min, 1200 tx in 1h = 20 tx/min
        result = ComponentCalculator.calculate_tx_accel(50, 1200)
        assert result == pytest.approx(0.5, rel=1e-6)
    
    def test_calculate_tx_accel_edge_cases(self):
        """Test transaction acceleration with edge cases."""
        # Zero transactions in 5m
        result = ComponentCalculator.calculate_tx_accel(0, 1200)
        assert result == 0.0
        
        # Zero transactions in 1h
        result = ComponentCalculator.calculate_tx_accel(100, 0)
        assert result == 0.0
        
        # Negative values
        result = ComponentCalculator.calculate_tx_accel(-10, 1200)
        assert result == 0.0
        
        result = ComponentCalculator.calculate_tx_accel(100, -1200)
        assert result == 0.0
    
    def test_calculate_vol_momentum_normal_cases(self):
        """Test volume momentum calculation with normal inputs."""
        # Test case: equal momentum
        # 1000 USD in 5m, 12000 USD in 1h (avg 1000 per 5m)
        result = ComponentCalculator.calculate_vol_momentum(1000, 12000)
        assert result == pytest.approx(1.0, rel=1e-6)
        
        # Test case: 2x momentum
        # 2000 USD in 5m, 12000 USD in 1h (avg 1000 per 5m)
        result = ComponentCalculator.calculate_vol_momentum(2000, 12000)
        assert result == pytest.approx(2.0, rel=1e-6)
        
        # Test case: low momentum
        # 500 USD in 5m, 12000 USD in 1h (avg 1000 per 5m)
        result = ComponentCalculator.calculate_vol_momentum(500, 12000)
        assert result == pytest.approx(0.5, rel=1e-6)
    
    def test_calculate_vol_momentum_edge_cases(self):
        """Test volume momentum with edge cases."""
        # Zero volume in 5m
        result = ComponentCalculator.calculate_vol_momentum(0, 12000)
        assert result == 0.0
        
        # Zero volume in 1h
        result = ComponentCalculator.calculate_vol_momentum(1000, 0)
        assert result == 0.0
        
        # Negative values
        result = ComponentCalculator.calculate_vol_momentum(-1000, 12000)
        assert result == 0.0
        
        result = ComponentCalculator.calculate_vol_momentum(1000, -12000)
        assert result == 0.0
    
    def test_calculate_token_freshness_normal_cases(self):
        """Test token freshness calculation with normal inputs."""
        # Test case: very fresh token (1 hour old)
        result = ComponentCalculator.calculate_token_freshness(1.0, 6.0)
        assert result == pytest.approx(5.0/6.0, rel=1e-6)  # (6-1)/6 = 0.833
        
        # Test case: moderately fresh token (3 hours old)
        result = ComponentCalculator.calculate_token_freshness(3.0, 6.0)
        assert result == pytest.approx(0.5, rel=1e-6)  # (6-3)/6 = 0.5
        
        # Test case: at threshold (6 hours old)
        result = ComponentCalculator.calculate_token_freshness(6.0, 6.0)
        assert result == pytest.approx(0.0, rel=1e-6)
        
        # Test case: old token (8 hours old)
        result = ComponentCalculator.calculate_token_freshness(8.0, 6.0)
        assert result == 0.0
        
        # Test case: brand new token (0 hours old)
        result = ComponentCalculator.calculate_token_freshness(0.0, 6.0)
        assert result == pytest.approx(1.0, rel=1e-6)
    
    def test_calculate_token_freshness_edge_cases(self):
        """Test token freshness with edge cases."""
        # Negative time (shouldn't happen but handle gracefully)
        result = ComponentCalculator.calculate_token_freshness(-1.0, 6.0)
        assert result == 1.0
        
        # Zero threshold
        result = ComponentCalculator.calculate_token_freshness(1.0, 0.0)
        assert result == 0.0
        
        # Negative threshold
        result = ComponentCalculator.calculate_token_freshness(1.0, -6.0)
        assert result == 0.0
    
    def test_calculate_orderflow_imbalance_normal_cases(self):
        """Test orderflow imbalance calculation with normal inputs."""
        # Test case: balanced flow
        result = ComponentCalculator.calculate_orderflow_imbalance(1000, 1000)
        assert result == pytest.approx(0.0, rel=1e-6)
        
        # Test case: strong buying pressure
        result = ComponentCalculator.calculate_orderflow_imbalance(1500, 500)
        assert result == pytest.approx(0.5, rel=1e-6)  # (1500-500)/(1500+500) = 0.5
        
        # Test case: strong selling pressure
        result = ComponentCalculator.calculate_orderflow_imbalance(500, 1500)
        assert result == pytest.approx(-0.5, rel=1e-6)  # (500-1500)/(500+1500) = -0.5
        
        # Test case: extreme buying pressure
        result = ComponentCalculator.calculate_orderflow_imbalance(2000, 0)
        assert result == pytest.approx(1.0, rel=1e-6)
        
        # Test case: extreme selling pressure
        result = ComponentCalculator.calculate_orderflow_imbalance(0, 2000)
        assert result == pytest.approx(-1.0, rel=1e-6)
    
    def test_calculate_orderflow_imbalance_edge_cases(self):
        """Test orderflow imbalance with edge cases."""
        # Zero volume on both sides
        result = ComponentCalculator.calculate_orderflow_imbalance(0, 0)
        assert result == 0.0
        
        # Negative values
        result = ComponentCalculator.calculate_orderflow_imbalance(-1000, 1000)
        assert result == 0.0
        
        result = ComponentCalculator.calculate_orderflow_imbalance(1000, -1000)
        assert result == 0.0
    
    def test_validate_component_inputs(self):
        """Test input validation and sanitization."""
        # Test normal inputs
        metrics = {
            "tx_count_5m": 100,
            "tx_count_1h": 1200,
            "volume_5m": 1000.0,
            "volume_1h": 12000.0,
            "buys_volume_5m": 600.0,
            "sells_volume_5m": 400.0,
            "hours_since_creation": 2.5,
        }
        
        result = ComponentCalculator.validate_component_inputs(metrics)
        
        assert result["tx_count_5m"] == 100.0
        assert result["tx_count_1h"] == 1200.0
        assert result["volume_5m"] == 1000.0
        assert result["volume_1h"] == 12000.0
        assert result["buys_volume_5m"] == 600.0
        assert result["sells_volume_5m"] == 400.0
        assert result["hours_since_creation"] == 2.5
    
    def test_validate_component_inputs_with_missing_data(self):
        """Test input validation with missing or invalid data."""
        # Test with missing fields
        metrics = {
            "tx_count_5m": 100,
            # tx_count_1h missing
            "volume_5m": None,
            "volume_1h": "invalid",
            "buys_volume_5m": float('inf'),
            "sells_volume_5m": float('nan'),
        }
        
        result = ComponentCalculator.validate_component_inputs(metrics)
        
        assert result["tx_count_5m"] == 100.0
        assert result["tx_count_1h"] == 0.0  # default
        assert result["volume_5m"] == 0.0  # None -> default
        assert result["volume_1h"] == 0.0  # invalid string -> default
        assert result["buys_volume_5m"] == 0.0  # inf -> default
        assert result["sells_volume_5m"] == 0.0  # nan -> default
        assert result["hours_since_creation"] == 0.0  # missing -> default
    
    def test_error_handling_with_invalid_types(self):
        """Test error handling with completely invalid input types."""
        # Test with string inputs that can't be converted
        result = ComponentCalculator.calculate_tx_accel("invalid", "also_invalid")
        assert result == 0.0
        
        result = ComponentCalculator.calculate_vol_momentum("invalid", "also_invalid")
        assert result == 0.0
        
        result = ComponentCalculator.calculate_token_freshness("invalid", "also_invalid")
        assert result == 0.0
        
        result = ComponentCalculator.calculate_orderflow_imbalance("invalid", "also_invalid")
        assert result == 0.0
    
    def test_extreme_values_handling(self):
        """Test handling of extreme numerical values."""
        # Test with very large numbers
        # (1e10 / 5) / (1e12 / 60) = 2e9 / (1e12/60) = 2e9 / 1.67e10 = 0.12
        result = ComponentCalculator.calculate_tx_accel(1e10, 1e12)
        assert result == pytest.approx(0.12, rel=1e-6)  # Should still calculate correctly
        
        # Test with very small numbers
        # 1e-10 / (1e-8 / 12) = 1e-10 / (8.33e-10) = 0.12
        result = ComponentCalculator.calculate_vol_momentum(1e-10, 1e-8)
        assert result == pytest.approx(0.12, rel=1e-6)
        
        # Test with infinity
        result = ComponentCalculator.calculate_tx_accel(float('inf'), 1200)
        assert result == 0.0
        
        # Test with NaN
        result = ComponentCalculator.calculate_vol_momentum(float('nan'), 12000)
        assert result == 0.0