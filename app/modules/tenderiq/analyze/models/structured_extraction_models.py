"""
Pydantic Models for Structured Data Extraction (Phases 2-4).

Defines the structured data models for information extracted from tender text,
including tender metadata, financial details, one-pager summaries, etc.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date
from enum import Enum


class Currency(str, Enum):
    INR = "INR"
    USD = "USD"


class MoneyAmount(BaseModel):
    amount: float
    currency: Currency
    displayText: str


class TenderType(str, Enum):
    OPEN = "open"
    LIMITED = "limited"
    EOI = "eoi"
    RATE_CONTRACT = "rateContract"


class TenderStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    AWARDED = "awarded"


class Coordinates(BaseModel):
    latitude: float
    longitude: float


class ProjectLocation(BaseModel):
    state: str
    city: Optional[str] = None
    district: Optional[str] = None
    coordinates: Optional[Coordinates] = None


class ContactPerson(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None


class RequiredSimilarProjects(BaseModel):
    count: int
    minValue: MoneyAmount
    description: str


class ProjectDuration(BaseModel):
    value: int
    unit: str  # e.g., "days", "months", "years"
    displayText: str


class TenderInfo(BaseModel):
    """Structured tender metadata"""
    referenceNumber: str
    title: str
    issuingOrganization: str
    department: Optional[str] = None
    category: str
    subCategory: Optional[str] = None
    tenderType: TenderType
    status: TenderStatus
    estimatedValue: MoneyAmount
    projectLocation: Optional[ProjectLocation] = None
    contactPerson: Optional[ContactPerson] = None
    publishedDate: Optional[date] = None
    submissionDeadline: Optional[date] = None
    extractionConfidence: float = Field(..., ge=0, le=100)


class FinancialRequirements(BaseModel):
    """Structured financial requirements"""
    contractValue: MoneyAmount
    emdAmount: Optional[MoneyAmount] = None
    emdPercentage: Optional[float] = None
    performanceBankGuarantee: Optional[MoneyAmount] = None
    pbgPercentage: Optional[float] = None
    tenderDocumentFee: Optional[MoneyAmount] = None
    totalUpfrontCost: Optional[MoneyAmount] = None
    extractionConfidence: float = Field(..., ge=0, le=100)


class EligibilityHighlights(BaseModel):
    """Structured eligibility highlights"""
    minimumExperience: str
    minimumTurnover: Optional[MoneyAmount] = None
    requiredCertifications: List[str] = []
    requiredSimilarProjects: Optional[RequiredSimilarProjects] = None
    specialRelaxations: List[str] = []
    extractionConfidence: float = Field(..., ge=0, le=100)


class KeyDates(BaseModel):
    """Structured key dates and timeline"""
    bidSubmissionDeadline: Optional[date] = None
    technicalEvaluation: Optional[date] = None
    financialBidOpening: Optional[date] = None
    projectDuration: Optional[ProjectDuration] = None
    extractionConfidence: float = Field(..., ge=0, le=100)


class RiskFactors(BaseModel):
    """Structured risk factors"""
    level: str  # low, medium, high
    factors: List[str]


class CompetitiveAnalysis(BaseModel):
    """Structured competitive analysis"""
    estimatedBidders: str
    complexity: str  # simple, moderate, complex
    barriers: List[str]


class ProjectOverview(BaseModel):
    """Structured project overview for one-pager"""
    description: str
    keyHighlights: List[str]
    projectScope: Optional[str] = None


class OnePagerData(BaseModel):
    """Complete structured data for a one-pager summary"""
    projectOverview: Optional[ProjectOverview] = None
    financialRequirements: Optional[FinancialRequirements] = None
    eligibilityHighlights: Optional[EligibilityHighlights] = None
    keyDates: Optional[KeyDates] = None
    riskFactors: Optional[RiskFactors] = None
    competitiveAnalysis: Optional[CompetitiveAnalysis] = None
    extractionConfidence: float = Field(..., ge=0, le=100)
