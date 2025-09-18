# src/config/policies.py
"""
Business rules and approval policies for invoice processing
"""
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class ApprovalPolicies:
    """Enhanced approval policies with multi-factor risk scoring"""
    
    # Basic approval thresholds 
    AUTO_APPROVAL_COP: int = 18_417_000     
    AUTO_APPROVAL_USD: int = 4_385          
    SUPERVISOR_MAX_COP: int = 47_329_800    
    SUPERVISOR_MAX_USD: int = 11_269        
    MANAGER_MAX_COP: int = 190_680_000      
    MANAGER_MAX_USD: int = 45_400           
    
    # Exchange rate
    COP_USD_RATE: int = 4200
    
    # Critical fields for validation
    CRITICAL_FIELDS: List[str] = None
    
    # Document type specific rules 
    DOCUMENT_TYPE_RULES: Dict[str, Dict] = None
    
    # Risk scoring factors (weights) 
    RISK_FACTORS: Dict[str, float] = None
    
    # Critical anomalies that force rejection
    CRITICAL_ANOMALIES: List[str] = None
    
    def __post_init__(self):
        if self.CRITICAL_FIELDS is None:
            self.CRITICAL_FIELDS = ["numero_factura", "proveedor", "monto_total"]
        
        if self.DOCUMENT_TYPE_RULES is None:
            self.DOCUMENT_TYPE_RULES = {
                'credit_note': {
                    'max_auto_approval': 0,  # Never auto-approve credit notes
                    'min_approval_level': 'manager_review',
                    'risk_multiplier': 1.3
                },
                'email': {
                    'max_auto_approval': self.AUTO_APPROVAL_COP * 0.7,  # More restrictive
                    'min_approval_level': 'supervisor_review',
                    'risk_multiplier': 1.2
                },
                'json': {
                    'max_auto_approval': self.AUTO_APPROVAL_COP * 0.8,
                    'min_approval_level': 'supervisor_review', 
                    'risk_multiplier': 1.1
                },
                'formal_invoice': {
                    'max_auto_approval': self.AUTO_APPROVAL_COP,  # Full value
                    'min_approval_level': 'auto_approved',
                    'risk_multiplier': 1.0
                }
            }
        
        if self.RISK_FACTORS is None:
            self.RISK_FACTORS = {
                'validation_errors': 0.4,      # 40% weight for errors
                'document_type': 0.2,          # 20% for document type
                'amount_threshold': 0.2,       # 20% for amount
                'data_completeness': 0.2       # 20% for data completeness
            }
        
        if self.CRITICAL_ANOMALIES is None:
            self.CRITICAL_ANOMALIES = [
                "numero_factura faltante",
                "proveedor faltante", 
                "monto_total faltante",
                "monto inválido o cero"
            ]
    
    def get_document_rules(self, doc_type: str) -> Dict:
        """Get rules for specific document type with fallback"""
        return self.DOCUMENT_TYPE_RULES.get(doc_type, {
            'max_auto_approval': self.AUTO_APPROVAL_COP * 0.5,
            'min_approval_level': 'manager_review',
            'risk_multiplier': 1.2
        })
    
    def is_critical_anomaly(self, anomaly: str) -> bool:
        """Check if anomaly is critical"""
        return any(critical in anomaly.lower() for critical in self.CRITICAL_ANOMALIES)