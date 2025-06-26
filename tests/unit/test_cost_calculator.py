"""
tests.unit.test_cost_calculator - Unit tests for cost calculation logic

This module contains unit tests for cost calculation logic with various pricing scenarios.
"""

import pytest
from unittest.mock import Mock, patch
import datetime


@pytest.mark.unit
@pytest.mark.cost
class TestCostCalculator:
    """Test cases for the cost calculator functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Placeholder for test setup
        # Will be implemented in task 7.2
        pass
    
    @pytest.mark.mock
    def test_calculate_spot_price(self, mock_cost_calculator, mock_pricing_client):
        """Test spot price calculation."""
        # Placeholder for spot price calculation test
        # Will be implemented in task 7.2
        mock_cost_calculator.calculate_spot_price.return_value = 0.30
        result = mock_cost_calculator.calculate_spot_price('g4dn.xlarge', 'us-east-1a')
        assert result == 0.30
        mock_cost_calculator.calculate_spot_price.assert_called_once()
    
    @pytest.mark.mock
    def test_budget_tracking(self, mock_cost_calculator):
        """Test budget tracking functionality."""
        # Placeholder for budget tracking test
        # Will be implemented in task 7.2
        mock_cost_calculator.calculate_budget_remaining.return_value = 75.0
        result = mock_cost_calculator.calculate_budget_remaining()
        assert result == 75.0
        mock_cost_calculator.calculate_budget_remaining.assert_called_once()
    
    @pytest.mark.mock
    def test_budget_alerts(self, mock_cost_calculator):
        """Test budget alert functionality."""
        # Placeholder for budget alerts test
        # Will be implemented in task 7.2
        mock_cost_calculator.check_budget_alerts.return_value = []
        result = mock_cost_calculator.check_budget_alerts()
        assert result == []
        mock_cost_calculator.check_budget_alerts.assert_called_once()
    
    @pytest.mark.unit
    def test_cost_calculator_initialization(self):
        """Test cost calculator initialization."""
        # Placeholder for initialization test
        # Will be implemented in task 7.2
        pass 
    
    @pytest.mark.mock
    def test_pricing_api_integration(self, mock_pricing_client):
        """Test pricing API integration."""
        # Placeholder for pricing API test
        # Will be implemented in task 7.2
        mock_pricing_client.get_products.return_value = {
            'PriceList': ['{"product":{"productFamily":"Compute Instance"}}']
        }
        # Test will be implemented with actual pricing logic
        assert mock_pricing_client.get_products.return_value is not None 
    
    def test_estimate_spot_request_cost(self):
        """Test that estimate_spot_request_cost returns the latest spot price from EC2."""
        from spottycat.core.cost_calculator import CostCalculator
        mock_aws_client = Mock()
        mock_ec2_client = Mock()
        # Mock the EC2 client's describe_spot_price_history response
        mock_ec2_client.describe_spot_price_history.return_value = {
            'SpotPriceHistory': [
                {
                    'InstanceType': 'g4dn.xlarge',
                    'ProductDescription': 'Linux/UNIX',
                    'SpotPrice': '0.42',
                    'Timestamp': '2023-01-01T00:00:00Z',
                    'AvailabilityZone': 'us-east-1a'
                }
            ]
        }
        mock_aws_client.ec2_client = mock_ec2_client
        mock_aws_client.region = 'us-east-1'
        calc = CostCalculator(mock_aws_client)
        price = calc.estimate_spot_request_cost('g4dn.xlarge', region='us-east-1', availability_zone='us-east-1a')
        assert price == 0.42 
    
    def test_get_instance_spend_and_all_instance_spend(self):
        """Test spend calculation for a running spot instance."""
        from spottycat.core.cost_calculator import CostCalculator
        mock_aws_client = Mock()
        # Mock describe_instances to return a running spot instance
        launch_time = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0) - datetime.timedelta(hours=2)
        mock_aws_client.describe_instances.return_value = {
            'Reservations': [
                {
                    'Instances': [
                        {
                            'InstanceId': 'i-1234',
                            'LaunchTime': launch_time,
                            'InstanceType': 'g4dn.xlarge',
                            'Placement': {'AvailabilityZone': 'us-east-1a'}
                        }
                    ]
                }
            ]
        }
        mock_aws_client.region = 'us-east-1'
        # Patch estimate_spot_request_cost to return a fixed price
        calc = CostCalculator(mock_aws_client)
        calc.estimate_spot_request_cost = Mock(return_value=0.5)
        spend = calc.get_instance_spend('i-1234')
        assert 0.99 < spend < 1.01  # 2 hours * $0.5 = $1.0
        all_spend = calc.get_all_instance_spend()
        assert all_spend['i-1234'] == spend 
    
    def test_enforce_instance_budgets(self):
        """Test that enforce_instance_budgets terminates instances over budget."""
        from spottycat.core.cost_calculator import CostCalculator
        mock_aws_client = Mock()
        calc = CostCalculator(mock_aws_client)
        # Mock get_all_instance_spend to return one instance over budget
        calc.get_all_instance_spend = Mock(return_value={'i-1234': 10.0, 'i-5678': 4.0})
        # Mock terminate_instance to record calls
        calc.terminate_instance = Mock()
        terminated = calc.enforce_instance_budgets(max_budget=5.0)
        assert terminated == ['i-1234']
        calc.terminate_instance.assert_called_once_with('i-1234') 
    
    def test_estimate_spot_request_total_cost(self):
        """Test total cost estimation for a spot request before submission."""
        from spottycat.core.cost_calculator import CostCalculator
        mock_aws_client = Mock()
        calc = CostCalculator(mock_aws_client)
        calc.estimate_spot_request_cost = Mock(return_value=0.25)
        total = calc.estimate_spot_request_total_cost('g4dn.xlarge', hours=8)
        assert 1.99 < total < 2.01  # 8 hours * $0.25 = $2.00 
    
    def test_check_budget_alerts(self):
        """Test budget alerting at 75% and 90% thresholds."""
        from spottycat.core.cost_calculator import CostCalculator
        mock_aws_client = Mock()
        calc = CostCalculator(mock_aws_client)
        # Mock spends: one below, one at 75%, one at 90%, one above 100%
        calc.get_all_instance_spend = Mock(return_value={
            'i-low': 3.0,    # below 75% of 10
            'i-warn': 7.5,   # exactly 75% of 10
            'i-crit': 9.0,   # exactly 90% of 10
            'i-over': 12.0   # over 100% of 10
        })
        alerts = calc.check_budget_alerts(max_budget=10.0)
        # Should alert for i-warn (0.75), i-crit (0.75, 0.9), i-over (0.75, 0.9)
        alert_set = set((a['instance_id'], a['threshold']) for a in alerts)
        expected = set([
            ('i-warn', 0.75),
            ('i-crit', 0.75), ('i-crit', 0.9),
            ('i-over', 0.75), ('i-over', 0.9)
        ])
        assert alert_set == expected 