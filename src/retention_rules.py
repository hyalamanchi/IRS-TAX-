# IRS Document Retention Rules Schema

from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

class DocumentAction(Enum):
    SHRED = "SHRED"
    KEEP = "KEEP"
    ARCHIVE = "ARCHIVE"

class DocumentType(Enum):
    TAX_RETURN = "TAX_RETURN"
    W2 = "W2"
    LETTER_CP = "LETTER_CP"
    LETTER_LT = "LETTER_LT"
    NOTICE = "NOTICE"
    CORRESPONDENCE = "CORRESPONDENCE"

@dataclass
class RetentionRule:
    document_type: DocumentType
    retention_period: timedelta
    action: DocumentAction
    requires_scanning: bool
    requires_approval: bool
    sensitive_info: bool = True
    notes: str = ""

# Standard IRS retention periods
RETENTION_RULES = {
    DocumentType.TAX_RETURN: RetentionRule(
        document_type=DocumentType.TAX_RETURN,
        retention_period=timedelta(days=365 * 7),  # 7 years
        action=DocumentAction.KEEP,
        requires_scanning=True,
        requires_approval=True,
        notes="Keep for minimum 7 years after filing"
    ),
    DocumentType.W2: RetentionRule(
        document_type=DocumentType.W2,
        retention_period=timedelta(days=365 * 4),  # 4 years
        action=DocumentAction.KEEP,
        requires_scanning=True,
        requires_approval=False,
        notes="Keep for minimum 4 years"
    ),
    DocumentType.LETTER_CP: RetentionRule(
        document_type=DocumentType.LETTER_CP,
        retention_period=timedelta(days=365 * 3),  # 3 years
        action=DocumentAction.ARCHIVE,
        requires_scanning=True,
        requires_approval=True,
        notes="Scan and keep digital copy for 3 years"
    ),
    DocumentType.LETTER_LT: RetentionRule(
        document_type=DocumentType.LETTER_LT,
        retention_period=timedelta(days=365 * 3),  # 3 years
        action=DocumentAction.ARCHIVE,
        requires_scanning=True,
        requires_approval=True,
        notes="Scan and keep digital copy for 3 years"
    ),
    DocumentType.NOTICE: RetentionRule(
        document_type=DocumentType.NOTICE,
        retention_period=timedelta(days=365 * 2),  # 2 years
        action=DocumentAction.ARCHIVE,
        requires_scanning=True,
        requires_approval=False,
        notes="Scan and archive after processing"
    ),
    DocumentType.CORRESPONDENCE: RetentionRule(
        document_type=DocumentType.CORRESPONDENCE,
        retention_period=timedelta(days=365),  # 1 year
        action=DocumentAction.SHRED,
        requires_scanning=True,
        requires_approval=False,
        notes="Scan and shred after processing if no legal hold"
    )
}

class DocumentProcessor:
    def __init__(self):
        self.rules = RETENTION_RULES

    def get_retention_rule(self, document_type: DocumentType) -> RetentionRule:
        return self.rules.get(document_type)

    def calculate_retention_date(self, document_type: DocumentType, processing_date: datetime = None) -> datetime:
        if processing_date is None:
            processing_date = datetime.now()
        
        rule = self.get_retention_rule(document_type)
        if rule:
            return processing_date + rule.retention_period
        return None

    def should_retain(self, document_type: DocumentType, document_date: datetime) -> bool:
        rule = self.get_retention_rule(document_type)
        if rule:
            retention_end = document_date + rule.retention_period
            return datetime.now() <= retention_end
        return True  # Default to retain if no rule found

    def get_action(self, document_type: DocumentType, document_date: datetime) -> DocumentAction:
        if not self.should_retain(document_type, document_date):
            return DocumentAction.SHRED
        return self.get_retention_rule(document_type).action