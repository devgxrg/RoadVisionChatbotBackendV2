"""
RFP Section Analyzer Service (Phase 3).

Analyzes and extracts RFP (Request for Proposal) sections from tender documents.
Identifies requirements, evaluation criteria, and compliance items.
"""

import logging
import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import UUID
import time

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("Google Generative AI not available")

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class RFPSection:
    """Represents a single RFP section"""

    def __init__(
        self,
        section_number: str,
        title: str,
        content: str,
        section_type: str,  # functional, technical, commercial, legal, evaluation
        requirements: List[str],
        sub_sections: Optional[List["RFPSection"]] = None,
        confidence: float = 75.0,
    ):
        self.section_number = section_number
        self.title = title
        self.content = content
        self.section_type = section_type
        self.requirements = requirements
        self.sub_sections = sub_sections or []
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "sectionNumber": self.section_number,
            "title": self.title,
            "content": self.content[:500],  # Truncate for response
            "sectionType": self.section_type,
            "requirements": self.requirements,
            "subSections": [s.to_dict() for s in self.sub_sections],
            "confidence": self.confidence,
        }


class RFPSectionAnalyzer:
    """
    Analyzes RFP sections from tender documents.
    Extracts requirements, evaluation criteria, and compliance items.
    """

    def __init__(self):
        """Initialize analyzer"""
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
                logger.info("✅ Gemini initialized for RFP analysis")

    async def analyze_rfp_sections(
        self,
        db: Session,
        analysis_id: UUID,
        raw_text: str,
        use_llm: bool = True,
    ) -> Dict[str, Any]:
        """
        Analyze RFP sections from tender document.

        Args:
            db: Database session
            analysis_id: Analysis ID
            raw_text: Raw tender text
            use_llm: Use LLM-based analysis

        Returns:
            Dictionary with RFP sections and analysis
        """
        start_time = time.time()
        logger.info(f"Starting RFP section analysis for {analysis_id}")

        try:
            if use_llm and self.gemini_model:
                sections = await self._analyze_with_llm(raw_text)
            else:
                sections = await self._analyze_with_keywords(raw_text)

            # Calculate statistics
            total_requirements = sum(
                len(s.requirements) + sum(len(ss.requirements) for ss in s.sub_sections)
                for s in sections
            )
            avg_confidence = (
                sum(s.confidence for s in sections) / len(sections)
                if sections
                else 0
            )

            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(
                f"✅ RFP analysis completed: {len(sections)} sections, "
                f"{total_requirements} requirements"
            )

            return {
                "sections": [s.to_dict() for s in sections],
                "total_sections": len(sections),
                "total_requirements": total_requirements,
                "section_types": self._get_section_types(sections),
                "average_confidence": avg_confidence,
                "processing_duration_ms": duration_ms,
            }

        except Exception as e:
            logger.error(f"❌ RFP analysis failed: {e}", exc_info=True)
            raise

    # ===== LLM-based Analysis =====

    async def _analyze_with_llm(self, text: str) -> List[RFPSection]:
        """Analyze RFP sections using Gemini"""
        prompt = self._build_rfp_analysis_prompt(text)

        try:
            response = self.gemini_model.generate_content(prompt)
            response_text = response.text.strip()

            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            response_text = response_text.strip()

            data = json.loads(response_text)
            sections = []

            for section_data in data.get("sections", []):
                section = RFPSection(
                    section_number=section_data.get("section_number", ""),
                    title=section_data.get("title", ""),
                    content=section_data.get("content", ""),
                    section_type=section_data.get("section_type", "general"),
                    requirements=section_data.get("requirements", []),
                    confidence=min(100, section_data.get("confidence", 85)),
                )
                sections.append(section)

            return sections

        except Exception as e:
            logger.warning(f"LLM analysis failed: {e}")
            return await self._analyze_with_keywords(text)

    # ===== Keyword-based Analysis (Fallback) =====

    async def _analyze_with_keywords(self, text: str) -> List[RFPSection]:
        """Analyze RFP sections using keyword patterns"""
        sections = []

        # Split text into sections using common RFP patterns
        section_pattern = r"(?:^|\n)(?:Section\s+)?(\d+(?:\.\d+)*)\s+([^\n]+)"
        matches = list(re.finditer(section_pattern, text, re.MULTILINE))

        for i, match in enumerate(matches):
            section_num = match.group(1)
            section_title = match.group(2).strip()

            # Get content until next section
            start = match.end()
            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )
            content = text[start:end].strip()[:1000]

            # Determine section type
            section_type = self._determine_section_type(section_title, content)

            # Extract requirements
            requirements = self._extract_requirements(content)

            section = RFPSection(
                section_number=section_num,
                title=section_title,
                content=content,
                section_type=section_type,
                requirements=requirements,
                confidence=65.0,
            )
            sections.append(section)

        # If no sections found with pattern, create default ones
        if not sections:
            sections = [
                RFPSection(
                    section_number="1",
                    title="Functional Requirements",
                    content="Document functional requirements",
                    section_type="functional",
                    requirements=[
                        "Core functionality must be implemented",
                        "Performance standards must be met",
                    ],
                    confidence=60.0,
                ),
                RFPSection(
                    section_number="2",
                    title="Technical Requirements",
                    content="Document technical specifications",
                    section_type="technical",
                    requirements=[
                        "Technology stack must be specified",
                        "Integration points must be documented",
                    ],
                    confidence=60.0,
                ),
                RFPSection(
                    section_number="3",
                    title="Commercial Terms",
                    content="Document commercial requirements",
                    section_type="commercial",
                    requirements=[
                        "Pricing must be itemized",
                        "Payment terms must be specified",
                    ],
                    confidence=60.0,
                ),
                RFPSection(
                    section_number="4",
                    title="Evaluation Criteria",
                    content="Document evaluation criteria",
                    section_type="evaluation",
                    requirements=[
                        "Technical evaluation criteria",
                        "Commercial evaluation criteria",
                        "Compliance checklist",
                    ],
                    confidence=60.0,
                ),
            ]

        return sections

    # ===== Prompt Builder =====

    def _build_rfp_analysis_prompt(self, text: str) -> str:
        """Build prompt for RFP section analysis"""
        return f"""You are an expert RFP analyst. Analyze this tender document and identify all RFP sections.

TENDER DOCUMENT:
{text[:4000]}

Extract and return RFP sections in this JSON format:
{{
  "sections": [
    {{
      "section_number": "1.0",
      "title": "Section Title",
      "content": "Section content summary",
      "section_type": "functional|technical|commercial|legal|evaluation",
      "requirements": [
        "Specific requirement 1",
        "Specific requirement 2"
      ],
      "confidence": <0-100>
    }}
  ]
}}

For each section:
- section_number: e.g., "1", "1.1", "2.0"
- title: Clear section title
- content: Summary of section content (2-3 sentences)
- section_type: Categorize as functional, technical, commercial, legal, or evaluation
- requirements: List 2-5 key requirements from this section
- confidence: Your confidence in the extraction (0-100)

Return ONLY valid JSON."""

    # ===== Helper Methods =====

    def _determine_section_type(self, title: str, content: str) -> str:
        """Determine the type of RFP section"""
        text = (title + " " + content).lower()

        type_keywords = {
            "functional": [
                "function",
                "feature",
                "capability",
                "behavior",
                "business",
            ],
            "technical": [
                "technical",
                "technology",
                "system",
                "architecture",
                "infrastructure",
                "database",
                "integration",
            ],
            "commercial": [
                "commercial",
                "price",
                "cost",
                "fee",
                "payment",
                "financial",
                "budget",
                "contract",
            ],
            "legal": [
                "legal",
                "law",
                "compliance",
                "regulation",
                "liability",
                "insurance",
                "confidential",
            ],
            "evaluation": [
                "evaluation",
                "criteria",
                "assessment",
                "scoring",
                "selection",
                "bid",
                "proposal",
            ],
        }

        type_scores = {
            section_type: sum(
                1 for keyword in keywords if keyword in text
            )
            for section_type, keywords in type_keywords.items()
        }

        return max(type_scores, key=type_scores.get)

    def _extract_requirements(self, text: str) -> List[str]:
        """Extract requirements from section text"""
        requirements = []

        # Look for bulleted items
        bullet_pattern = r"(?:^|\n)\s*[•\-\*]\s+([^\n]+)"
        for match in re.finditer(bullet_pattern, text):
            req = match.group(1).strip()
            if len(req) > 5:
                requirements.append(req[:100])

        # Look for numbered items
        numbered_pattern = r"(?:^|\n)\s*(\d+)\s*[.)]\s+([^\n]+)"
        for match in re.finditer(numbered_pattern, text):
            req = match.group(2).strip()
            if len(req) > 5:
                requirements.append(req[:100])

        # If few requirements found, extract from sentences
        if len(requirements) < 2:
            sentences = re.split(r"[.!?]", text)
            for sentence in sentences[:3]:
                cleaned = sentence.strip()
                if len(cleaned) > 10:
                    requirements.append(cleaned[:100])

        return requirements[:5]  # Return top 5

    def _get_section_types(self, sections: List[RFPSection]) -> Dict[str, int]:
        """Get distribution of section types"""
        types = {}
        for section in sections:
            types[section.section_type] = types.get(section.section_type, 0) + 1
        return types
