from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime


# ==================== Tender Models ====================

class TenderFile(BaseModel):
    id: UUID
    file_name: str
    file_url: str
    dms_path: str
    file_description: Optional[str] = None
    file_size: Optional[str] = None
    is_cached: bool = False
    cache_status: Optional[str] = "pending"
    model_config = ConfigDict(from_attributes=True)

class Tender(BaseModel):
    id: UUID
    tender_id_str: str
    tender_name: str
    tender_url: str
    drive_url: Optional[str] = None
    city: str
    summary: str
    value: str
    due_date: str
    tdr: Optional[str] = None
    tendering_authority: Optional[str] = None
    tender_no: Optional[str] = None
    tender_id_detail: Optional[str] = None
    tender_brief: Optional[str] = None
    state: Optional[str] = None
    document_fees: Optional[str] = None
    emd: Optional[str] = None
    tender_value: Optional[str] = None
    tender_type: Optional[str] = None
    bidding_type: Optional[str] = None
    competition_type: Optional[str] = None
    tender_details: Optional[str] = None
    publish_date: Optional[str] = None
    last_date_of_bid_submission: Optional[str] = None
    tender_opening_date: Optional[str] = None
    company_name: Optional[str] = None
    contact_person: Optional[str] = None
    address: Optional[str] = None
    information_source: Optional[str] = None
    files: list[TenderFile]
    dms_folder_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)

class TenderCreate(BaseModel):
    tender_title: str
    description: Optional[str] = None
    status: str = 'New'


# ==================== Request Models ====================

class AnalyzeTenderRequest(BaseModel):
    """Request to initiate tender analysis"""
    document_ids: Optional[List[UUID]] = None  # Specific documents to analyze
    analysis_type: Optional[str] = "full"  # "full", "summary", "risk-only"
    include_risk_assessment: bool = True
    include_rfp_analysis: bool = True
    include_scope_of_work: bool = True


class GenerateOnePagerRequest(BaseModel):
    """Request to generate one-pager"""
    format: str = "markdown"  # "markdown", "html", "pdf"
    include_risk_assessment: bool = True
    include_scope_of_work: bool = True
    include_financials: bool = True
    max_length: int = 800  # words


# ==================== Response Models - Analysis Metadata ====================

class AnalysisStatusResponse(BaseModel):
    """Status of an ongoing analysis"""
    analysis_id: UUID
    tender_id: UUID
    status: str  # "pending", "processing", "completed", "failed"
    progress: int  # 0-100
    current_step: str  # "initializing", "parsing-documents", "analyzing-risk", etc
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AnalysisInitiatedResponse(BaseModel):
    """Response when analysis is initiated (202 Accepted)"""
    analysis_id: UUID
    tender_id: UUID
    status: str
    created_at: datetime
    estimated_completion_time: int  # milliseconds


# ==================== Response Models - Risk Assessment ====================

class RiskDetailResponse(BaseModel):
    """Single risk identified"""
    id: UUID
    level: str  # "low", "medium", "high", "critical"
    category: str  # "regulatory", "financial", "operational", "contractual", "market"
    title: str
    description: str
    impact: str  # "low", "medium", "high"
    likelihood: str  # "low", "medium", "high"
    mitigation_strategy: Optional[str] = None
    recommended_action: Optional[str] = None
    related_documents: List[UUID] = []

    model_config = ConfigDict(from_attributes=True)


class RiskAssessmentResponse(BaseModel):
    """Risk assessment for a tender"""
    tender_id: UUID
    overall_risk_level: str  # "low", "medium", "high", "critical"
    risk_score: int  # 0-100
    executive_summary: Optional[str] = None
    risks: List[RiskDetailResponse]
    analyzed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskAssessmentInAnalysis(BaseModel):
    """Risk assessment component in full analysis results"""
    overall_risk_level: str
    risk_score: int
    risks: List[RiskDetailResponse]


# ==================== Response Models - RFP Analysis ====================

class RFPSectionComplianceResponse(BaseModel):
    """Compliance status for RFP section"""
    status: str  # "compliant", "non-compliant", "requires-review"
    issues: List[str] = []


class DocumentReferenceResponse(BaseModel):
    """Reference to document and location"""
    document_id: UUID
    page_number: Optional[int] = None


class RFPSectionResponse(BaseModel):
    """Single RFP section"""
    id: UUID
    number: str  # "1.1", "2.3", etc
    title: str
    description: str
    key_requirements: List[str]
    compliance: Optional[RFPSectionComplianceResponse] = None
    estimated_complexity: str  # "low", "medium", "high"
    related_sections: List[str] = []
    document_references: List[DocumentReferenceResponse] = []

    model_config = ConfigDict(from_attributes=True)


class RFPSectionSummaryResponse(BaseModel):
    """Summary of all RFP sections"""
    total_requirements: int
    criticality: dict  # {"high": 12, "medium": 23, "low": 10}


class RFPAnalysisResponse(BaseModel):
    """RFP section analysis for a tender"""
    tender_id: UUID
    total_sections: int
    sections: List[RFPSectionResponse]
    summary: RFPSectionSummaryResponse

    model_config = ConfigDict(from_attributes=True)


class RFPAnalysisInResults(BaseModel):
    """RFP analysis component in full analysis results"""
    sections: List[RFPSectionResponse]
    missing_documents: List[str] = []


# ==================== Response Models - Scope of Work ====================

class WorkItemResponse(BaseModel):
    """Single work item"""
    id: UUID
    description: str
    estimated_duration: str
    priority: str  # "high", "medium", "low"
    dependencies: List[UUID] = []


class DeliverableResponse(BaseModel):
    """Deliverable with acceptance criteria"""
    id: UUID
    description: str
    delivery_date: Optional[str] = None  # "YYYY-MM-DD"
    acceptance_criteria: List[str] = []


class KeyDatesResponse(BaseModel):
    """Key project dates"""
    start_date: Optional[str] = None  # "YYYY-MM-DD"
    end_date: Optional[str] = None


class ScopeOfWorkDetailResponse(BaseModel):
    """Detailed scope of work"""
    description: str
    work_items: List[WorkItemResponse] = []
    key_deliverables: List[DeliverableResponse] = []
    estimated_total_effort: int  # days
    estimated_total_duration: str
    key_dates: KeyDatesResponse


class ScopeOfWorkResponse(BaseModel):
    """Scope of work analysis for a tender"""
    tender_id: UUID
    scope_of_work: ScopeOfWorkDetailResponse
    analyzed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScopeOfWorkInResults(BaseModel):
    """Scope of work component in full analysis results"""
    description: str
    estimated_duration: str
    key_deliverables: List[str]
    estimated_effort: int  # days


# ==================== Response Models - Summary ====================

class TenderSummaryResponse(BaseModel):
    """Summary of tender analysis"""
    title: str
    overview: str
    key_points: List[str]


# ==================== Response Models - One-Pager ====================

class OnePagerResponse(BaseModel):
    """Generated one-pager document"""
    tender_id: UUID
    one_pager: dict  # {content: str, format: str, generatedAt: datetime}

    model_config = ConfigDict(from_attributes=True)


# ==================== Response Models - Data Sheet ====================

class BasicInfoResponse(BaseModel):
    """Basic tender information"""
    tender_number: str
    tender_name: str
    tendering_authority: str
    tender_url: str


class FinancialInfoResponse(BaseModel):
    """Financial information"""
    estimated_value: Optional[float] = None
    currency: str = "INR"
    emd: Optional[float] = None
    bid_security_required: bool = False


class TemporalInfoResponse(BaseModel):
    """Timeline information"""
    release_date: Optional[str] = None
    due_date: Optional[str] = None
    opening_date: Optional[str] = None


class ScopeInfoResponse(BaseModel):
    """Scope information"""
    location: str
    category: str
    description: str


class AnalysisInfoResponse(BaseModel):
    """Analysis summary in datasheet"""
    risk_level: str
    estimated_effort: int
    complexity_level: str


class DataSheetContentResponse(BaseModel):
    """Data sheet content"""
    basic_info: BasicInfoResponse
    financial_info: FinancialInfoResponse
    temporal: TemporalInfoResponse
    scope: ScopeInfoResponse
    analysis: Optional[AnalysisInfoResponse] = None


class DataSheetResponse(BaseModel):
    """Generated data sheet"""
    tender_id: UUID
    data_sheet: DataSheetContentResponse
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== Response Models - Full Analysis Results ====================

class AnalysisResultsResponse(BaseModel):
    """Complete analysis results for a tender"""
    analysis_id: UUID
    tender_id: UUID
    status: str  # "completed" or "failed"
    results: dict  # {summary, riskAssessment, rfpAnalysis, scopeOfWork, onePager}
    completed_at: datetime
    processing_time_ms: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== Response Models - Analysis List ====================

class AnalysisListItemResponse(BaseModel):
    """Item in analyses list"""
    analysis_id: UUID
    tender_id: UUID
    tender_name: Optional[str] = None
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    processing_time_ms: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class PaginationResponse(BaseModel):
    """Pagination metadata"""
    total: int
    limit: int
    offset: int


class AnalysesListResponse(BaseModel):
    """List of recent analyses"""
    analyses: List[AnalysisListItemResponse]
    pagination: PaginationResponse


# ==================== Response Models - Delete ====================

class DeleteAnalysisResponse(BaseModel):
    """Response to delete analysis"""
    success: bool
    message: str


# ==================== Response Models - Error ====================

class ErrorResponse(BaseModel):
    """Consistent error response format"""
    error: str
    code: str  # "INVALID_REQUEST", "UNAUTHORIZED", "NOT_FOUND", etc
    details: Optional[str] = None
    timestamp: datetime

# ==================== Scraper Models ====================

class ScrapedTenderQuery(BaseModel):
    id: UUID
    query_name: str
    number_of_tenders: str
    tenders: list[Tender]
    model_config = ConfigDict(from_attributes=True)


class DailyTendersResponse(BaseModel):
    id: UUID
    run_at: datetime
    date_str: str
    name: str
    contact: str
    no_of_new_tenders: str
    company: str
    queries: list[ScrapedTenderQuery]
    model_config = ConfigDict(from_attributes=True)


# ==================== Date Filtering Models ====================

class ScrapeDateInfo(BaseModel):
    """Information about a specific scrape date with tender count"""
    date: str  # YYYY-MM-DD
    date_str: str  # "November 3, 2024"
    run_at: datetime  # ISO format timestamp
    tender_count: int  # Total tenders on this date
    is_latest: bool  # Whether this is the most recent scrape

    model_config = ConfigDict(from_attributes=True)


class AvailableDatesResponse(BaseModel):
    """Response for GET /api/v1/tenderiq/dates endpoint"""
    dates: list[ScrapeDateInfo]  # All available scrape dates


class FilteredTendersResponse(BaseModel):
    """Response for GET /api/v1/tenderiq/tenders endpoint with filters"""
    tenders: list[Tender]  # Filtered tender results
    total_count: int  # Total number of tenders returned
    filtered_by: dict  # What filters were applied (e.g., {"date_range": "last_5_days"})
    available_dates: list[str]  # List of all available dates in YYYY-MM-DD format

    model_config = ConfigDict(from_attributes=True)
