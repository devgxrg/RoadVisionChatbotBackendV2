"""
Advanced Intelligence Services (Phase 4).

High-level strategic analysis services:
- SWOT Analyzer
- Bid Decision Recommender
- Risk Assessment Engine (enhanced)
- Compliance Checker
- Cost Breakdown Generator
- Win Probability Calculator
"""

import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from uuid import UUID
import time

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("Google Generative AI not available")

logger = logging.getLogger(__name__)


# ===== SWOT Analyzer =====

class SWOTAnalyzer:
    """Analyzes SWOT (Strengths, Weaknesses, Opportunities, Threats) for tender bidding"""

    def __init__(self):
        self.gemini_model = None
        if GEMINI_AVAILABLE:
            import os
            api_key = os.getenv("GOOGLE_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                self.gemini_model = genai.GenerativeModel("gemini-pro")

    async def analyze_swot(
        self,
        tender_info: Dict[str, Any],
        scope_data: Dict[str, Any],
        financials: Dict[str, Any],
        use_llm: bool = True,
    ) -> Dict[str, Any]:
        """
        Analyze SWOT factors for tender bidding.

        Args:
            tender_info: Extracted tender information
            scope_data: Scope of work analysis
            financials: Financial requirements data
            use_llm: Use LLM-based analysis

        Returns:
            Dictionary with SWOT analysis
        """
        logger.info("Starting SWOT analysis")

        if use_llm and self.gemini_model:
            return await self._analyze_with_llm(tender_info, scope_data, financials)
        else:
            return await self._analyze_with_keywords(tender_info, scope_data, financials)

    async def _analyze_with_llm(
        self,
        tender_info: Dict[str, Any],
        scope_data: Dict[str, Any],
        financials: Dict[str, Any],
    ) -> Dict[str, Any]:
        """LLM-based SWOT analysis"""
        prompt = f"""Analyze SWOT factors for bidding on this tender:

Tender: {tender_info.get('title', 'N/A')}
Category: {tender_info.get('category', 'N/A')}
Contract Value: {tender_info.get('estimatedValue', {}).get('displayText', 'N/A')}
Scope: {scope_data.get('total_effort_days', 0)} days of work
Financial Requirements: EMD ₹{financials.get('emdAmount', {}).get('amount', 0)}L

Provide SWOT analysis in this JSON format:
{{
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "weaknesses": ["weakness 1", "weakness 2"],
  "opportunities": ["opportunity 1", "opportunity 2"],
  "threats": ["threat 1", "threat 2"]
}}

Consider company capabilities, market conditions, and project complexity."""

        try:
            response = self.gemini_model.generate_content(prompt)
            response_text = response.text.strip()

            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            response_text = response_text.strip()

            data = json.loads(response_text)
            return {
                "strengths": data.get("strengths", []),
                "weaknesses": data.get("weaknesses", []),
                "opportunities": data.get("opportunities", []),
                "threats": data.get("threats", []),
                "confidence": 85.0,
            }

        except Exception as e:
            logger.warning(f"LLM SWOT analysis failed: {e}")
            return await self._analyze_with_keywords(tender_info, scope_data, financials)

    async def _analyze_with_keywords(
        self,
        tender_info: Dict[str, Any],
        scope_data: Dict[str, Any],
        financials: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Keyword-based SWOT analysis"""
        total_effort = scope_data.get("total_effort_days", 0)
        contract_value = tender_info.get("estimatedValue", {}).get("amount", 0)

        # Determine effort level
        effort_level = "High" if total_effort > 100 else "Moderate" if total_effort > 50 else "Low"

        return {
            "strengths": [
                "Detailed tender documentation available",
                "Clear requirements and specifications",
                "Defined timeline and milestones",
                "Standard evaluation criteria",
            ],
            "weaknesses": [
                f"{effort_level} effort requirement ({total_effort} days)",
                f"Complex scope requiring multiple disciplines",
                "Tight submission deadlines",
                "Stringent compliance requirements",
            ],
            "opportunities": [
                "Market demand for project type",
                "Potential for long-term client relationship",
                "Knowledge building in this sector",
                "Resource utilization opportunity",
            ],
            "threats": [
                "Competitive bidding environment",
                "Possible scope creep",
                "Market price pressure",
                "Resource availability constraints",
            ],
            "confidence": 60.0,
        }


# ===== Bid Decision Recommender =====

class BidDecisionRecommender:
    """Recommends whether to bid and strategy"""

    async def recommend_bid_decision(
        self,
        tender_info: Dict[str, Any],
        scope_data: Dict[str, Any],
        financials: Dict[str, Any],
        risk_level: str,
        swot: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Recommend bid/no-bid decision.

        Args:
            tender_info: Tender information
            scope_data: Scope analysis
            financials: Financial data
            risk_level: Risk assessment level
            swot: SWOT analysis

        Returns:
            Recommendation with rationale
        """
        logger.info("Generating bid recommendation")

        # Calculate recommendation score (0-100)
        score = 50

        # Adjust for scope
        total_effort = scope_data.get("total_effort_days", 0)
        if 50 < total_effort < 150:
            score += 15  # Sweet spot
        elif total_effort < 50:
            score += 10  # Small projects easier to execute
        elif total_effort > 200:
            score -= 15  # Large projects higher risk

        # Adjust for financials
        contract_value = tender_info.get("estimatedValue", {}).get("amount", 0)
        emd_amount = financials.get("emdAmount", {}).get("amount", 0)

        if contract_value > 0 and emd_amount > 0:
            emd_ratio = (emd_amount / contract_value) * 100
            if emd_ratio < 3:
                score += 10  # Reasonable EMD
            elif emd_ratio > 5:
                score -= 10  # High EMD risk

        # Adjust for risk
        if risk_level == "low":
            score += 15
        elif risk_level == "high":
            score -= 20

        # Adjust for SWOT
        if len(swot.get("strengths", [])) > len(swot.get("weaknesses", [])):
            score += 10
        if len(swot.get("threats", [])) > len(swot.get("opportunities", [])):
            score -= 10

        # Determine recommendation
        if score >= 70:
            recommendation = "STRONG BID"
            rationale = "High confidence in successful bid. Align resources and proceed."
        elif score >= 55:
            recommendation = "CONDITIONAL BID"
            rationale = "Moderate confidence. Address weaknesses before bidding."
        elif score >= 40:
            recommendation = "CAUTION"
            rationale = "Consider strategic value. High risk-reward ratio."
        else:
            recommendation = "NO BID"
            rationale = "Low confidence in success. Focus on better opportunities."

        effort_level = "High" if total_effort > 100 else "Medium" if total_effort > 50 else "Low"

        return {
            "recommendation": recommendation,
            "score": min(100, max(0, score)),
            "rationale": rationale,
            "key_factors": {
                "scope_complexity": effort_level,
                "financial_burden": f"EMD: ₹{emd_amount}L",
                "risk_profile": risk_level.upper(),
                "strategic_fit": "Good" if len(swot.get("opportunities", [])) > 0 else "Limited",
            },
        }


# ===== Enhanced Risk Assessment Engine =====

class EnhancedRiskEngine:
    """Enhanced risk assessment engine for Phase 4"""

    async def assess_risks(
        self,
        tender_info: Dict[str, Any],
        scope_data: Dict[str, Any],
        financials: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Comprehensive risk assessment.

        Args:
            tender_info: Tender information
            scope_data: Scope data
            financials: Financial data

        Returns:
            Detailed risk assessment
        """
        logger.info("Performing enhanced risk assessment")

        risks = []
        risk_score = 0

        # Scope risks
        total_effort = scope_data.get("total_effort_days", 0)
        if total_effort > 150:
            risks.append({
                "category": "Scope",
                "severity": "HIGH",
                "factor": "Complex/Large Project",
                "impact": "Resource constraints, schedule pressure",
                "likelihood": 0.7,
            })
            risk_score += 30
        elif total_effort > 100:
            risks.append({
                "category": "Scope",
                "severity": "MEDIUM",
                "factor": "Moderate Complexity",
                "impact": "Coordination challenges",
                "likelihood": 0.5,
            })
            risk_score += 15

        # Financial risks
        contract_value = tender_info.get("estimatedValue", {}).get("amount", 0)
        emd_amount = financials.get("emdAmount", {}).get("amount", 0)

        if emd_amount > contract_value * 0.03:
            risks.append({
                "category": "Financial",
                "severity": "MEDIUM",
                "factor": "High EMD Requirement",
                "impact": "Capital tie-up, cash flow impact",
                "likelihood": 0.6,
            })
            risk_score += 10

        # Compliance risks
        risks.append({
            "category": "Compliance",
            "severity": "MEDIUM",
            "factor": "Regulatory Requirements",
            "impact": "Delays, additional costs",
            "likelihood": 0.4,
        })
        risk_score += 5

        # Market risks
        risks.append({
            "category": "Market",
            "severity": "LOW",
            "factor": "Competition",
            "impact": "Price pressure, bid rejection",
            "likelihood": 0.3,
        })
        risk_score += 3

        # Normalize risk score (0-100)
        overall_risk_score = min(100, risk_score)

        if overall_risk_score < 30:
            risk_level = "LOW"
        elif overall_risk_score < 60:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        return {
            "overall_score": overall_risk_score,
            "risk_level": risk_level,
            "individual_risks": risks,
            "mitigation_strategies": self._generate_mitigations(risks),
            "confidence": 75.0,
        }

    def _generate_mitigations(self, risks: List[Dict[str, Any]]) -> List[str]:
        """Generate mitigation strategies"""
        mitigations = []

        for risk in risks:
            if risk["category"] == "Scope":
                mitigations.append("Establish clear scope boundaries and change control process")
                mitigations.append("Plan for resource scaling based on project phases")

            elif risk["category"] == "Financial":
                mitigations.append("Negotiate payment milestones tied to deliverables")
                mitigations.append("Establish financial reserves for contingencies")

            elif risk["category"] == "Compliance":
                mitigations.append("Create dedicated compliance team")
                mitigations.append("Conduct early compliance audits")

            elif risk["category"] == "Market":
                mitigations.append("Develop competitive pricing strategy")
                mitigations.append("Differentiate through superior service delivery")

        return list(set(mitigations))


# ===== Compliance Checker =====

class ComplianceChecker:
    """Checks compliance requirements and readiness"""

    async def check_compliance(
        self,
        tender_info: Dict[str, Any],
        company_capabilities: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Check compliance requirements.

        Args:
            tender_info: Tender information
            company_capabilities: Company's capabilities

        Returns:
            Compliance check results
        """
        logger.info("Checking compliance requirements")

        compliance_items = []
        met_items = 0

        # Check financial requirements
        compliance_items.append({
            "requirement": "Financial Stability",
            "criteria": "Min Turnover ₹25 Cr",
            "status": "MET" if company_capabilities.get("turnover", 0) >= 2500 else "NOT MET",
            "notes": f"Company Turnover: ₹{company_capabilities.get('turnover', 0)} L",
        })
        if company_capabilities.get("turnover", 0) >= 2500:
            met_items += 1

        # Check experience requirements
        compliance_items.append({
            "requirement": "Experience",
            "criteria": "7+ years in category",
            "status": "MET" if company_capabilities.get("years_experience", 0) >= 7 else "NOT MET",
            "notes": f"Experience: {company_capabilities.get('years_experience', 0)} years",
        })
        if company_capabilities.get("years_experience", 0) >= 7:
            met_items += 1

        # Check similar projects
        compliance_items.append({
            "requirement": "Similar Projects",
            "criteria": "2+ projects ≥ ₹10 Cr",
            "status": "MET" if company_capabilities.get("similar_projects", 0) >= 2 else "NOT MET",
            "notes": f"Similar Projects: {company_capabilities.get('similar_projects', 0)}",
        })
        if company_capabilities.get("similar_projects", 0) >= 2:
            met_items += 1

        # Check certifications
        compliance_items.append({
            "requirement": "Certifications",
            "criteria": "ISO/Quality standards",
            "status": "MET" if company_capabilities.get("certifications", []) else "NOT MET",
            "notes": f"Certifications: {', '.join(company_capabilities.get('certifications', []))}",
        })
        if company_capabilities.get("certifications", []):
            met_items += 1

        compliance_score = (met_items / len(compliance_items)) * 100

        return {
            "overall_compliance": "COMPLIANT" if compliance_score >= 75 else "PARTIALLY COMPLIANT" if compliance_score >= 50 else "NON-COMPLIANT",
            "compliance_score": compliance_score,
            "items": compliance_items,
            "gaps": [
                item["requirement"]
                for item in compliance_items
                if item["status"] == "NOT MET"
            ],
            "recommendations": self._compliance_recommendations(compliance_items),
        }

    def _compliance_recommendations(self, items: List[Dict[str, Any]]) -> List[str]:
        """Generate compliance recommendations"""
        recommendations = []

        for item in items:
            if item["status"] == "NOT MET":
                if "Financial" in item["requirement"]:
                    recommendations.append(
                        "Partner with financially stronger company or investor"
                    )
                elif "Experience" in item["requirement"]:
                    recommendations.append(
                        "Partner with experienced company or build experience"
                    )
                elif "Similar" in item["requirement"]:
                    recommendations.append(
                        "Showcase relevant projects from team members"
                    )
                elif "Certification" in item["requirement"]:
                    recommendations.append("Obtain required certifications before bidding")

        return recommendations


# ===== Cost Breakdown Generator =====

class CostBreakdownGenerator:
    """Generates detailed cost breakdown for bidding"""

    async def generate_cost_breakdown(
        self,
        scope_data: Dict[str, Any],
        financials: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate cost breakdown.

        Args:
            scope_data: Scope of work data
            financials: Financial requirements

        Returns:
            Detailed cost breakdown
        """
        logger.info("Generating cost breakdown")

        contract_value = financials.get("contractValue", {}).get("amount", 0)
        total_effort = scope_data.get("total_effort_days", 0)

        # Allocate costs across work items
        work_items = scope_data.get("work_items", [])
        cost_breakdown = []

        if work_items and contract_value > 0:
            for item in work_items[:3]:  # Top 3 items
                item_effort = item.get("estimatedDays", 10)
                effort_ratio = item_effort / max(1, total_effort)
                item_cost = contract_value * effort_ratio

                cost_breakdown.append({
                    "work_item": item.get("title", "Work Item"),
                    "effort_days": item_effort,
                    "estimated_cost": round(item_cost, 2),
                    "cost_percentage": round(effort_ratio * 100, 1),
                })

        # Add contingency and overhead
        contingency = contract_value * 0.10  # 10% contingency
        overhead = contract_value * 0.05  # 5% overhead

        return {
            "line_items": cost_breakdown,
            "subtotal": round(contract_value, 2),
            "contingency": round(contingency, 2),
            "contingency_percentage": 10.0,
            "overhead": round(overhead, 2),
            "overhead_percentage": 5.0,
            "total_estimate": round(contract_value + contingency + overhead, 2),
            "margin": round((contingency + overhead) / contract_value * 100, 2) if contract_value > 0 else 0,
        }


# ===== Win Probability Calculator =====

class WinProbabilityCalculator:
    """Calculates probability of winning the bid"""

    async def calculate_win_probability(
        self,
        bid_recommendation_score: float,
        risk_level: str,
        compliance_score: float,
        competitive_complexity: str,
    ) -> Dict[str, Any]:
        """
        Calculate win probability.

        Args:
            bid_recommendation_score: Bid decision score (0-100)
            risk_level: Risk assessment level
            compliance_score: Compliance check score (0-100)
            competitive_complexity: Complexity level

        Returns:
            Win probability analysis
        """
        logger.info("Calculating win probability")

        # Base probability from bid recommendation
        win_prob = bid_recommendation_score * 0.4

        # Adjust for risk
        risk_adjustments = {
            "LOW": 0.9,
            "MEDIUM": 0.7,
            "HIGH": 0.4,
        }
        win_prob += 20 * risk_adjustments.get(risk_level, 0.5)

        # Adjust for compliance
        compliance_factor = (compliance_score / 100) * 25
        win_prob += compliance_factor

        # Adjust for complexity
        complexity_adjustments = {
            "simple": 1.0,
            "moderate": 0.8,
            "complex": 0.5,
        }
        complexity_factor = 15 * complexity_adjustments.get(competitive_complexity.lower(), 0.5)
        win_prob += complexity_factor

        # Normalize to 0-100
        win_prob = min(100, max(0, win_prob))

        # Categorize probability
        if win_prob >= 70:
            category = "HIGH"
            interpretation = "Strong likelihood of winning this bid"
        elif win_prob >= 50:
            category = "MODERATE"
            interpretation = "Reasonable chance with competitive positioning"
        elif win_prob >= 30:
            category = "LOW"
            interpretation = "Significant competition expected"
        else:
            category = "VERY LOW"
            interpretation = "Limited chances of success"

        return {
            "win_probability": round(win_prob, 1),
            "category": category,
            "interpretation": interpretation,
            "confidence": 70.0,
            "factors": {
                "bid_score_contribution": bid_recommendation_score * 0.4,
                "risk_contribution": 20 * risk_adjustments.get(risk_level, 0.5),
                "compliance_contribution": compliance_factor,
                "complexity_contribution": complexity_factor,
            },
        }
