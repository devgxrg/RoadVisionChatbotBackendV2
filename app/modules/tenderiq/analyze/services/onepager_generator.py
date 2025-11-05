"""
OnePager Generator Service (Phase 3).

Generates high-level executive summaries from tender analysis data.
Creates one-page summaries for quick decision making.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import UUID
import time

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("Google Generative AI not available - OnePager generation will be limited")

from sqlalchemy.orm import Session
from app.modules.tenderiq.analyze.db.repository import AnalyzeRepository
from app.modules.tenderiq.analyze.models.structured_extraction_models import (
    OnePagerData,
    ProjectOverview,
    FinancialRequirements,
    EligibilityHighlights,
    KeyDates,
    RiskFactors,
    CompetitiveAnalysis,
    MoneyAmount,
    ProjectDuration,
    Currency,
)

logger = logging.getLogger(__name__)


class OnePagerGenerator:
    """
    Generates one-page executive summaries from tender analysis data.
    Uses LLM-based synthesis with keyword-based fallback.
    """

    def __init__(self):
        """Initialize generator with Gemini API if available"""
        self.gemini_model = None
        if GEMINI_AVAILABLE:
            api_key = None
            try:
                from app.config import settings
                api_key = settings.GOOGLE_API_KEY
            except:
                import os
                api_key = os.getenv("GOOGLE_API_KEY")

            if api_key:
                genai.configure(api_key=api_key)
                self.gemini_model = genai.GenerativeModel("gemini-pro")
                logger.info("✅ Google Gemini API initialized for OnePager generation")
            else:
                logger.warning("GOOGLE_API_KEY not configured")
        else:
            logger.warning("Google Generative AI not installed")

    async def generate_onepager(
        self,
        db: Session,
        analysis_id: UUID,
        raw_text: str,
        extracted_tender_info: Optional[Dict[str, Any]] = None,
        use_llm: bool = True,
    ) -> OnePagerData:
        """
        Generate executive summary (one-pager) from tender data.

        Args:
            db: Database session
            analysis_id: Analysis ID for tracking
            raw_text: Raw tender document text
            extracted_tender_info: Optional pre-extracted tender information
            use_llm: Whether to use LLM generation

        Returns:
            OnePagerData with executive summary
        """
        start_time = time.time()
        logger.info(f"Starting onepager generation for analysis {analysis_id}")

        try:
            if use_llm and self.gemini_model:
                onepager = await self._generate_with_llm(
                    raw_text, extracted_tender_info
                )
            else:
                onepager = await self._generate_with_keywords(
                    raw_text, extracted_tender_info
                )

            onepager.extractionConfidence = self._calculate_confidence(onepager)
            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(f"✅ OnePager generated in {duration_ms}ms")

            return onepager

        except Exception as e:
            logger.error(f"❌ OnePager generation failed: {e}", exc_info=True)
            raise

    # ===== LLM-based Generation =====

    async def _generate_with_llm(
        self,
        text: str,
        tender_info: Optional[Dict[str, Any]] = None,
    ) -> OnePagerData:
        """Generate onepager using Google Gemini"""
        prompt = self._build_onepager_prompt(text, tender_info)

        try:
            response = self.gemini_model.generate_content(prompt)
            response_text = response.text.strip()

            # Handle markdown code blocks
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            response_text = response_text.strip()

            data = json.loads(response_text)
            return self._build_onepager_from_dict(data)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            return await self._generate_with_keywords(text, tender_info)
        except Exception as e:
            logger.warning(f"LLM generation failed: {e}")
            return await self._generate_with_keywords(text, tender_info)

    # ===== Keyword-based Generation (Fallback) =====

    async def _generate_with_keywords(
        self,
        text: str,
        tender_info: Optional[Dict[str, Any]] = None,
    ) -> OnePagerData:
        """Generate onepager using keyword extraction"""
        # Extract project overview
        project_overview = self._extract_project_overview(text)

        # Extract financial information
        financial = self._extract_financial_requirements(text)

        # Extract eligibility criteria
        eligibility = self._extract_eligibility_highlights(text)

        # Extract key dates
        key_dates = self._extract_key_dates(text)

        # Assess risk factors
        risk_factors = self._assess_risk_factors(text)

        # Estimate competitive analysis
        competitive_analysis = self._estimate_competitive_analysis(text)

        onepager = OnePagerData(
            projectOverview=project_overview,
            financialRequirements=financial,
            eligibilityHighlights=eligibility,
            keyDates=key_dates,
            riskFactors=risk_factors,
            competitiveAnalysis=competitive_analysis,
            extractionConfidence=60.0,  # Moderate confidence for keyword-based
        )

        return onepager

    # ===== Prompt Builder =====

    def _build_onepager_prompt(
        self,
        text: str,
        tender_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build prompt for onepager generation"""
        tender_context = ""
        if tender_info:
            tender_context = f"""
Reference: {tender_info.get('referenceNumber', 'N/A')}
Title: {tender_info.get('title', 'N/A')}
Value: {tender_info.get('estimatedValue', {}).get('displayText', 'N/A')}
"""

        return f"""You are an expert tender analyst. Generate a one-page executive summary from this tender document.

{tender_context}

TENDER DOCUMENT:
{text[:4000]}  # Limit to first 4000 chars

Generate a comprehensive one-pager with the following JSON structure:
{{
  "projectOverview": {{
    "description": "100-200 word project description",
    "keyHighlights": ["highlight 1", "highlight 2", "highlight 3"],
    "projectScope": "Brief scope description"
  }},
  "financialRequirements": {{
    "contractValue": {{"amount": <number>, "currency": "INR", "displayText": "formatted"}},
    "emdAmount": {{"amount": <number>, "currency": "INR", "displayText": "formatted"}},
    "emdPercentage": <number>,
    "performanceBankGuarantee": {{"amount": <number>, "currency": "INR", "displayText": "formatted"}},
    "pbgPercentage": <number>,
    "totalUpfrontCost": {{"amount": <number>, "currency": "INR", "displayText": "formatted"}}
  }},
  "eligibilityHighlights": {{
    "minimumExperience": "Required experience description",
    "minimumTurnover": {{"amount": <number>, "currency": "INR", "displayText": "formatted"}},
    "specialRelaxations": ["relaxation 1", "relaxation 2"]
  }},
  "keyDates": {{
    "bidSubmissionDeadline": "ISO 8601 date",
    "technicalEvaluation": "ISO 8601 date",
    "financialBidOpening": "ISO 8601 date",
    "projectDuration": {{"value": <number>, "unit": "months", "displayText": "24 months"}}
  }},
  "riskFactors": {{
    "level": "low|medium|high",
    "factors": ["risk factor 1", "risk factor 2"]
  }},
  "competitiveAnalysis": {{
    "estimatedBidders": "10-15 bidders",
    "complexity": "simple|moderate|complex",
    "barriers": ["barrier 1", "barrier 2"]
  }}
}}

Return ONLY valid JSON, no other text."""

    # ===== Helper Methods: Keyword-based Generation =====

    def _extract_project_overview(self, text: str) -> ProjectOverview:
        """Extract project overview information"""
        import re

        # Extract description from overview sections
        description = ""
        for pattern in [
            r"(?:project\s+overview|scope\s+of\s+work)[:\s]*([^\n]+(?:\n[^\n]{0,200})?)",
            r"(?:description|overview)[:\s]*([^\n]+(?:\n[^\n]{0,200})?)",
        ]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                description = match.group(1).strip()[:200]
                break

        if not description:
            # Use first few sentences
            sentences = text.split(". ")
            description = ". ".join(sentences[:2])[:200]

        # Extract key highlights (look for bullet points or numbered items)
        highlights = []
        for pattern in [
            r"(?:highlights?|key\s+points?)[:\s]*([^\n]+(?:\n[^\n]+)*)",
        ]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                items = re.split(r"[•\-\*\n]", match.group(1))
                highlights = [item.strip() for item in items if item.strip()][:5]
                break

        if not highlights:
            highlights = [
                "Professional tender document",
                "Structured requirements",
                "Clear deliverables",
            ]

        project_scope = "Comprehensive project scope"
        for pattern in [
            r"(?:scope)[:\s]*([^\n]+(?:\n[^\n]{0,100})?)",
        ]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                project_scope = match.group(1).strip()[:150]
                break

        return ProjectOverview(
            description=description,
            keyHighlights=highlights,
            projectScope=project_scope,
        )

    def _extract_financial_requirements(self, text: str) -> FinancialRequirements:
        """Extract financial requirements summary"""
        import re

        # Extract contract value
        contract_value = MoneyAmount(
            amount=0.0,
            currency=Currency.INR,
            displayText="Not specified",
        )

        match = re.search(
            r"(?:contract\s+value|estimated\s+value)[:\s]*₹?\s*([0-9.]+)\s*(?:crore|cr|lakh|l)",
            text,
            re.IGNORECASE,
        )
        if match:
            try:
                amount = float(match.group(1))
                if "crore" in match.group(0).lower():
                    amount *= 100
                contract_value = MoneyAmount(
                    amount=amount,
                    currency=Currency.INR,
                    displayText=f"₹{amount:.2f} L",
                )
            except ValueError:
                pass

        # Calculate upfront cost (EMD + fees)
        total_upfront = contract_value.amount * 0.03  # Rough estimate: 3% of contract value

        return FinancialRequirements(
            contractValue=contract_value,
            emdAmount=MoneyAmount(
                amount=contract_value.amount * 0.02,
                currency=Currency.INR,
                displayText=f"₹{contract_value.amount * 0.02:.2f} L",
            ) if contract_value.amount > 0 else None,
            emdPercentage=2.0,
            performanceBankGuarantee=MoneyAmount(
                amount=contract_value.amount * 0.10,
                currency=Currency.INR,
                displayText=f"₹{contract_value.amount * 0.10:.2f} L",
            ) if contract_value.amount > 0 else None,
            pbgPercentage=10.0,
            totalUpfrontCost=MoneyAmount(
                amount=total_upfront,
                currency=Currency.INR,
                displayText=f"₹{total_upfront:.2f} L",
            ) if contract_value.amount > 0 else None,
            extractionConfidence=65.0,
        )

    def _extract_eligibility_highlights(self, text: str) -> EligibilityHighlights:
        """Extract eligibility criteria highlights"""
        import re

        # Extract minimum experience
        min_experience = "Not specified"
        for pattern in [
            r"(?:minimum\s+experience|experience\s+required)[:\s]*([^\n]+)",
            r"(\d+)\s+(?:years?|months?)\s+(?:in|of)\s+([^\n]+)",
        ]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if "(?:years?" in pattern:
                    # For the second pattern, group 1 is the number
                    min_experience = match.group(0).strip()[:100]
                else:
                    min_experience = match.group(1).strip()[:100]
                break

        # Extract minimum turnover
        min_turnover = None
        match = re.search(
            r"(?:minimum\s+turnover)[:\s]*₹?\s*([0-9.]+)\s*(?:crore|cr|lakh|l)",
            text,
            re.IGNORECASE,
        )
        if match:
            try:
                amount = float(match.group(1))
                if "crore" in match.group(0).lower():
                    amount *= 100
                min_turnover = MoneyAmount(
                    amount=amount,
                    currency=Currency.INR,
                    displayText=f"₹{amount:.2f} L",
                )
            except ValueError:
                pass

        return EligibilityHighlights(
            minimumExperience=min_experience,
            minimumTurnover=min_turnover,
            specialRelaxations=[],
            extractionConfidence=60.0,
        )

    def _extract_key_dates(self, text: str) -> KeyDates:
        """Extract key dates from tender"""
        import re

        # Try to extract dates (simplified)
        bid_deadline = None
        for pattern in [
            r"(?:bid\s+submission|submission\s+deadline)[:\s]*([^\n]+)",
        ]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                bid_deadline = match.group(1).strip()[:50]
                break

        # Extract project duration
        duration = None
        match = re.search(
            r"(?:project\s+duration|duration)[:\s]*(\d+)\s*(?:months?|days?|years?)",
            text,
            re.IGNORECASE,
        )
        if match:
            try:
                value = int(match.group(1))
                unit = "months"
                if "days" in match.group(0).lower():
                    unit = "days"
                elif "years" in match.group(0).lower():
                    unit = "years"

                duration = ProjectDuration(
                    value=value,
                    unit=unit,
                    displayText=f"{value} {unit}",
                )
            except ValueError:
                pass

        return KeyDates(
            bidSubmissionDeadline=bid_deadline,
            projectDuration=duration,
            extractionConfidence=50.0,
        )

    def _assess_risk_factors(self, text: str) -> RiskFactors:
        """Assess risk level and factors"""
        # Simple risk assessment based on text analysis
        text_lower = text.lower()

        # Count risk indicators
        high_risk_terms = [
            "challenging",
            "complex",
            "difficult",
            "strict",
            "demanding",
            "compressed",
        ]
        medium_risk_terms = ["moderate", "standard", "typical", "regular"]
        low_risk_terms = ["simple", "straightforward", "basic", "routine"]

        high_count = sum(1 for term in high_risk_terms if term in text_lower)
        medium_count = sum(1 for term in medium_risk_terms if term in text_lower)
        low_count = sum(1 for term in low_risk_terms if term in text_lower)

        if high_count > medium_count and high_count > low_count:
            risk_level = "high"
        elif medium_count > low_count:
            risk_level = "medium"
        else:
            risk_level = "low"

        factors = [
            "Strict compliance requirements",
            "Performance guarantees required",
            "Competitive bidding environment",
        ]

        return RiskFactors(
            level=risk_level,
            factors=factors,
        )

    def _estimate_competitive_analysis(self, text: str) -> CompetitiveAnalysis:
        """Estimate competitive analysis"""
        # Estimate based on tender value and category
        estimated_bidders = "10-15 bidders expected"
        complexity = "moderate"
        barriers = [
            "Technical qualification requirements",
            "Financial thresholds",
            "Experience requirements",
        ]

        return CompetitiveAnalysis(
            estimatedBidders=estimated_bidders,
            complexity=complexity,
            barriers=barriers,
        )

    # ===== Data Building Helpers =====

    def _build_onepager_from_dict(self, data: Dict[str, Any]) -> OnePagerData:
        """Build OnePagerData from extracted dictionary"""
        project_overview = None
        if data.get("projectOverview"):
            po = data["projectOverview"]
            project_overview = ProjectOverview(
                description=po.get("description", ""),
                keyHighlights=po.get("keyHighlights", []),
                projectScope=po.get("projectScope"),
            )

        financial = None
        if data.get("financialRequirements"):
            fr = data["financialRequirements"]
            financial = FinancialRequirements(
                contractValue=MoneyAmount(**fr.get("contractValue", {}))
                if fr.get("contractValue")
                else MoneyAmount(amount=0, currency=Currency.INR, displayText="N/A"),
                emdAmount=MoneyAmount(**fr.get("emdAmount", {}))
                if fr.get("emdAmount")
                else None,
                emdPercentage=fr.get("emdPercentage"),
                performanceBankGuarantee=MoneyAmount(**fr.get("performanceBankGuarantee", {}))
                if fr.get("performanceBankGuarantee")
                else None,
                pbgPercentage=fr.get("pbgPercentage"),
                totalUpfrontCost=MoneyAmount(**fr.get("totalUpfrontCost", {}))
                if fr.get("totalUpfrontCost")
                else None,
                extractionConfidence=85.0,
            )

        return OnePagerData(
            projectOverview=project_overview,
            financialRequirements=financial,
            extractionConfidence=85.0,
        )

    def _calculate_confidence(self, onepager: OnePagerData) -> float:
        """Calculate overall generation confidence"""
        confidence = 50.0

        if onepager.projectOverview:
            if onepager.projectOverview.description:
                confidence += 10
            if onepager.projectOverview.keyHighlights:
                confidence += 10

        if onepager.financialRequirements:
            if onepager.financialRequirements.contractValue.amount > 0:
                confidence += 10

        if onepager.eligibilityHighlights:
            confidence += 10

        if onepager.keyDates:
            confidence += 10

        return min(100.0, confidence)
