"""
Scope of Work Analyzer Service (Phase 3).

Extracts and analyzes work items, deliverables, and effort estimation from tender documents.
"""

import logging
import json
import re
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

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class WorkItem:
    """Represents a single work item or deliverable"""

    def __init__(
        self,
        id: str,
        title: str,
        description: str,
        category: str,
        complexity: str,
        estimated_days: int,
        dependencies: Optional[List[str]] = None,
        confidence: float = 75.0,
    ):
        self.id = id
        self.title = title
        self.description = description
        self.category = category  # e.g., "construction", "equipment", "services"
        self.complexity = complexity  # low, medium, high
        self.estimated_days = estimated_days
        self.dependencies = dependencies or []
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "complexity": self.complexity,
            "estimatedDays": self.estimated_days,
            "dependencies": self.dependencies,
            "confidence": self.confidence,
        }


class ScopeOfWorkAnalyzer:
    """
    Analyzes scope of work from tender documents.
    Extracts work items, deliverables, and provides effort estimation.
    """

    def __init__(self):
        """Initialize analyzer with Gemini API if available"""
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
                logger.info("✅ Gemini initialized for scope analysis")

    async def analyze_scope(
        self,
        db: Session,
        analysis_id: UUID,
        raw_text: str,
        use_llm: bool = True,
    ) -> Dict[str, Any]:
        """
        Analyze scope of work from tender document.

        Args:
            db: Database session
            analysis_id: Analysis ID
            raw_text: Raw tender text
            use_llm: Use LLM-based analysis

        Returns:
            Dictionary with work items and effort estimation
        """
        start_time = time.time()
        logger.info(f"Starting scope analysis for {analysis_id}")

        try:
            work_items = []

            if use_llm and self.gemini_model:
                work_items = await self._extract_with_llm(raw_text)
            else:
                work_items = await self._extract_with_keywords(raw_text)

            # Calculate totals
            total_effort = sum(item.estimated_days for item in work_items)
            avg_confidence = (
                sum(item.confidence for item in work_items) / len(work_items)
                if work_items
                else 0
            )

            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(f"✅ Scope analysis completed: {len(work_items)} items, {total_effort} days")

            return {
                "work_items": [item.to_dict() for item in work_items],
                "total_effort_days": total_effort,
                "estimated_duration_months": max(1, total_effort // 20),  # Rough estimate
                "item_count": len(work_items),
                "average_confidence": avg_confidence,
                "complexity_distribution": self._calculate_complexity_distribution(
                    work_items
                ),
                "category_distribution": self._calculate_category_distribution(
                    work_items
                ),
                "processing_duration_ms": duration_ms,
            }

        except Exception as e:
            logger.error(f"❌ Scope analysis failed: {e}", exc_info=True)
            raise

    # ===== LLM-based Extraction =====

    async def _extract_with_llm(self, text: str) -> List[WorkItem]:
        """Extract work items using Gemini"""
        prompt = self._build_scope_prompt(text)

        try:
            response = self.gemini_model.generate_content(prompt)
            response_text = response.text.strip()

            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            response_text = response_text.strip()

            data = json.loads(response_text)
            work_items = []

            for i, item in enumerate(data.get("work_items", [])):
                work_item = WorkItem(
                    id=f"WI-{i+1:03d}",
                    title=item.get("title", "Work Item"),
                    description=item.get("description", ""),
                    category=item.get("category", "general"),
                    complexity=item.get("complexity", "medium"),
                    estimated_days=item.get("estimated_days", 10),
                    dependencies=item.get("dependencies", []),
                    confidence=min(100, item.get("confidence", 85)),
                )
                work_items.append(work_item)

            return work_items

        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")
            return await self._extract_with_keywords(text)

    # ===== Keyword-based Extraction (Fallback) =====

    async def _extract_with_keywords(self, text: str) -> List[WorkItem]:
        """Extract work items using keyword patterns"""
        work_items = []

        # Extract major sections that look like work items
        sections = self._split_into_sections(text)

        for section in sections:
            # Try to parse as a work item
            work_item = self._parse_section_as_work_item(section)
            if work_item:
                work_items.append(work_item)

        # If no items found, create default ones
        if not work_items:
            work_items = [
                WorkItem(
                    id="WI-001",
                    title="Project Planning & Design",
                    description="Planning, design, and approvals",
                    category="planning",
                    complexity="medium",
                    estimated_days=20,
                    confidence=60.0,
                ),
                WorkItem(
                    id="WI-002",
                    title="Implementation",
                    description="Main project implementation",
                    category="implementation",
                    complexity="high",
                    estimated_days=100,
                    confidence=60.0,
                ),
                WorkItem(
                    id="WI-003",
                    title="Testing & QA",
                    description="Quality assurance and testing",
                    category="testing",
                    complexity="medium",
                    estimated_days=20,
                    confidence=60.0,
                ),
                WorkItem(
                    id="WI-004",
                    title="Deployment & Support",
                    description="Deployment and post-launch support",
                    category="deployment",
                    complexity="medium",
                    estimated_days=15,
                    confidence=60.0,
                ),
            ]

        return work_items

    # ===== Prompt Builder =====

    def _build_scope_prompt(self, text: str) -> str:
        """Build prompt for scope analysis"""
        return f"""You are an expert project scope analyzer. Extract all work items and deliverables from this tender document.

TENDER DOCUMENT:
{text[:4000]}

Identify and return a structured list of work items/deliverables in this JSON format:
{{
  "work_items": [
    {{
      "title": "Work item title",
      "description": "Detailed description",
      "category": "category (e.g., construction, supply, services, testing)",
      "complexity": "low|medium|high",
      "estimated_days": <estimated effort in days>,
      "dependencies": ["dependent item 1", "dependent item 2"],
      "confidence": <confidence score 0-100>
    }}
  ]
}}

For each work item:
- Title: Clear, concise name
- Description: 1-2 sentences
- Category: construction, supply, services, testing, planning, deployment, etc.
- Complexity: Based on technical difficulty and effort
- Estimated days: Your estimate (use complexity as guide)
- Dependencies: Any prerequisite work items
- Confidence: How confident you are in the extraction (0-100)

Return ONLY valid JSON."""

    # ===== Helper Methods =====

    def _split_into_sections(self, text: str) -> List[str]:
        """Split text into sections for analysis"""
        sections = []

        # Look for numbered sections (1., 1.1, etc.)
        section_pattern = r"(?:^|\n)\s*(\d+(?:\.\d+)*)\s+([^\n]+)"
        matches = list(re.finditer(section_pattern, text, re.MULTILINE))

        for i, match in enumerate(matches):
            # Get content from this section to the next
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section = text[start:end].strip()

            if section:
                sections.append(section)

        # If no numbered sections found, try splitting by bullets
        if not sections:
            current_section = []
            for line in text.split("\n"):
                stripped = line.strip()
                if re.match(r"^•|^-|^\d+\.", stripped):
                    if current_section:
                        sections.append("\n".join(current_section))
                    current_section = [stripped]
                else:
                    current_section.append(stripped)

            if current_section:
                sections.append("\n".join(current_section))

        return sections if sections else [text]

    def _parse_section_as_work_item(self, section: str) -> Optional[WorkItem]:
        """Try to parse a section as a work item"""
        lines = section.split("\n")
        if not lines:
            return None

        # First line is likely the title
        title = lines[0].strip()

        # Remove numbering and common prefixes
        title = re.sub(r"^[\d.•\-\s]+", "", title).strip()
        if not title or len(title) < 5:
            return None

        # Rest is description
        description = " ".join(l.strip() for l in lines[1:] if l.strip())[:200]

        # Estimate complexity based on keywords
        section_text = section.lower()
        if any(w in section_text for w in ["complex", "difficult", "challenging", "advanced"]):
            complexity = "high"
            estimated_days = 30
        elif any(w in section_text for w in ["moderate", "standard", "typical"]):
            complexity = "medium"
            estimated_days = 20
        else:
            complexity = "low"
            estimated_days = 10

        # Determine category
        category = self._determine_category(section_text)

        return WorkItem(
            id=f"WI-{hash(title) % 1000:03d}",
            title=title,
            description=description,
            category=category,
            complexity=complexity,
            estimated_days=estimated_days,
            confidence=70.0,
        )

    def _determine_category(self, text: str) -> str:
        """Determine work item category from text"""
        categories = {
            "planning": ["planning", "design", "architecture", "proposal"],
            "construction": ["construction", "build", "installation", "setup"],
            "supply": ["supply", "procurement", "equipment", "material"],
            "services": ["service", "consultation", "support", "maintenance"],
            "testing": ["test", "qa", "quality", "validation", "verification"],
            "deployment": ["deploy", "launch", "go-live", "release"],
        }

        for category, keywords in categories.items():
            if any(keyword in text for keyword in keywords):
                return category

        return "general"

    def _calculate_complexity_distribution(
        self, work_items: List[WorkItem]
    ) -> Dict[str, int]:
        """Calculate distribution of complexity levels"""
        distribution = {"low": 0, "medium": 0, "high": 0}
        for item in work_items:
            distribution[item.complexity] += 1
        return distribution

    def _calculate_category_distribution(
        self, work_items: List[WorkItem]
    ) -> Dict[str, int]:
        """Calculate distribution of categories"""
        distribution: Dict[str, int] = {}
        for item in work_items:
            distribution[item.category] = distribution.get(item.category, 0) + 1
        return distribution
