"""
Report Generation Service

Generates one-pagers and data sheets from analysis results.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.orm import Session

from app.modules.tenderiq.db.tenderiq_repository import TenderIQRepository
from app.modules.tenderiq.services.document_parser import DocumentParser
from app.modules.tenderiq.services.tender_info_extractor import TenderInfoExtractor
from app.modules.tenderiq.services.onepager_generator import OnePagerGenerator
from app.modules.tenderiq.analyze.models.structured_extraction_models import OnePagerData
from app.modules.tenderiq.models.pydantic_models import (
    OnePagerResponse,
    DataSheetResponse,
    DataSheetContentResponse,
    BasicInfoResponse,
    FinancialInfoResponse,
    TemporalInfoResponse,
    ScopeInfoResponse,
    AnalysisInfoResponse,
)


class ReportGenerationService:
    """Service for generating reports from analysis results"""

    def __init__(self):
        pass

    async def generate_one_pager(
        self,
        db: Session,
        tender_id: UUID,
        format: str = "markdown",
        include_risk_assessment: bool = True,
        include_scope_of_work: bool = True,
        include_financials: bool = True,
        max_length: int = 800,
    ) -> OnePagerResponse:
        """
        Generate a one-page executive summary by running an on-demand analysis.
        """
        import os
        
        # 1. Fetch tender and document path
        repo = TenderIQRepository(db)
        tender = repo.get_tender_by_id(tender_id)
        if not tender or not tender.files:
            raise ValueError("Tender or associated documents not found.")
        file_path = tender.files[0].dms_path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document file not found at path: {file_path}")

        # 2. Parse document text
        doc_parser = DocumentParser()
        raw_text, _, _ = await doc_parser._extract_text(file_path)

        # 3. Extract info and generate onepager data
        info_extractor = TenderInfoExtractor()
        onepager_generator = OnePagerGenerator()

        tender_info = await info_extractor.extract_tender_info(db, uuid4(), raw_text)
        onepager_data = await onepager_generator.generate_onepager(
            db=db,
            analysis_id=uuid4(),
            raw_text=raw_text,
            extracted_tender_info=tender_info.model_dump()
        )

        # 4. Format the structured data into markdown
        one_pager_content = self._format_one_pager_from_data(tender_id, onepager_data)
        formatted_content = self.format_for_output(one_pager_content, format)

        return OnePagerResponse(
            tender_id=tender_id,
            one_pager={
                "content": formatted_content,
                "format": format,
                "generatedAt": datetime.utcnow().isoformat(),
            },
        )

    def generate_data_sheet(
        self,
        db: Session,
        tender_id: UUID,
        format: str = "json",
        include_analysis: bool = True,
    ) -> DataSheetResponse:
        """
        Generate a structured data sheet with key tender information.

        Args:
            db: Database session
            tender_id: Tender ID
            format: Output format: "json", "csv", or "excel"
            include_analysis: Include analysis results in sheet

        Returns:
            DataSheetResponse with generated data sheet
        """
        # TODO: Fetch tender data from ScrapedTender
        # TODO: Fetch analysis results if include_analysis=True

        # Sample tender and analysis data
        basic_info = BasicInfoResponse(
            tender_number="TEN-2024-001",
            tender_name="Cloud Infrastructure Migration Project",
            tendering_authority="Ministry of Technology",
            tender_url="https://example.com/tender/001",
        )

        financial_info = FinancialInfoResponse(
            estimated_value=5000000.0,
            currency="INR",
            emd=250000.0,
            bid_security_required=True,
        )

        temporal_info = TemporalInfoResponse(
            release_date="2024-11-01",
            due_date="2024-12-15",
            opening_date="2024-12-20",
        )

        scope_info = ScopeInfoResponse(
            location="New Delhi",
            category="Cloud Services",
            description="Migrate legacy infrastructure to cloud with minimal downtime",
        )

        analysis_info = None
        if include_analysis:
            analysis_info = AnalysisInfoResponse(
                risk_level="medium",
                estimated_effort=120,
                complexity_level="high",
            )

        data_sheet = DataSheetContentResponse(
            basic_info=basic_info,
            financial_info=financial_info,
            temporal=temporal_info,
            scope=scope_info,
            analysis=analysis_info,
        )

        return DataSheetResponse(
            tender_id=tender_id,
            data_sheet=data_sheet,
            generated_at=datetime.utcnow(),
        )

    def format_for_output(
        self,
        content: str,
        format: str = "markdown",
    ) -> str:
        """
        Convert content to desired output format.

        Args:
            content: Content to format
            format: Target format: "markdown", "html", or "pdf"

        Returns:
            Formatted content
        """
        if format == "markdown":
            return content
        elif format == "html":
            return self._markdown_to_html(content)
        elif format == "pdf":
            # TODO: Use library like reportlab or weasyprint
            return content  # For now, return markdown
        else:
            return content

    # ==================== Helper Methods ====================

    def _format_one_pager_from_data(self, tender_id: UUID, data: OnePagerData) -> str:
        """Formats the structured OnePagerData into a markdown string."""
        lines = [
            "# Tender Analysis Executive Summary",
            f"\n**Tender ID:** {tender_id}",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        # Project Overview
        if data.projectOverview:
            lines.append("\n## Project Overview")
            lines.append(data.projectOverview.description)
            if data.projectOverview.keyHighlights:
                lines.append("\n**Key Highlights:**")
                lines.extend([f"- {h}" for h in data.projectOverview.keyHighlights])
            if data.projectOverview.projectScope:
                lines.append(f"\n**Scope:** {data.projectOverview.projectScope}")

        # Financials
        if data.financialRequirements:
            fr = data.financialRequirements
            lines.append("\n## Financial Summary")
            if fr.contractValue:
                lines.append(f"- **Contract Value:** {fr.contractValue.displayText}")
            if fr.emdAmount:
                lines.append(f"- **EMD:** {fr.emdAmount.displayText} ({fr.emdPercentage}%)")
            if fr.performanceBankGuarantee:
                lines.append(f"- **PBG:** {fr.performanceBankGuarantee.displayText} ({fr.pbgPercentage}%)")

        # Eligibility
        if data.eligibilityHighlights:
            eh = data.eligibilityHighlights
            lines.append("\n## Eligibility")
            if eh.minimumExperience:
                lines.append(f"- **Experience:** {eh.minimumExperience}")
            if eh.minimumTurnover:
                lines.append(f"- **Turnover:** {eh.minimumTurnover.displayText}")

        # Key Dates
        if data.keyDates:
            kd = data.keyDates
            lines.append("\n## Key Dates & Duration")
            if kd.bidSubmissionDeadline:
                lines.append(f"- **Submission Deadline:** {kd.bidSubmissionDeadline}")
            if kd.projectDuration:
                lines.append(f"- **Project Duration:** {kd.projectDuration.displayText}")

        # Risks
        if data.riskFactors:
            rf = data.riskFactors
            lines.append(f"\n## Risk Assessment")
            lines.append(f"**Overall Risk Level:** {rf.level.upper()}")
            if rf.factors:
                lines.append("\n**Key Factors:**")
                lines.extend([f"- {f}" for f in rf.factors])
        
        lines.extend([
            "\n---",
            "*This is an automated analysis. Please review with domain experts.*",
        ])
        
        return "\n".join(lines)

    def _markdown_to_html(self, markdown_content: str) -> str:
        """
        Convert markdown to basic HTML.

        TODO: Use markdown library for proper conversion.

        Args:
            markdown_content: Markdown formatted string

        Returns:
            Basic HTML string
        """
        html = "<html><body>\n"

        lines = markdown_content.split("\n")
        for line in lines:
            if line.startswith("# "):
                html += f"<h1>{line[2:]}</h1>\n"
            elif line.startswith("## "):
                html += f"<h2>{line[3:]}</h2>\n"
            elif line.startswith("### "):
                html += f"<h3>{line[4:]}</h3>\n"
            elif line.startswith("- "):
                html += f"<li>{line[2:]}</li>\n"
            elif line.startswith("**") and line.endswith("**"):
                content = line[2:-2]
                html += f"<strong>{content}</strong>\n"
            elif line.startswith("*") and line.endswith("*"):
                content = line[1:-1]
                html += f"<em>{content}</em>\n"
            elif line.strip() == "---":
                html += "<hr/>\n"
            elif line.strip():
                html += f"<p>{line}</p>\n"

        html += "\n</body></html>"
        return html

    def _format_markdown_one_pager(
        self,
        title: str,
        sections: Dict[str, Any],
    ) -> str:
        """
        Format one-pager content as markdown.

        Args:
            title: Document title
            sections: Dict of section_name -> content

        Returns:
            Markdown formatted string
        """
        lines = [f"# {title}", ""]

        for section_name, section_content in sections.items():
            lines.append(f"## {section_name}")
            if isinstance(section_content, dict):
                for key, value in section_content.items():
                    lines.append(f"- **{key}:** {value}")
            elif isinstance(section_content, list):
                for item in section_content:
                    lines.append(f"- {item}")
            else:
                lines.append(str(section_content))
            lines.append("")

        return "\n".join(lines)

    def _format_markdown_data_sheet(
        self,
        tender_data: Dict[str, Any],
        analysis_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Format data sheet content as markdown table.

        Args:
            tender_data: Basic tender information
            analysis_data: Analysis results (optional)

        Returns:
            Markdown formatted string with table
        """
        lines = ["# Tender Data Sheet", ""]

        # Create markdown table
        lines.append("| Property | Value |")
        lines.append("|----------|-------|")

        # Add tender data rows
        for key, value in tender_data.items():
            lines.append(f"| {key} | {value} |")

        if analysis_data:
            lines.append("")
            lines.append("## Analysis Results")
            lines.append("")
            for key, value in analysis_data.items():
                lines.append(f"| {key} | {value} |")

        return "\n".join(lines)
