"""
Document Parser Service

Handles PDF parsing and text extraction using LLAMA Cloud OCR.

Features:
- PDF text extraction with OCR fallback for scanned documents
- Automatic section identification
- Table and figure detection
- Quality assessment of extraction
- Confidence scoring per section
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from uuid import UUID
import time
import os

try:
    from llama_parse import LlamaParse
    LLAMA_PARSE_AVAILABLE = True
except ImportError:
    LLAMA_PARSE_AVAILABLE = False
    logging.warning("LLAMA_PARSE not available - OCR functionality will be limited")

from sqlalchemy.orm import Session

from app.modules.tenderiq.analyze.db.repository import AnalyzeRepository
from app.modules.tenderiq.analyze.db.schema import TenderExtractedContent, ExtractionQualityMetrics
from app.modules.tenderiq.analyze.models.document_extraction_models import (
    DocumentExtractionResult,
    DocumentMetadata,
    ExtractedSection,
    ExtractedTable,
    ExtractedFigure,
    ExtractionQualityResult,
    QualityWarning,
    QualityRecommendation,
)

logger = logging.getLogger(__name__)


class DocumentParser:
    """
    Parses tender documents and extracts structured content.

    Uses LLAMA Cloud for OCR and text extraction from PDFs.
    Includes section identification, table detection, and quality assessment.
    """

    def __init__(self):
        """Initialize document parser with LLAMA Cloud if available"""
        self.llama_parse = None
        if LLAMA_PARSE_AVAILABLE:
            api_key = os.getenv("LLAMA_CLOUD_API_KEY")
            if api_key:
                self.llama_parse = LlamaParse(api_key=api_key)
                logger.info("✅ LLAMA Cloud parser initialized")
            else:
                logger.warning("LLAMA_CLOUD_API_KEY not configured")
        else:
            logger.warning("LLAMA Parse library not installed")

    async def parse_document(
        self,
        db: Session,
        analysis_id: UUID,
        file_path: str,
        file_size: int,
    ) -> DocumentExtractionResult:
        """
        Parse a tender document and extract structured content.

        Args:
            db: Database session
            analysis_id: Analysis ID to associate with extraction
            file_path: Path to PDF file
            file_size: File size in bytes

        Returns:
            DocumentExtractionResult with extracted content and quality metrics

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file parsing fails
        """
        start_time = time.time()
        logger.info(f"Starting document parsing for analysis {analysis_id}")

        # Verify file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document not found: {file_path}")

        # Get file metadata
        filename = os.path.basename(file_path)
        file_type = self._get_file_type(file_path)

        try:
            # Extract text from PDF
            raw_text, ocr_required, ocr_confidence = await self._extract_text(file_path)

            # Parse sections from text
            sections = await self._parse_sections(raw_text)

            # Extract tables
            tables = await self._extract_tables(raw_text)

            # Extract figures
            figures = await self._extract_figures(raw_text)

            # Assess extraction quality
            quality = await self._assess_quality(
                raw_text=raw_text,
                sections=sections,
                tables=tables,
                figures=figures,
                ocr_required=ocr_required,
                ocr_confidence=ocr_confidence,
            )

            # Calculate page count (estimate if not available)
            page_count = self._estimate_page_count(raw_text)

            # Create extraction result
            extraction_result = DocumentExtractionResult(
                analysis_id=analysis_id,
                metadata=DocumentMetadata(
                    original_filename=filename,
                    file_size=file_size,
                    file_type=file_type,
                    page_count=page_count,
                    uploaded_at=datetime.utcnow(),
                ),
                raw_text=raw_text,
                sections=sections,
                tables=tables,
                figures=figures,
                extraction_quality=quality["extraction_quality"],
                ocr_required=ocr_required,
                ocr_confidence=ocr_confidence,
                extractable_sections=len(sections),
                extraction_started_at=datetime.utcnow(),
                extraction_completed_at=datetime.utcnow(),
                processing_duration_seconds=time.time() - start_time,
            )

            # Store in database
            await self._store_extraction(db, extraction_result)

            # Store quality metrics
            await self._store_quality_metrics(db, analysis_id, quality)

            logger.info(
                f"✅ Document parsing completed: {len(sections)} sections, "
                f"{len(tables)} tables, {len(figures)} figures"
            )

            return extraction_result

        except Exception as e:
            logger.error(f"❌ Document parsing failed: {e}", exc_info=True)
            raise

    async def _extract_text(self, file_path: str) -> Tuple[str, bool, Optional[float]]:
        """
        Extract text from PDF using LLAMA Cloud.

        Returns:
            Tuple of (text, ocr_required, ocr_confidence)
        """
        try:
            if self.llama_parse:
                logger.info(f"Parsing {file_path} with LLAMA Cloud")
                parsed_doc = self.llama_parse.load_data(file_path)
                # LLAMA returns Document objects
                text = "\n".join([doc.text if hasattr(doc, 'text') else str(doc) for doc in parsed_doc])
                ocr_required = True
                ocr_confidence = 90.0  # LLAMA Cloud generally has high confidence
                return text, ocr_required, ocr_confidence
            else:
                # Fallback: try basic PDF extraction
                logger.warning("LLAMA Parse not available, using basic text extraction")
                text = self._basic_pdf_extraction(file_path)
                return text, False, None

        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            raise ValueError(f"Failed to extract text from document: {e}")

    def _basic_pdf_extraction(self, file_path: str) -> str:
        """
        Basic PDF text extraction fallback (no OCR).

        This is a simple implementation. In production, you'd use PyPDF2 or pdfplumber.
        """
        try:
            import PyPDF2
            text_parts = []
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text_parts.append(page.extract_text())
            return "\n".join(text_parts)
        except ImportError:
            logger.warning("PyPDF2 not installed for basic extraction")
            raise ValueError("No PDF extraction library available")
        except Exception as e:
            logger.error(f"Basic PDF extraction failed: {e}")
            raise

    async def _parse_sections(self, text: str) -> List[ExtractedSection]:
        """
        Parse sections from extracted text.

        Identifies major sections by looking for numbering patterns.
        """
        sections = []
        section_pattern_lines = []

        lines = text.split('\n')
        current_section = None
        section_text = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Check if line is a section header (e.g., "1.", "2.1", "Section 3")
            if self._is_section_header(stripped):
                # Save previous section if exists
                if current_section:
                    current_section.text = '\n'.join(section_text).strip()
                    sections.append(current_section)

                # Start new section
                section_number = self._extract_section_number(stripped)
                current_section = ExtractedSection(
                    section_number=section_number,
                    title=stripped,
                    text="",
                    page_numbers=[],
                    confidence=95.0 if section_number else 70.0,
                )
                section_text = []
            elif current_section and stripped:
                section_text.append(line)

        # Add last section
        if current_section:
            current_section.text = '\n'.join(section_text).strip()
            sections.append(current_section)

        logger.info(f"Identified {len(sections)} sections in document")
        return sections

    async def _extract_tables(self, text: str) -> List[ExtractedTable]:
        """
        Detect and extract tables from document.

        This is a simple implementation that looks for table-like patterns.
        """
        tables = []

        # Split by common table delimiters
        table_count = 0

        # Look for lines that contain multiple pipes or tabs
        lines = text.split('\n')
        current_table_lines = []

        for i, line in enumerate(lines):
            # Detect table rows (containing pipes or multiple spaces)
            is_table_row = '|' in line or line.count('  ') > 2

            if is_table_row:
                current_table_lines.append(line)
            elif current_table_lines:
                # End of table
                if len(current_table_lines) > 1:
                    table_count += 1
                    tables.append(ExtractedTable(
                        table_number=table_count,
                        title=f"Table {table_count}",
                        data={"raw_content": '\n'.join(current_table_lines)},
                        page_number=max(1, i // 50),  # Estimate
                        location_on_page="middle",
                        confidence=75.0,
                    ))
                current_table_lines = []

        logger.info(f"Detected {len(tables)} tables in document")
        return tables

    async def _extract_figures(self, text: str) -> List[ExtractedFigure]:
        """
        Detect and extract figures/images from document.

        This is a basic implementation looking for figure references.
        """
        figures = []
        figure_count = 0

        # Look for figure references like "Figure 1", "Fig. 1", etc.
        import re
        pattern = r'(?:Figure|Fig\.?)\s+(\d+)'

        for match in re.finditer(pattern, text, re.IGNORECASE):
            figure_count += 1
            # Get context around the match
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            context = text[start:end].strip()

            figures.append(ExtractedFigure(
                figure_number=figure_count,
                description=context[:200],
                figure_type="diagram",
                page_number=max(1, text[:match.start()].count('\n') // 40),  # Estimate
                confidence=70.0,
            ))

        logger.info(f"Detected {len(figures)} figures in document")
        return figures

    async def _assess_quality(
        self,
        raw_text: str,
        sections: List[ExtractedSection],
        tables: List[ExtractedTable],
        figures: List[ExtractedFigure],
        ocr_required: bool,
        ocr_confidence: Optional[float],
    ) -> Dict[str, Any]:
        """
        Assess extraction quality and generate warnings/recommendations.
        """
        warnings = []
        recommendations = []

        # Calculate metrics
        text_length = len(raw_text)
        avg_section_length = text_length / max(1, len(sections))

        # Quality checks
        if ocr_required and ocr_confidence and ocr_confidence < 70:
            warnings.append(QualityWarning(
                field="overall",
                severity="high",
                message="OCR confidence below optimal threshold",
                recommendation="Consider re-uploading a higher quality document scan",
            ))
            recommendations.append(QualityRecommendation(
                priority="high",
                suggestion="Improve document scan quality (higher DPI, better lighting)",
                impact="Could improve accuracy of all extracted fields",
            ))

        if text_length < 1000:
            warnings.append(QualityWarning(
                field="raw_text",
                severity="medium",
                message="Extracted text is unusually short",
                recommendation="Verify document completeness",
            ))

        if len(sections) < 3:
            warnings.append(QualityWarning(
                field="sections",
                severity="low",
                message="Fewer than 3 sections identified",
                recommendation="Document may have unusual structure",
            ))

        if avg_section_length < 500:
            warnings.append(QualityWarning(
                field="sections",
                severity="low",
                message="Average section length is short",
                recommendation="Some sections may be incomplete",
            ))

        # Overall confidence calculation
        extraction_quality = 85.0
        if ocr_required:
            extraction_quality = ocr_confidence or 80.0
        if warnings:
            extraction_quality -= len(warnings) * 5

        return {
            "extraction_quality": max(0, min(100, extraction_quality)),
            "data_completeness": min(100, 70 + len(sections) * 5),  # 70-100 based on sections
            "tender_info_confidence": 80.0,
            "financial_confidence": 75.0,
            "scope_confidence": 78.0,
            "rfp_sections_confidence": 80.0,
            "eligibility_confidence": 75.0,
            "warnings": warnings,
            "recommendations": recommendations,
            "sections_extracted": len(sections),
            "tables_extracted": len(tables),
            "figures_extracted": len(figures),
            "annexures_identified": max(0, len(sections) - 5),
        }

    async def _store_extraction(
        self,
        db: Session,
        extraction_result: DocumentExtractionResult,
    ) -> None:
        """Store extraction result in database"""
        content = TenderExtractedContent(
            analysis_id=extraction_result.analysis_id,
            original_filename=extraction_result.metadata.original_filename,
            file_size=extraction_result.metadata.file_size,
            file_type=extraction_result.metadata.file_type,
            page_count=extraction_result.metadata.page_count,
            uploaded_at=extraction_result.metadata.uploaded_at,
            raw_text=extraction_result.raw_text,
            sections={s.section_number: {"title": s.title, "text": s.text} for s in extraction_result.sections},
            tables=[t.model_dump() for t in extraction_result.tables],
            figures=[f.model_dump() for f in extraction_result.figures],
            extraction_quality=extraction_result.extraction_quality,
            ocr_required=extraction_result.ocr_required,
            ocr_confidence=extraction_result.ocr_confidence,
            extractable_sections=extraction_result.extractable_sections,
            created_at=extraction_result.extraction_started_at,
            extraction_started_at=extraction_result.extraction_started_at,
            extraction_completed_at=extraction_result.extraction_completed_at,
        )
        db.add(content)
        db.commit()
        logger.info(f"✅ Stored extraction result for analysis {extraction_result.analysis_id}")

    async def _store_quality_metrics(
        self,
        db: Session,
        analysis_id: UUID,
        quality: Dict[str, Any],
    ) -> None:
        """Store quality metrics in database"""
        metrics = ExtractionQualityMetrics(
            analysis_id=analysis_id,
            data_completeness=quality["data_completeness"],
            overall_confidence=quality["extraction_quality"],
            tender_info_confidence=quality["tender_info_confidence"],
            financial_confidence=quality["financial_confidence"],
            scope_confidence=quality["scope_confidence"],
            rfp_sections_confidence=quality["rfp_sections_confidence"],
            eligibility_confidence=quality["eligibility_confidence"],
            warnings=[w.model_dump() for w in quality["warnings"]],
            recommendations=[r.model_dump() for r in quality["recommendations"]],
            sections_extracted=quality["sections_extracted"],
            tables_extracted=quality["tables_extracted"],
            figures_extracted=quality["figures_extracted"],
            annexures_identified=quality["annexures_identified"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(metrics)
        db.commit()
        logger.info(f"✅ Stored quality metrics for analysis {analysis_id}")

    # Helper methods

    def _get_file_type(self, file_path: str) -> str:
        """Get MIME type of file"""
        ext = os.path.splitext(file_path)[1].lower()
        mime_types = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
        }
        return mime_types.get(ext, "application/octet-stream")

    def _is_section_header(self, line: str) -> bool:
        """Check if a line is likely a section header"""
        import re
        # Numbered patterns (case-insensitive for "Section", "Chapter", etc.)
        if re.match(r'^\d+\.?\s', line):  # "1." or "1 " followed by space
            return True
        if re.match(r'^\d+(\.\d+)+\s', line):  # "2.1", "1.2.3" followed by space
            return True
        if re.match(r'^[A-Z][A-Z\s]+$', line):  # All caps (case-sensitive)
            return True
        if re.match(r'^(Section|Chapter|Part)\s+\d+', line, re.IGNORECASE):  # Named sections
            return True
        return False

    def _extract_section_number(self, line: str) -> str:
        """Extract section number from header"""
        import re
        match = re.match(r'^(\d+(?:\.\d+)*)', line)
        if match:
            return match.group(1)
        return "unknown"

    def _estimate_page_count(self, text: str) -> int:
        """Estimate page count based on text length"""
        # Rough estimate: ~3000 chars per page
        return max(1, len(text) // 3000)
