# src/models/state.py
"""
State definitions for the invoice processing workflow
"""
from typing import Dict, List, Any, TypedDict

class EnhancedProcessingState(TypedDict):
    """State object passed between LangGraph nodes"""
    invoice_id: int
    raw_content: str
    content_hash: str
    document_type: str
    language: str
    extracted_data: Dict[str, Any]
    validation_errors: List[str]
    
    # Enhanced risk scoring fields
    risk_score: float
    risk_factors: Dict[str, float]
    anomalies_detected: List[str]
    compliance_flags: List[str]
    
    # Workflow control
    approval_decision: str
    processing_status: str
    final_output: Dict[str, Any]
    processing_start_time: float