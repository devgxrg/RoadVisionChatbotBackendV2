"""
RFP Extraction Service

Extracts and analyzes RFP (Request for Proposal) sections from tender documents.
"""

from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.orm import Session

from app.modules.tenderiq.db.repository import AnalyzeRepository
from app.modules.tenderiq.models.pydantic_models import (
    RFPAnalysisResponse,
    RFPSectionResponse,
    RFPSectionSummaryResponse,
    RFPSectionComplianceResponse,
)


class RFPExtractionService:
    """Service for extracting and analyzing RFP sections"""

    def __init__(self):
        pass

    def extract_rfp_sections(
        self,
        tender_id: UUID,
        section_number: Optional[str] = None,
        include_compliance: bool = False,
    ) -> RFPAnalysisResponse:
        """
        Extract RFP sections from tender documents.

        Args:
            tender_id: Tender to analyze
            section_number: Optional specific section to retrieve
            include_compliance: Include compliance assessment

        Returns:
            RFPAnalysisResponse with extracted sections
        """
        # Sample RFP sections for demonstration
        sample_sections = [
            {
                "number": "1.0",
                "title": "Eligibility Criteria",
                "description": "Vendor must be registered and in good standing for minimum 3 years",
                "requirements": [
                    "Valid business registration",
                    "Minimum 3 years operational history",
                    "No pending litigation",
                    "GST registration",
                ],
                "complexity": "low",
            },
            {
                "number": "2.0",
                "title": "Technical Requirements",
                "description": "Technical specifications for proposed solution and resources",
                "requirements": [
                    "System architecture design",
                    "Technology stack specification",
                    "Disaster recovery plan",
                    "Security framework",
                    "Performance benchmarks",
                ],
                "complexity": "high",
            },
            {
                "number": "3.0",
                "title": "Commercial Terms",
                "description": "Pricing and commercial conditions",
                "requirements": [
                    "Detailed price quotation",
                    "Payment terms (Net 30)",
                    "Warranty period (12 months)",
                    "Service level agreement",
                ],
                "complexity": "medium",
            },
        ]

        # Build response directly without database interaction
        section_responses = []
        criticality_counts = {"high": 0, "medium": 0, "low": 0}
        total_requirements = 0

        for section_data in sample_sections:
            if section_number and section_data["number"] != section_number:
                continue

            complexity = section_data["complexity"]
            criticality_counts[complexity] += 1
            total_requirements += len(section_data["requirements"])

            compliance = None
            if include_compliance:
                compliance = RFPSectionComplianceResponse(
                    status="requires-review",
                    issues=[],
                )

            section_responses.append(
                RFPSectionResponse(
                    id=uuid4(),
                    number=section_data["number"],
                    title=section_data["title"],
                    description=section_data["description"],
                    key_requirements=section_data["requirements"],
                    compliance=compliance,
                    estimated_complexity=complexity,
                    related_sections=self._find_related_sections(section_data["number"]),
                    document_references=[],
                )
            )

        return RFPAnalysisResponse(
            tender_id=tender_id,
            total_sections=len(section_responses),
            sections=section_responses,
            summary=RFPSectionSummaryResponse(
                total_requirements=total_requirements,
                criticality=criticality_counts,
            ),
        )

    def identify_requirements(self, section_text: str) -> List[str]:
        """
        Extract key requirements from an RFP section.

        Uses sentence-based parsing. TODO: Upgrade to LLM-based extraction.

        Args:
            section_text: Text of the RFP section

        Returns:
            List of identified requirements
        """
        if not section_text:
            return []

        requirements = []

        # Split by common requirement keywords
        requirement_keywords = ["must", "shall", "required", "should", "need", "provide"]
        sentences = section_text.split(".")

        for sentence in sentences:
            sentence_clean = sentence.strip()
            if any(keyword in sentence_clean.lower() for keyword in requirement_keywords):
                if len(sentence_clean) > 10:  # Filter out very short strings
                    requirements.append(sentence_clean)

        # Remove duplicates while preserving order
        seen = set()
        unique_requirements = []
        for req in requirements:
            if req not in seen:
                seen.add(req)
                unique_requirements.append(req)

        return unique_requirements[:10]  # Return top 10 requirements

    def assess_section_complexity(self, section_text: str) -> str:
        """
        Estimate complexity of an RFP section (low/medium/high).

        Uses heuristics based on section length and keywords.

        Args:
            section_text: Text of the RFP section

        Returns:
            Complexity level: "low", "medium", or "high"
        """
        if not section_text:
            return "medium"

        text_lower = section_text.lower()

        # High complexity indicators
        high_complexity_keywords = [
            "architecture", "implementation", "security", "performance",
            "integration", "compliance", "regulation", "technical",
            "infrastructure", "enterprise", "scalability", "recovery"
        ]

        # Low complexity indicators
        low_complexity_keywords = [
            "basic", "simple", "standard", "general", "eligibility",
            "registration", "name", "address", "contact"
        ]

        high_score = sum(text_lower.count(keyword) for keyword in high_complexity_keywords)
        low_score = sum(text_lower.count(keyword) for keyword in low_complexity_keywords)
        word_count = len(section_text.split())

        # Calculate complexity
        if high_score > low_score and word_count > 200:
            return "high"
        elif low_score > high_score or word_count < 100:
            return "low"
        else:
            return "medium"

    def identify_missing_documents(
        self,
        sections: List[dict],
        provided_documents: List[str]
    ) -> List[str]:
        """
        Identify documents referenced in RFP but not provided.

        Args:
            sections: RFP sections with requirements
            provided_documents: List of document names provided

        Returns:
            List of missing document names
        """
        if not sections:
            return []

        document_keywords = [
            "document", "certificate", "letter", "report", "statement",
            "plan", "proposal", "specification", "design", "drawing"
        ]

        mentioned_documents = set()
        provided_lower = [doc.lower() for doc in provided_documents]

        for section in sections:
            description = section.get("description", "").lower()
            requirements = [req.lower() for req in section.get("requirements", [])]

            # Search for document references
            all_text = " ".join([description] + requirements)

            for keyword in document_keywords:
                if keyword in all_text:
                    # Extract document type (e.g., "Technical Document", "Audit Report")
                    words = all_text.split()
                    for i, word in enumerate(words):
                        if keyword in word.lower() and i > 0:
                            doc_name = " ".join(words[max(0, i-2):i+1])
                            mentioned_documents.add(doc_name)

        # Find missing documents
        missing = []
        for doc in mentioned_documents:
            if not any(doc.lower() in prov.lower() or prov.lower() in doc.lower()
                      for prov in provided_lower):
                missing.append(doc)

        return list(missing)[:5]  # Return top 5 missing documents

    # ==================== Helper Methods ====================

    def _find_related_sections(self, section_number: str) -> List[str]:
        """Find related section numbers"""
        # In a real implementation, would use semantic analysis
        # For now, return sections with adjacent numbers
        try:
            num = float(section_number)
            related = [
                str(num + 0.1),
                str(num + 1.0),
            ]
            return [r for r in related if r != section_number]
        except ValueError:
            return []
