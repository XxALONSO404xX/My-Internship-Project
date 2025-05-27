"""
Shared utilities for simulating realistic network behavior
"""
import logging
import random
import asyncio
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

async def simulate_network_delay(action_type="scanning", base_seconds=8, scale_factor=None):
    """
    Simulate realistic network delays for various operations
    
    Args:
        action_type: Type of action for logging (scanning, connecting, etc.)
        base_seconds: Base delay in seconds
        scale_factor: Optional scaling factor (0-1) to adjust delay
        
    Returns:
        Actual delay used in seconds
    """
    # Calculate delay with some randomness
    variation = random.uniform(-0.5, 1.5)
    
    # Apply scaling if provided
    if scale_factor is not None:
        delay = base_seconds + (base_seconds * scale_factor) + variation
    else:
        delay = base_seconds + variation
    
    logger.info(f"{action_type.capitalize()}, estimated time: {delay:.1f} seconds")
    await asyncio.sleep(delay)
    return delay

def calculate_risk_score(vulnerabilities):
    """
    Calculate risk score based on vulnerabilities
    
    Args:
        vulnerabilities: List of vulnerability dictionaries with severity
        
    Returns:
        Risk score between 1-10
    """
    if not vulnerabilities:
        return 0.0
        
    severity_weights = {
        "CRITICAL": 10.0,
        "HIGH": 7.5,
        "MEDIUM": 5.0,
        "LOW": 2.5,
        "INFO": 0.5
    }
    
    total_score = sum(severity_weights.get(v.get("severity", "MEDIUM"), 5.0) for v in vulnerabilities)
    # Normalize to 1-10 scale
    return min(10.0, max(1.0, total_score / max(1, len(vulnerabilities))))

def simulate_failures(failure_rate=0.08):
    """
    Simulate random failures at a specified rate
    
    Args:
        failure_rate: Probability of failure (0-1)
        
    Returns:
        True if failure should occur, False otherwise
    """
    return random.random() < failure_rate 