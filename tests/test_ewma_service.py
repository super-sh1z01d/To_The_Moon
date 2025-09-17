"""
Unit tests for EWMAService class.

Tests EWMA smoothing functionality with various scenarios including
initialization, smoothing persistence, and error handling.
"""
import math
import pytest
from unittest.mock import Mock, MagicMock

from src.domain.scoring.ewma_service import EWMAService
from src.adapters.db.models import TokenScore


class TestEWMAService:
    """Test suite for EWMAService class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_repository = Mock()
        self.ewma_service = EWMAService(self.mock_repository)
    
    def test_calculate_ewma_initialization(self):
        """Test EWMA calculation with no previous value (initialization)."""
        result = self.ewma_service.calculate_ewma(0.5, None, 0.3)
        assert result == 0.5
        
        result = self.ewma_service.calculate_ewma(1.0, None, 0.7)
        assert result == 1.0
    
    def test_calculate_ewma_smoothing(self):
        """Test EWMA calculation with previous values."""
        # Test with alpha = 0.3
        # EWMA = 0.3 * 0.8 + 0.7 * 0.5 = 0.24 + 0.35 = 0.59
        result = self.ewma_service.calculate_ewma(0.8, 0.5, 0.3)
        assert result == pytest.approx(0.59, rel=1e-6)
        
        # Test with alpha = 0.7 (more responsive)
        # EWMA = 0.7 * 0.8 + 0.3 * 0.5 = 0.56 + 0.15 = 0.71
        result = self.ewma_service.calculate_ewma(0.8, 0.5, 0.7)
        assert result == pytest.approx(0.71, rel=1e-6)
        
        # Test with alpha = 0.0 (no change)
        result = self.ewma_service.calculate_ewma(0.8, 0.5, 0.0)
        assert result == 0.5
        
        # Test with alpha = 1.0 (no smoothing)
        result = self.ewma_service.calculate_ewma(0.8, 0.5, 1.0)
        assert result == 0.8
    
    def test_calculate_ewma_edge_cases(self):
        """Test EWMA calculation with edge cases."""
        # Test with NaN current value (gets converted to 0.0)
        # EWMA = 0.3 * 0.0 + 0.7 * 0.5 = 0.35
        result = self.ewma_service.calculate_ewma(float('nan'), 0.5, 0.3)
        assert result == pytest.approx(0.35, rel=1e-6)
        
        # Test with infinite current value (gets converted to 0.0)
        # EWMA = 0.3 * 0.0 + 0.7 * 0.5 = 0.35
        result = self.ewma_service.calculate_ewma(float('inf'), 0.5, 0.3)
        assert result == pytest.approx(0.35, rel=1e-6)
        
        # Test with NaN previous value (gets converted to 0.0)
        result = self.ewma_service.calculate_ewma(0.8, float('nan'), 0.3)
        assert result == pytest.approx(0.24, rel=1e-6)  # 0.3 * 0.8 + 0.7 * 0.0
        
        # Test with infinite previous value (gets converted to 0.0)
        result = self.ewma_service.calculate_ewma(0.8, float('inf'), 0.3)
        assert result == pytest.approx(0.24, rel=1e-6)  # 0.3 * 0.8 + 0.7 * 0.0
    
    def test_validate_smoothing_parameters(self):
        """Test alpha parameter validation."""
        # Test normal values
        assert self.ewma_service.validate_smoothing_parameters(0.3) == 0.3
        assert self.ewma_service.validate_smoothing_parameters(0.0) == 0.0
        assert self.ewma_service.validate_smoothing_parameters(1.0) == 1.0
        
        # Test clamping
        assert self.ewma_service.validate_smoothing_parameters(-0.5) == 0.0
        assert self.ewma_service.validate_smoothing_parameters(1.5) == 1.0
        
        # Test invalid values
        assert self.ewma_service.validate_smoothing_parameters(None) == 0.3
        assert self.ewma_service.validate_smoothing_parameters("invalid") == 0.3
        assert self.ewma_service.validate_smoothing_parameters(float('nan')) == 0.3
        assert self.ewma_service.validate_smoothing_parameters(float('inf')) == 0.3
    
    def test_get_previous_values_with_history(self):
        """Test getting previous EWMA values when history exists."""
        # Mock a previous score with smoothed components
        mock_score = Mock()
        mock_score.smoothed_components = {
            "tx_accel": 0.5,
            "vol_momentum": 0.8,
            "token_freshness": 0.3,
            "orderflow_imbalance": 0.1,
            "final_score": 0.45
        }
        
        self.mock_repository.get_latest_score.return_value = mock_score
        
        result = self.ewma_service.get_previous_values(123)
        
        assert result == mock_score.smoothed_components
        self.mock_repository.get_latest_score.assert_called_once_with(123)
    
    def test_get_previous_values_no_history(self):
        """Test getting previous EWMA values when no history exists."""
        self.mock_repository.get_latest_score.return_value = None
        
        result = self.ewma_service.get_previous_values(123)
        
        assert result is None
        self.mock_repository.get_latest_score.assert_called_once_with(123)
    
    def test_get_previous_values_no_smoothed_components(self):
        """Test getting previous EWMA values when score exists but no smoothed components."""
        mock_score = Mock()
        mock_score.smoothed_components = None
        
        self.mock_repository.get_latest_score.return_value = mock_score
        
        result = self.ewma_service.get_previous_values(123)
        
        assert result is None
    
    def test_apply_smoothing_initialization(self):
        """Test applying smoothing when no previous values exist."""
        # Mock no previous values
        self.mock_repository.get_latest_score.return_value = None
        
        raw_components = {
            "tx_accel": 1.0,
            "vol_momentum": 0.8,
            "token_freshness": 0.6,
            "orderflow_imbalance": 0.2,
            "final_score": 0.65
        }
        
        result = self.ewma_service.apply_smoothing(123, raw_components, 0.3)
        
        # Should return the same values since no previous values exist
        assert result["tx_accel"] == 1.0
        assert result["vol_momentum"] == 0.8
        assert result["token_freshness"] == 0.6
        assert result["orderflow_imbalance"] == 0.2
        assert result["final_score"] == 0.65
    
    def test_apply_smoothing_with_history(self):
        """Test applying smoothing when previous values exist."""
        # Mock previous values
        mock_score = Mock()
        mock_score.smoothed_components = {
            "tx_accel": 0.5,
            "vol_momentum": 0.6,
            "token_freshness": 0.4,
            "orderflow_imbalance": 0.0,
            "final_score": 0.4
        }
        self.mock_repository.get_latest_score.return_value = mock_score
        
        raw_components = {
            "tx_accel": 1.0,
            "vol_momentum": 0.8,
            "token_freshness": 0.6,
            "orderflow_imbalance": 0.2,
            "final_score": 0.65
        }
        
        result = self.ewma_service.apply_smoothing(123, raw_components, 0.3)
        
        # Check smoothed values: alpha * current + (1-alpha) * previous
        # tx_accel: 0.3 * 1.0 + 0.7 * 0.5 = 0.65
        assert result["tx_accel"] == pytest.approx(0.65, rel=1e-6)
        
        # vol_momentum: 0.3 * 0.8 + 0.7 * 0.6 = 0.66
        assert result["vol_momentum"] == pytest.approx(0.66, rel=1e-6)
        
        # token_freshness: 0.3 * 0.6 + 0.7 * 0.4 = 0.46
        assert result["token_freshness"] == pytest.approx(0.46, rel=1e-6)
        
        # orderflow_imbalance: 0.3 * 0.2 + 0.7 * 0.0 = 0.06
        assert result["orderflow_imbalance"] == pytest.approx(0.06, rel=1e-6)
        
        # final_score: 0.3 * 0.65 + 0.7 * 0.4 = 0.475
        assert result["final_score"] == pytest.approx(0.475, rel=1e-6)
    
    def test_apply_smoothing_missing_components(self):
        """Test applying smoothing when some components are missing."""
        self.mock_repository.get_latest_score.return_value = None
        
        raw_components = {
            "tx_accel": 1.0,
            "vol_momentum": 0.8,
            # token_freshness missing
            # orderflow_imbalance missing
            "final_score": 0.65
        }
        
        result = self.ewma_service.apply_smoothing(123, raw_components, 0.3)
        
        # Should only include components that were present
        assert "tx_accel" in result
        assert "vol_momentum" in result
        assert "final_score" in result
        assert "token_freshness" not in result
        assert "orderflow_imbalance" not in result
    
    def test_apply_smoothing_error_handling(self):
        """Test error handling in apply_smoothing method."""
        # Mock repository to raise an exception
        self.mock_repository.get_latest_score.side_effect = Exception("Database error")
        
        raw_components = {
            "tx_accel": 1.0,
            "vol_momentum": 0.8,
            "final_score": 0.65
        }
        
        # Should return raw components as fallback
        result = self.ewma_service.apply_smoothing(123, raw_components, 0.3)
        
        assert result == raw_components
    
    def test_get_smoothing_statistics_no_history(self):
        """Test getting smoothing statistics when no history exists."""
        self.mock_repository.get_score_history.return_value = []
        
        result = self.ewma_service.get_smoothing_statistics(123, "tx_accel")
        
        assert "error" in result
        assert "No score history available" in result["error"]
    
    def test_get_smoothing_statistics_with_data(self):
        """Test getting smoothing statistics with valid data."""
        # Mock score history
        mock_scores = []
        for i in range(5):
            score = Mock()
            score.metrics = {"tx_accel": 0.5 + i * 0.1}
            score.smoothed_components = {"tx_accel": 0.45 + i * 0.05}
            mock_scores.append(score)
        
        self.mock_repository.get_score_history.return_value = mock_scores
        
        result = self.ewma_service.get_smoothing_statistics(123, "tx_accel", window_size=5)
        
        assert result["component"] == "tx_accel"
        assert result["window_size"] == 5
        assert "raw_mean" in result
        assert "smoothed_mean" in result
        assert "raw_variance" in result
        assert "smoothed_variance" in result
        assert "variance_reduction" in result
        assert "latest_raw" in result
        assert "latest_smoothed" in result
    
    def test_alpha_clamping_in_apply_smoothing(self):
        """Test that alpha parameter is properly clamped in apply_smoothing."""
        self.mock_repository.get_latest_score.return_value = None
        
        raw_components = {"final_score": 0.5}
        
        # Test with alpha > 1.0
        result = self.ewma_service.apply_smoothing(123, raw_components, 1.5)
        assert result["final_score"] == 0.5  # Should work with clamped alpha
        
        # Test with alpha < 0.0
        result = self.ewma_service.apply_smoothing(123, raw_components, -0.5)
        assert result["final_score"] == 0.5  # Should work with clamped alpha
    
    def test_precision_rounding(self):
        """Test that EWMA values are properly rounded to avoid precision issues."""
        result = self.ewma_service.calculate_ewma(1.0/3.0, 2.0/3.0, 0.5)
        
        # Should be rounded to 6 decimal places
        assert isinstance(result, float)
        assert len(str(result).split('.')[-1]) <= 6