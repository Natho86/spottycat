"""
spottycat.core.cost_calculator - Cost tracking and budget enforcement

This module implements cost tracking and budget management functionality
using AWS Pricing API for real-time cost calculations.
"""


class CostCalculator:
    """
    Cost calculator class using AWS Pricing API for real-time spot pricing.
    """
    
    def __init__(self, aws_client):
        """
        Initialize cost calculator.
        
        Args:
            aws_client: AWSClient instance
        """
        self.aws_client = aws_client
    
    # Placeholder for cost calculation implementation
    # Will be implemented in task 5.1 