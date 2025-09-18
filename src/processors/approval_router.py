# src/processors/approval_router.py
"""
Intelligent approval routing processor with compliance rules
"""
from typing import Tuple

from ..models.state import EnhancedProcessingState
from ..models.metrics import ProcessingMetrics
from ..config.policies import ApprovalPolicies
from ..utils.logger import get_logger

logger = get_logger(__name__)

class ApprovalRouter:
    """Routes invoices through intelligent approval workflows"""
    
    def __init__(self, policies: ApprovalPolicies, metrics: ProcessingMetrics):
        self.policies = policies
        self.metrics = metrics
        logger.info("ApprovalRouter initialized with enhanced compliance rules")
    
    def intelligent_approval_routing_with_compliance(self, state: EnhancedProcessingState) -> EnhancedProcessingState:
        """
        Main routing function with enhanced compliance and document-specific rules 
        """
        logger.info(f"Starting approval routing for invoice {state['invoice_id']}")
        
        data = state["extracted_data"]
        errors = state["validation_errors"]
        risk_score = state["risk_score"]
        doc_type = state["document_type"]
        
        # Route based on business rules 
        decision, reason = self._determine_approval_decision(
            data, errors, risk_score, doc_type
        )
        
        # Update state
        state["approval_decision"] = decision
        state["processing_status"] = "routed"
        
        # Update metrics
        self._update_approval_metrics(decision)
        
        logger.info(
            f"Invoice {state['invoice_id']}: routed to {decision}, "
            f"reason: {reason[:50]}..."
        )
        
        return state
    
    def _determine_approval_decision(self, data: dict, errors: list, 
                                   risk_score: float, doc_type: str) -> Tuple[str, str]:
        """
        Determine approval decision based on comprehensive business rules 
        """
        # Rule 1: Automatic rejection for critical errors 
        if self._should_reject_for_critical_errors(errors, risk_score):
            if errors and any(self.policies.is_critical_anomaly(error.lower()) for error in errors):
                return "rejected", f"Critical errors detected: {len(errors)} - Compliance violation"
            else:
                return "rejected", f"Risk score too high ({risk_score:.2f}) - Auto-rejected"
        
        # Rule 2: Apply document-specific routing logic 
        try:
            monto_cop, monto_usd = self._normalize_amounts(data)
            return self._route_by_document_type(doc_type, monto_cop, monto_usd, risk_score, errors)
            
        except Exception as e:
            error_msg = f"Routing error: {str(e)[:50]}"
            self.metrics.errors.append(f"Routing error: {e}")
            return "manual_review", error_msg
    
    def _should_reject_for_critical_errors(self, errors: list, risk_score: float) -> bool:
        """Check if invoice should be automatically rejected """
        critical_errors_detected = any(
            self.policies.is_critical_anomaly(error.lower()) for error in errors
        )
        return (errors and critical_errors_detected) or risk_score >= 0.8
    
    def _normalize_amounts(self, data: dict) -> Tuple[float, float]:
        """Normalize amounts to both COP and USD"""
        monto_str = str(data.get("monto_total", "0")).replace(",", "").replace("$", "")
        monto = float(monto_str)
        currency = data.get("moneda", "").upper()
        
        if currency == "USD":
            monto_cop = monto * self.policies.COP_USD_RATE
            monto_usd = monto
        else:
            monto_cop = monto
            monto_usd = monto / self.policies.COP_USD_RATE
            
        return monto_cop, monto_usd
    
    def _route_by_document_type(self, doc_type: str, monto_cop: float, monto_usd: float, 
                               risk_score: float, errors: list) -> Tuple[str, str]:
        """Route based on document type specific rules """
        
        doc_rules = self.policies.get_document_rules(doc_type)
        
        if doc_type == 'credit_note':
            return self._route_credit_note(monto_cop, doc_rules)
            
        elif doc_type == 'email':
            return self._route_email(monto_cop, risk_score, errors, doc_rules)
            
        elif doc_type == 'formal_invoice':
            return self._route_formal_invoice(monto_cop, monto_usd, risk_score, errors)
            
        else:
            return self._route_other_document(doc_type, monto_cop, risk_score, doc_rules)
    
    def _route_credit_note(self, monto_cop: float, doc_rules: dict) -> Tuple[str, str]:
        """Credit notes never auto-approve """
        if monto_cop <= self.policies.SUPERVISOR_MAX_COP:
            self.metrics.document_type_escalations += 1
            return "manager_review", "Credit note - Requires management review by policy"
        else:
            return "executive_review", "High-amount credit note - Requires executive approval"
    
    def _route_email(self, monto_cop: float, risk_score: float, errors: list, 
                    doc_rules: dict) -> Tuple[str, str]:
        """Email invoices are more restrictive """
        if (monto_cop <= doc_rules['max_auto_approval'] and 
            risk_score < 0.2 and len(errors) == 0):
            return "supervisor_review", "Email - Requires minimum supervision"
        elif monto_cop <= self.policies.SUPERVISOR_MAX_COP:
            self.metrics.document_type_escalations += 1
            return "manager_review", "Medium-amount email - Escalated by document type"
        else:
            return "executive_review", "High-amount email - Maximum review required"
    
    def _route_formal_invoice(self, monto_cop: float, monto_usd: float, 
                             risk_score: float, errors: list) -> Tuple[str, str]:
        """Formal invoices follow standard logic """
        if (monto_cop <= self.policies.AUTO_APPROVAL_COP and 
            monto_usd <= self.policies.AUTO_APPROVAL_USD and
            risk_score < 0.3 and len(errors) == 0):
            
            return "auto_approved", "Formal invoice, low amount, acceptable risk score"
            
        elif (monto_cop <= self.policies.SUPERVISOR_MAX_COP and 
              monto_usd <= self.policies.SUPERVISOR_MAX_USD):
            return "supervisor_review", "Formal invoice, medium amount"
            
        elif (monto_cop <= self.policies.MANAGER_MAX_COP and 
              monto_usd <= self.policies.MANAGER_MAX_USD):
            return "manager_review", "Formal invoice, high amount"
        else:
            return "executive_review", "Formal invoice, very high amount"
    
    def _route_other_document(self, doc_type: str, monto_cop: float, 
                             risk_score: float, doc_rules: dict) -> Tuple[str, str]:
        """Route JSON and other document types """
        if monto_cop <= doc_rules['max_auto_approval'] and risk_score < 0.25:
            return "supervisor_review", f"Document {doc_type} - Supervision by precaution"
        elif monto_cop <= self.policies.MANAGER_MAX_COP:
            self.metrics.document_type_escalations += 1
            return "manager_review", f"Document {doc_type} - Amount requires management"
        else:
            return "executive_review", f"Document {doc_type} - High amount requires executives"
    
    def _update_approval_metrics(self, decision: str) -> None:
        """Update approval metrics based on decision """
        if decision == "auto_approved":
            self.metrics.auto_approved += 1
        elif decision == "supervisor_review":
            self.metrics.supervisor_review += 1  
        elif decision == "manager_review":
            self.metrics.manager_review += 1
        elif decision == "executive_review":
            self.metrics.executive_review += 1
        elif decision == "rejected":
            self.metrics.rejected += 1