"""
Risk scoring utilities for vulnerability management.
Provides advanced risk calculation and prioritization algorithms.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import math
import logging

logger = logging.getLogger(__name__)

class RiskScorer:
    """
    Calculates risk scores for vulnerabilities based on multiple factors:
    - Base CVSS score
    - Asset criticality
    - Exploitability
    - Time since discovery
    - Network exposure
    - Remediation complexity
    """
    
    # Device type criticality weightings (scale 1-10)
    DEVICE_CRITICALITY = {
        "security_camera": 9,
        "smart_lock": 10,
        "thermostat": 7,
        "light_bulb": 3,
        "smart_plug": 4,
        "temperature_sensor": 5,
        "motion_sensor": 6,
        "air_purifier": 6,
        "air_quality": 6,
        "humidity_sensor": 5,
        "water_leak_sensor": 8,
        "gateway": 10,
        "hub": 9,
        "default": 5  # Default for unknown device types
    }
    
    # Weights for different risk factors (must sum to 1.0)
    RISK_WEIGHTS = {
        "cvss": 0.35,
        "criticality": 0.25,
        "exploitability": 0.20,
        "exposure": 0.10,
        "age": 0.10
    }
    
    def __init__(self):
        # Validate weights
        if abs(sum(self.RISK_WEIGHTS.values()) - 1.0) > 0.001:
            logger.warning(f"Risk weights do not sum to 1.0: {sum(self.RISK_WEIGHTS.values())}")
    
    def get_device_criticality(self, device_type: str) -> float:
        """Get the criticality score for a device type (1-10 scale)"""
        return self.DEVICE_CRITICALITY.get(device_type.lower(), self.DEVICE_CRITICALITY["default"])
    
    def calculate_device_risk_score(self, device: Any, vulnerabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate an overall risk score for a device based on its vulnerabilities
        Returns a dictionary with the overall score and component scores
        """
        if not vulnerabilities:
            return {
                "total_score": 0.0,
                "risk_level": "none",
                "component_scores": {},
                "vulnerability_scores": []
            }
        
        # Calculate individual vulnerability scores
        vuln_scores = []
        for vuln in vulnerabilities:
            vuln_score = self.calculate_vulnerability_risk_score(device, vuln)
            vuln_scores.append({
                "vulnerability_id": vuln.get("id"),
                "name": vuln.get("name"),
                "score": vuln_score,
                "normalized_score": self._normalize_score(vuln_score)
            })
        
        # Sort by score (descending)
        vuln_scores.sort(key=lambda x: x["score"], reverse=True)
        
        # Calculate total risk score (weighted average of top 3 risks + diminishing factor for others)
        total_score = 0
        component_scores = {}
        
        if vuln_scores:
            # Calculate device criticality factor
            device_type = getattr(device, "device_type", "default")
            criticality = self.get_device_criticality(device_type) / 10.0  # Normalize to 0-1
            
            # Network exposure factor
            exposure = self._calculate_exposure_factor(device)
            
            # Top vulnerability has full impact
            top_score = vuln_scores[0]["score"]
            
            # Additional vulnerabilities have diminishing impact (80% of previous)
            diminishing_factor = 0.8
            effective_count = 1.0
            
            for i, vs in enumerate(vuln_scores):
                if i == 0:
                    weight = 1.0
                else:
                    weight = diminishing_factor ** (i)
                effective_count += weight
                total_score += vs["score"] * weight
            
            # Average the scores with diminishing returns
            avg_score = total_score / effective_count
            
            # Apply criticality and exposure modifiers
            final_score = avg_score * (0.7 + (criticality * 0.3)) * (0.8 + (exposure * 0.2))
            
            # Cap at 10
            final_score = min(10.0, final_score)
            
            # Record component scores for transparency
            component_scores = {
                "base_score": avg_score,
                "criticality_factor": criticality,
                "exposure_factor": exposure,
                "vulnerability_count": len(vulnerabilities),
                "effective_vulnerability_count": effective_count
            }
            
            return {
                "total_score": round(final_score, 1),
                "risk_level": self._risk_level_from_score(final_score),
                "component_scores": component_scores,
                "vulnerability_scores": vuln_scores
            }
        else:
            return {
                "total_score": 0.0,
                "risk_level": "none",
                "component_scores": {},
                "vulnerability_scores": []
            }
    
    def calculate_vulnerability_risk_score(self, device: Any, vulnerability: Dict[str, Any]) -> float:
        """
        Calculate risk score for a specific vulnerability on a specific device
        Returns a score from 0-10
        """
        # Get base CVSS score (0-10)
        cvss = vulnerability.get("cvss_score", 5.0)
        
        # Get device criticality (0-1)
        device_type = getattr(device, "device_type", "default")
        criticality = self.get_device_criticality(device_type) / 10.0
        
        # Get exploitability (0-1)
        exploitability = self._get_exploitability_factor(vulnerability)
        
        # Network exposure (0-1)
        exposure = self._calculate_exposure_factor(device)
        
        # Age factor - vulnerabilities get more risky over time if not addressed (0-1)
        age_factor = self._calculate_age_factor(vulnerability)
        
        # Calculate weighted score
        score = (
            cvss * self.RISK_WEIGHTS["cvss"] +
            (criticality * 10) * self.RISK_WEIGHTS["criticality"] +
            (exploitability * 10) * self.RISK_WEIGHTS["exploitability"] +
            (exposure * 10) * self.RISK_WEIGHTS["exposure"] +
            (age_factor * 10) * self.RISK_WEIGHTS["age"]
        )
        
        # Modifiers for partial fixes, temporary fixes, or remediation attempts
        if vulnerability.get("partial_fix"):
            score *= 0.7  # 30% reduction for partially fixed vulnerabilities
        
        if vulnerability.get("temporarily_fixed"):
            # Check if the fix is about to expire
            if "fix_expiration" in vulnerability:
                try:
                    expiry = datetime.fromisoformat(vulnerability["fix_expiration"])
                    now = datetime.utcnow()
                    days_to_expiry = (expiry - now).days
                    
                    if days_to_expiry < 0:
                        # Fix has expired, treat as regular vulnerability
                        pass
                    elif days_to_expiry < 7:
                        # About to expire, only 10% reduction
                        score *= 0.9
                    elif days_to_expiry < 30:
                        # Will expire soon, 30% reduction
                        score *= 0.7
                    else:
                        # Won't expire for a while, 50% reduction
                        score *= 0.5
                except:
                    # If we can't parse the date, assume 30% reduction
                    score *= 0.7
            else:
                # No expiry info, assume 30% reduction
                score *= 0.7
        
        if vulnerability.get("remediation_attempted") and vulnerability.get("remediation_failed"):
            # Failed remediation attempt might indicate the vulnerability is harder to fix
            # or more entrenched, slightly increase the risk
            score *= 1.1
        
        return min(10.0, score)  # Cap at 10
    
    def _get_exploitability_factor(self, vulnerability: Dict[str, Any]) -> float:
        """Convert exploitability string to numerical factor (0-1)"""
        exploitability = vulnerability.get("exploitability", "MEDIUM").upper()
        
        if exploitability == "CRITICAL" or exploitability == "VERY_HIGH":
            return 1.0
        elif exploitability == "HIGH":
            return 0.8
        elif exploitability == "MEDIUM":
            return 0.5
        elif exploitability == "LOW":
            return 0.3
        else:
            return 0.5  # Default to medium
    
    def _calculate_exposure_factor(self, device: Any) -> float:
        """Calculate network exposure factor based on device properties (0-1)"""
        exposure = 0.5  # Default to medium exposure
        
        # Increase exposure for internet-connected devices
        if getattr(device, "supports_http", False):
            exposure += 0.2
        
        # Increase for devices with common vulnerable protocols
        if hasattr(device, "ports"):
            ports = device.ports or {}
            if isinstance(ports, dict):
                vulnerable_protocols = {"telnet": 0.2, "ftp": 0.15, "snmp": 0.1, "mqtt": 0.05}
                for protocol in vulnerable_protocols:
                    if protocol in ports:
                        exposure += vulnerable_protocols[protocol]
        
        # Decrease for devices with TLS
        if getattr(device, "supports_tls", False):
            exposure -= 0.2
            
            # But consider TLS version
            if hasattr(device, "tls_version"):
                if device.tls_version in ["TLS 1.0", "TLS 1.1"]:
                    # Older TLS is less secure, so less reduction
                    exposure += 0.1
        
        return max(0.0, min(1.0, exposure))  # Clamp between 0-1
    
    def _calculate_age_factor(self, vulnerability: Dict[str, Any]) -> float:
        """
        Calculate age factor - vulnerabilities get more risky over time if not addressed (0-1)
        """
        # Default age factor (medium)
        age_factor = 0.5
        
        # If we have a discovery date
        if "discovery_date" in vulnerability:
            try:
                discovery_date = datetime.fromisoformat(vulnerability["discovery_date"])
                now = datetime.utcnow()
                days_since_discovery = (now - discovery_date).days
                
                # Log function to model increasing risk over time
                # Newer vulnerabilities start low, then risk increases more rapidly,
                # then levels off for very old vulnerabilities
                if days_since_discovery <= 0:
                    age_factor = 0.3  # Just discovered
                elif days_since_discovery < 30:
                    # First month, increasing risk
                    age_factor = 0.3 + (0.4 * (days_since_discovery / 30))
                elif days_since_discovery < 180:
                    # 1-6 months, higher risk
                    age_factor = 0.7 + (0.2 * ((days_since_discovery - 30) / 150))
                else:
                    # >6 months, maximum risk factor
                    age_factor = 0.9
            except:
                # If we can't parse the date, use default
                pass
        
        return age_factor
    
    def _normalize_score(self, score: float) -> int:
        """Normalize score to 0-100 integer range for easier consumption by frontend"""
        return min(100, max(0, int(score * 10)))
    
    def _risk_level_from_score(self, score: float) -> str:
        """Convert numerical score to risk level category"""
        if score >= 8.0:
            return "critical"
        elif score >= 6.0:
            return "high"
        elif score >= 4.0:
            return "medium"
        elif score > 0:
            return "low"
        else:
            return "none"
    
    def prioritize_vulnerabilities(self, device: Any, vulnerabilities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create a prioritized list of vulnerabilities for remediation
        Adds risk scores, priority levels, and sorts by priority
        """
        if not vulnerabilities:
            return []
        
        # Calculate risk scores for each vulnerability
        scored_vulnerabilities = []
        for vuln in vulnerabilities:
            score = self.calculate_vulnerability_risk_score(device, vuln)
            
            # Copy the vulnerability and add scoring data
            scored_vuln = vuln.copy()
            scored_vuln["risk_score"] = round(score, 1)
            scored_vuln["normalized_risk"] = self._normalize_score(score)
            scored_vuln["risk_level"] = self._risk_level_from_score(score)
            
            # Add a recommended timeframe for remediation
            if score >= 8.0:
                scored_vuln["remediation_timeframe"] = "immediate"
            elif score >= 6.0:
                scored_vuln["remediation_timeframe"] = "within_week"
            elif score >= 4.0:
                scored_vuln["remediation_timeframe"] = "within_month"
            else:
                scored_vuln["remediation_timeframe"] = "next_cycle"
            
            scored_vulnerabilities.append(scored_vuln)
        
        # Sort by risk score (highest first)
        scored_vulnerabilities.sort(key=lambda x: x["risk_score"], reverse=True)
        
        return scored_vulnerabilities

# Create singleton instance
risk_scorer = RiskScorer()
