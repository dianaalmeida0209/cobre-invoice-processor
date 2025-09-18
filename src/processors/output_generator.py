# src/processors/output_generator.py
"""
Enhanced output generation for integration-ready results
"""
import time
from datetime import datetime
from typing import Dict

from ..models.state import EnhancedProcessingState
from ..config.policies import ApprovalPolicies
from ..utils.logger import get_logger

logger = get_logger(__name__)

class OutputGenerator:
    """Generates comprehensive, integration-ready output with enhanced analytics"""
    
    def __init__(self, policies: ApprovalPolicies):
        self.policies = policies
        logger.info("OutputGenerator initialized with enhanced compliance analytics")
    
    def generate_enhanced_integration_output(self, state: EnhancedProcessingState) -> EnhancedProcessingState:
        """
        Generate comprehensive output with enhanced risk analytics and compliance data 
        """
        logger.info(f"Generating output for invoice {state['invoice_id']}")
        
        processing_time = time.time() - state["processing_start_time"]
        
        # Build complete 
        output = {
            # Basic identification and timing
            "invoice_id": state["invoice_id"],
            "content_hash": state.get("content_hash", ""),
            "processing_timestamp": datetime.now().isoformat(),
            "processing_time_seconds": round(processing_time, 3),
            
            # Document metadata with risk score
            "document_metadata": self._build_document_metadata(state),
            
            # Extracted data
            "extracted_data": state["extracted_data"],
            
            # Validation results
            "validation": self._build_validation_section(state),
            
            # Enhanced risk analytics section 
            "enhanced_risk_analytics": self._build_risk_analytics(state),
            
            # Approval decision
            "approval": self._build_approval_section(state),
            
            # Integration readiness flags 
            "integration_ready": self._build_integration_flags(state),
            
            # Comprehensive audit trail 
            "audit_trail": self._build_audit_trail(state)
        }
        
        state["final_output"] = output
        state["processing_status"] = "completed"
        
        logger.info(
            f"Invoice {state['invoice_id']}: output generated successfully, "
            f"decision={state['approval_decision']}, risk={state['risk_score']:.3f}"
        )
        
        return state
    
    def _build_document_metadata(self, state: EnhancedProcessingState) -> Dict:
        """Build document metadata section """
        return {
            "type": state["document_type"],
            "language": state["language"], 
            "processing_status": state["processing_status"],
            "risk_score": round(state["risk_score"], 3)
        }
    
    def _build_validation_section(self, state: EnhancedProcessingState) -> Dict:
        """Build validation results section """
        return {
            "errors": state["validation_errors"],
            "is_valid": len(state["validation_errors"]) == 0,
            "critical_fields_complete": self._check_critical_fields_complete(state)
        }
    
    def _check_critical_fields_complete(self, state: EnhancedProcessingState) -> bool:
        """Check if all critical fields are present and valid """
        data = state["extracted_data"]
        return all(
            data.get(field) and str(data.get(field)).strip() != ""
            for field in self.policies.CRITICAL_FIELDS
        )
    
    def _build_risk_analytics(self, state: EnhancedProcessingState) -> Dict:
        """Build enhanced risk analytics section """
        return {
            "risk_score_breakdown": state.get("risk_factors", {}),
            "anomalies_detected": state.get("anomalies_detected", []),
            "compliance_flags": state.get("compliance_flags", []),
            "document_type_rules_applied": state["document_type"] in self.policies.DOCUMENT_TYPE_RULES
        }
    
    def _build_approval_section(self, state: EnhancedProcessingState) -> Dict:
        """Build approval decision section """
        risk_score = state["risk_score"]
        
        return {
            "decision": state["approval_decision"],
            "requires_human_review": state["approval_decision"] != "auto_approved",
            "risk_level": self._determine_risk_level(risk_score)
        }
    
    def _determine_risk_level(self, risk_score: float) -> str:
        """Determine risk level based on score """
        if risk_score > 0.6:
            return "high"
        elif risk_score > 0.3:
            return "medium"
        else:
            return "low"
    
    def _build_integration_flags(self, state: EnhancedProcessingState) -> Dict:
        """Build integration readiness flags for downstream systems """
        validation_errors = state["validation_errors"]
        risk_score = state["risk_score"]
        compliance_flags = state.get("compliance_flags", [])
        approval_decision = state["approval_decision"]
        
        return {
            "payment_system": approval_decision == "auto_approved",
            "erp_system": len(validation_errors) == 0,
            "reporting_system": True,  # Always ready for reporting
            "compliance_check": risk_score < 0.8 and len(compliance_flags) == 0
        }
    
    def _build_audit_trail(self, state: EnhancedProcessingState) -> Dict:
        """Build comprehensive audit trail """
        return {
            "api_calls_used": 1,  # Single LLM call per invoice
            "vendor_frequency": 1,  # Maintain compatibility
            "processing_node_path": [
                "detect_format", 
                "extract_data", 
                "enhanced_validate_risk", 
                "intelligent_routing_compliance", 
                "generate_enhanced_output"
            ],
            "compliance_version": "2.0",
            "risk_scoring_method": "multifactor_composite",
            "document_type_detected": state["document_type"],
            "language_detected": state["language"]
        }