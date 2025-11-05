"""
Tender Information Extractor Service (Phase 2).

Extracts structured tender information from parsed documents using LLM-based analysis.
Focuses on extracting:
- Tender metadata (reference number, title, organization)
- Financial information (contract value, EMD, guarantees)
- Eligibility criteria
- Key dates and timeline
"""

import logging
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from uuid import UUID
import time

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("Google Generative AI not available - LLM extraction will be limited")

from sqlalchemy.orm import Session
from app.modules.tenderiq.analyze.db.repository import AnalyzeRepository
from app.modules.tenderiq.analyze.models.structured_extraction_models import (
    TenderInfo,
    FinancialRequirements,
    EligibilityHighlights,
    KeyDates,
    OnePagerData,
    ProjectOverview,
    RiskFactors,
    CompetitiveAnalysis,
    MoneyAmount,
    ContactPerson,
    ProjectLocation,
    Coordinates,
    RequiredSimilarProjects,
    ProjectDuration,
    TenderType,
    TenderStatus,
    Currency,
)

logger = logging.getLogger(__name__)


class TenderInfoExtractor:
    """
    Extracts structured tender information from document text.
    Uses Google Gemini API for LLM-based extraction with fallback to keyword matching.
    """

    def __init__(self):
        """Initialize extractor with Gemini API if available"""
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
                logger.info("✅ Google Gemini API initialized for tender extraction")
            else:
                logger.warning("GOOGLE_API_KEY not configured - using keyword fallback")
        else:
            logger.warning("Google Generative AI not installed - using keyword fallback")

    async def extract_tender_info(
        self,
        db: Session,
        analysis_id: UUID,
        raw_text: str,
        use_llm: bool = True,
    ) -> TenderInfo:
        """
        Extract tender information from document text.

        Args:
            db: Database session
            analysis_id: Analysis ID for tracking
            raw_text: Raw text from document parser
            use_llm: Whether to use LLM extraction (vs. keyword-based)

        Returns:
            TenderInfo object with extracted metadata
        """
        start_time = time.time()
        logger.info(f"Starting tender info extraction for analysis {analysis_id}")

        try:
            if use_llm and self.gemini_model:
                tender_info = await self._extract_with_llm(raw_text)
                logger.info(f"✅ LLM-based extraction completed")
            else:
                tender_info = await self._extract_with_keywords(raw_text)
                logger.info(f"✅ Keyword-based extraction completed")

            tender_info.extractionConfidence = self._calculate_confidence(tender_info)

            return tender_info

        except Exception as e:
            logger.error(f"❌ Tender info extraction failed: {e}", exc_info=True)
            raise

    async def extract_financial_info(
        self,
        raw_text: str,
        use_llm: bool = True,
    ) -> FinancialRequirements:
        """
        Extract financial requirements from document.

        Args:
            raw_text: Raw text from document parser
            use_llm: Whether to use LLM extraction

        Returns:
            FinancialRequirements object
        """
        logger.info("Starting financial information extraction")

        try:
            if use_llm and self.gemini_model:
                financial = await self._extract_financial_with_llm(raw_text)
            else:
                financial = await self._extract_financial_with_keywords(raw_text)

            financial.extractionConfidence = self._calculate_financial_confidence(financial)
            return financial

        except Exception as e:
            logger.error(f"❌ Financial extraction failed: {e}")
            raise

    # ===== LLM-based Extraction =====

    async def _extract_with_llm(self, text: str) -> TenderInfo:
        """Extract tender info using Google Gemini"""
        prompt = self._build_tender_extraction_prompt(text)

        try:
            response = self.gemini_model.generate_content(prompt)

            # Parse JSON response
            response_text = response.text.strip()

            # Handle markdown code blocks
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            response_text = response_text.strip()

            data = json.loads(response_text)
            return self._build_tender_info_from_dict(data)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            # Fallback to keyword extraction
            return await self._extract_with_keywords(text)
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}, falling back to keywords")
            return await self._extract_with_keywords(text)

    async def _extract_financial_with_llm(self, text: str) -> FinancialRequirements:
        """Extract financial info using Google Gemini"""
        prompt = self._build_financial_extraction_prompt(text)

        try:
            response = self.gemini_model.generate_content(prompt)
            response_text = response.text.strip()

            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            response_text = response_text.strip()

            data = json.loads(response_text)
            return self._build_financial_requirements_from_dict(data)

        except Exception as e:
            logger.warning(f"LLM financial extraction failed: {e}")
            return await self._extract_financial_with_keywords(text)

    # ===== Keyword-based Extraction (Fallback) =====

    async def _extract_with_keywords(self, text: str) -> TenderInfo:
        """Extract tender info using keyword patterns"""
        tender_info = TenderInfo(
            referenceNumber=self._extract_reference_number(text),
            title=self._extract_title(text),
            issuingOrganization=self._extract_organization(text),
            category=self._extract_category(text),
            tenderType=TenderType.OPEN,
            estimatedValue=self._extract_estimated_value(text),
            extractionConfidence=50.0,  # Lower confidence for keyword extraction
        )
        return tender_info

    async def _extract_financial_with_keywords(self, text: str) -> FinancialRequirements:
        """Extract financial info using keyword patterns"""
        contract_value = self._extract_estimated_value(text)

        financial = FinancialRequirements(
            contractValue=contract_value,
            emdAmount=self._extract_emd_amount(text),
            emdPercentage=self._extract_emd_percentage(text),
            performanceBankGuarantee=self._extract_pbg_amount(text),
            pbgPercentage=self._extract_pbg_percentage(text),
            extractionConfidence=50.0,  # Lower confidence for keyword extraction
        )
        return financial

    # ===== Prompt Builders =====

    def _build_tender_extraction_prompt(self, text: str) -> str:
        """Build prompt for tender info extraction"""
        return f"""You are an expert tender document analyst. Extract structured information from this tender document.

TENDER DOCUMENT:
{text[:3000]}  # Limit to first 3000 chars to stay within token limits

Extract the following information and return as JSON:
{{
  "referenceNumber": "unique tender reference ID",
  "title": "tender title",
  "issuingOrganization": "organization name",
  "department": "department name (optional)",
  "estimatedValue": {{
    "amount": <number in lakhs>,
    "currency": "INR",
    "displayText": "formatted amount with currency"
  }},
  "category": "tender category (e.g., Road Construction)",
  "subCategory": "sub-category (optional)",
  "tenderType": "open|limited|eoi|rateContract",
  "status": "active|closed|cancelled|awarded",
  "publishedDate": "ISO 8601 date (optional)",
  "submissionDeadline": "ISO 8601 date (optional)",
  "projectLocation": {{
    "state": "state name",
    "city": "city (optional)",
    "district": "district (optional)"
  }}
}}

Return ONLY valid JSON, no other text."""

    def _build_financial_extraction_prompt(self, text: str) -> str:
        """Build prompt for financial extraction"""
        return f"""You are an expert tender document analyst. Extract financial requirements from this tender document.

TENDER DOCUMENT:
{text[:3000]}

Extract the following financial information and return as JSON:
{{
  "contractValue": {{
    "amount": <number in lakhs>,
    "currency": "INR",
    "displayText": "formatted display"
  }},
  "emdAmount": {{
    "amount": <number in lakhs>,
    "currency": "INR",
    "displayText": "formatted display"
  }},
  "emdPercentage": <percentage>,
  "performanceBankGuarantee": {{
    "amount": <number in lakhs>,
    "currency": "INR",
    "displayText": "formatted display"
  }},
  "pbgPercentage": <percentage>,
  "tenderDocumentFee": {{
    "amount": <number in lakhs>,
    "currency": "INR",
    "displayText": "formatted display"
  }}
}}

Return ONLY valid JSON, no other text."""

    # ===== Helper Methods: Keyword-based Extraction =====

    def _extract_reference_number(self, text: str) -> str:
        """Extract tender reference number"""
        patterns = [
            r'(?:Reference|Tender\s+(?:No|ID)|RFP\s+No)[:\s]*([A-Z0-9/\-]+)',
            r'(?:Ref|Tender)[:\s]+([A-Z0-9/\-]{10,})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return "Unknown"

    def _extract_title(self, text: str) -> str:
        """Extract tender title"""
        lines = text.split('\n')
        exclude_keywords = ['reference', 'earnest', 'deposit', 'percentage', 'amount', 'issued', 'category', 'eligible', 'key financial']
        for line in lines[:30]:  # Check first 30 lines
            stripped = line.strip()
            if (len(stripped) > 20 and len(stripped) < 300 and
                not any(keyword in stripped.lower() for keyword in exclude_keywords) and
                any(word in stripped.lower() for word in ['construction', 'maintenance', 'highway', 'project', 'road', 'building', 'tender for'])):
                return stripped
        return "Tender Document"

    def _extract_organization(self, text: str) -> str:
        """Extract issuing organization"""
        patterns = [
            r'(?:Issued\s+(?:by|from)|Inviting\s+(?:agency|organization))[:\s]*([^\n]+)',
            r'(?:Department|Agency)[:\s]*([^\n]+)',
            r'(?:Public\s+Works|Railway|Highway)[^\n]*',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()[:100]
        return "Government"

    def _extract_category(self, text: str) -> str:
        """Extract tender category"""
        categories = [
            "Road Construction", "Building", "Bridge", "Railway",
            "Water Supply", "Power", "Telecommunications", "Software",
            "Consulting Services", "Equipment Supply"
        ]
        text_lower = text.lower()
        for category in categories:
            if category.lower() in text_lower:
                return category
        return "General Construction"

    def _extract_estimated_value(self, text: str) -> MoneyAmount:
        """Extract contract value"""
        # Look for patterns like "₹15.50 Cr", "₹1550 Lakhs", "15.50 crores"
        patterns = [
            r'(?:estimated\s+)?(?:contract\s+)?(?:value|amount)[:\s]*₹?\s*([0-9.]+)\s*(?:crore|cr|lakh|l)',
            r'₹\s*([0-9.]+)\s*(?:crore|cr|lakh|l)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1)
                try:
                    amount = float(amount_str)
                    # Convert crores to lakhs if needed
                    if 'crore' in match.group(0).lower():
                        amount *= 100
                    return MoneyAmount(
                        amount=amount,
                        currency=Currency.INR,
                        displayText=f"₹{amount:.2f} L"
                    )
                except ValueError:
                    pass

        return MoneyAmount(
            amount=0.0,
            currency=Currency.INR,
            displayText="Not specified"
        )

    def _extract_emd_amount(self, text: str) -> Optional[MoneyAmount]:
        """Extract EMD amount"""
        patterns = [
            r'(?:earnest\s+money|emd)[:\s()]*₹?\s*([0-9.]+)\s*(?:lakh|l|lakhs)',
            r'(?:earnest\s+money|emd)[:\s()]*₹?\s*([0-9.]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    amount = float(match.group(1))
                    if amount > 0:  # Validate it's a real amount
                        return MoneyAmount(
                            amount=amount,
                            currency=Currency.INR,
                            displayText=f"₹{amount:.2f} L"
                        )
                except ValueError:
                    pass
        return None

    def _extract_emd_percentage(self, text: str) -> Optional[float]:
        """Extract EMD percentage"""
        match = re.search(r'emd.*?([0-9.]+)\s*%', text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None

    def _extract_pbg_amount(self, text: str) -> Optional[MoneyAmount]:
        """Extract Performance Bank Guarantee amount"""
        patterns = [
            r'(?:performance\s+(?:security|guarantee|bank\s+guarantee))[:\s]*₹?\s*([0-9.]+)\s*(?:crore|cr|lakh|l|lakhs|crores)',
            r'(?:pbg|performance)[:\s]*₹?\s*([0-9.]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    amount = float(match.group(1))
                    if amount > 0:
                        # Check if amount is in crores
                        if 'crore' in match.group(0).lower():
                            amount *= 100
                        return MoneyAmount(
                            amount=amount,
                            currency=Currency.INR,
                            displayText=f"₹{amount:.2f} L"
                        )
                except ValueError:
                    pass
        return None

    def _extract_pbg_percentage(self, text: str) -> Optional[float]:
        """Extract PBG percentage"""
        patterns = [
            r'(?:performance\s+(?:security|guarantee|bank)).*?([0-9.]+)\s*%',
            r'pbg.*?([0-9.]+)\s*%',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                try:
                    percentage = float(match.group(1))
                    if 0 < percentage <= 100:  # Valid percentage
                        return percentage
                except ValueError:
                    pass
        return None

    # ===== Data Building Helpers =====

    def _build_tender_info_from_dict(self, data: Dict[str, Any]) -> TenderInfo:
        """Build TenderInfo from extracted dictionary"""
        return TenderInfo(
            referenceNumber=data.get("referenceNumber", "Unknown"),
            title=data.get("title", "Tender Document"),
            issuingOrganization=data.get("issuingOrganization", "Government"),
            department=data.get("department"),
            category=data.get("category", "General"),
            subCategory=data.get("subCategory"),
            tenderType=TenderType(data.get("tenderType", "open")),
            status=TenderStatus(data.get("status", "active")),
            estimatedValue=MoneyAmount(
                amount=data.get("estimatedValue", {}).get("amount", 0),
                currency=Currency.INR,
                displayText=data.get("estimatedValue", {}).get("displayText", "₹0 L")
            ),
            publishedDate=data.get("publishedDate"),
            submissionDeadline=data.get("submissionDeadline"),
            extractionConfidence=85.0,  # Higher confidence for LLM extraction
        )

    def _build_financial_requirements_from_dict(self, data: Dict[str, Any]) -> FinancialRequirements:
        """Build FinancialRequirements from extracted dictionary"""
        return FinancialRequirements(
            contractValue=MoneyAmount(
                amount=data.get("contractValue", {}).get("amount", 0),
                currency=Currency.INR,
                displayText=data.get("contractValue", {}).get("displayText", "₹0 L")
            ),
            emdAmount=MoneyAmount(**data["emdAmount"]) if data.get("emdAmount") else None,
            emdPercentage=data.get("emdPercentage"),
            performanceBankGuarantee=MoneyAmount(**data["performanceBankGuarantee"]) if data.get("performanceBankGuarantee") else None,
            pbgPercentage=data.get("pbgPercentage"),
            extractionConfidence=85.0,
        )

    # ===== Confidence Calculation =====

    def _calculate_confidence(self, tender_info: TenderInfo) -> float:
        """Calculate overall extraction confidence"""
        confidence = 50.0  # Base confidence

        # Increase confidence based on what was extracted
        if tender_info.referenceNumber and tender_info.referenceNumber != "Unknown":
            confidence += 10
        if tender_info.title and tender_info.title != "Tender Document":
            confidence += 10
        if tender_info.issuingOrganization and tender_info.issuingOrganization != "Government":
            confidence += 10
        if tender_info.estimatedValue.amount > 0:
            confidence += 10
        if tender_info.projectLocation:
            confidence += 5
        if tender_info.contactPerson:
            confidence += 5

        return min(100.0, confidence)

    def _calculate_financial_confidence(self, financial: FinancialRequirements) -> float:
        """Calculate financial extraction confidence"""
        confidence = 50.0

        if financial.contractValue.amount > 0:
            confidence += 15
        if financial.emdAmount:
            confidence += 10
        if financial.performanceBankGuarantee:
            confidence += 10
        if financial.tenderDocumentFee:
            confidence += 5
        if financial.totalUpfrontCost:
            confidence += 10

        return min(100.0, confidence)
