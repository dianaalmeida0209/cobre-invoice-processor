# src/processors/risk_validator.py
"""
Risk validation and scoring processor
"""
from datetime import datetime
from typing import Dict, List, Tuple

from ..models.state import EnhancedProcessingState
from ..models.metrics import ProcessingMetrics
from ..config.policies import ApprovalPolicies
from ..utils.logger import get_logger

logger = get_logger(__name__)

class RiskValidator:
    """Validates invoice data and calculates multi-factor risk scores"""
    
    def __init__(self, policies: ApprovalPolicies, metrics: ProcessingMetrics):
        self.policies = policies
        self.metrics = metrics
        logger.info("RiskValidator initialized with enhanced scoring")
    
    def enhanced_validate_and_score_risk(self, state: EnhancedProcessingState) -> EnhancedProcessingState:
        """
        Main validation function with enhanced risk scoring 
        """
        logger.info(f"Starting risk validation for invoice {state['invoice_id']}")
        
        data = state["extracted_data"]
        errors = []
        anomalies = []
        compliance_flags = []
        
        # 1. Critical fields validation 
        self._validate_critical_fields(data, errors, anomalies)
        
        # 2. Amount validation and normalization 
        monto_normalized, amount_risk = self._validate_amount(data, errors, anomalies, compliance_flags)
        
        # 3. Date validation 
        self._validate_date(data, errors, compliance_flags)
        
        # 4. Calculate composite risk score 
        risk_factors = self._calculate_risk_factors(
            state, errors, amount_risk, data
        )
        
        final_risk_score = self._calculate_final_risk_score(risk_factors)
        
        # 5. Detect critical anomalies
        self._detect_critical_anomalies(anomalies, compliance_flags)
        
        # Update state
        state["validation_errors"] = errors
        state["risk_score"] = min(final_risk_score, 1.0)
        state["risk_factors"] = risk_factors
        state["anomalies_detected"] = anomalies
        state["compliance_flags"] = compliance_flags
        state["processing_status"] = "validated" if not errors else "validation_failed"
        
        # Update metrics
        self._update_metrics(errors, final_risk_score)
        
        logger.info(
            f"Invoice {state['invoice_id']}: validation completed, "
            f"risk_score={final_risk_score:.3f}, errors={len(errors)}"
        )
        
        return state
    
    def _validate_critical_fields(self, data: Dict, errors: List, anomalies: List) -> None:
        """Validate presence of critical fields """
        for field in self.policies.CRITICAL_FIELDS:
            if not data.get(field) or str(data.get(field)).strip() == "":
                error_msg = f"{field.replace('_', ' ').title()} faltante"
                errors.append(error_msg)
                anomalies.append(error_msg.lower())
    
    def _validate_amount(self, data: Dict, errors: List, anomalies: List, 
                        compliance_flags: List) -> Tuple[float, float]:
        """Validate and normalize amount, return normalized amount and risk score """
        monto_normalized = 0
        amount_risk = 0.0
        
        try:
            monto_str = str(data.get("monto_total", "0")).replace(",", "").replace("$", "")
            monto = float(monto_str)
            
            if monto <= 0:
                errors.append("Monto inválido o cero")
                anomalies.append("monto inválido o cero")
                amount_risk = 0.8
            else:
                currency = data.get("moneda", "").upper()
                if currency == "USD":
                    monto_normalized = monto * self.policies.COP_USD_RATE
                elif currency == "COP":
                    monto_normalized = monto
                else:
                    monto_normalized = monto
                    compliance_flags.append("Moneda no especificada")
                    
                # Calculate risk based on amount thresholds 
                if monto_normalized > self.policies.MANAGER_MAX_COP:
                    amount_risk = 0.3
                elif monto_normalized > self.policies.SUPERVISOR_MAX_COP:
                    amount_risk = 0.2
                else:
                    amount_risk = 0.1
                    
        except ValueError:
            errors.append("Monto no numérico")
            anomalies.append("monto no numérico")
            amount_risk = 0.7
        
        return monto_normalized, amount_risk
    
    def _validate_date(self, data: Dict, errors: List, compliance_flags: List) -> None:
        """Validate date format and content """
        fecha = data.get("fecha")
        if fecha and str(fecha).strip():
            try:
                fecha_formats = ['%Y-%m-%d', '%d/%m/%Y', '%Y-%m', '%m/%Y']
                parsed_date = None
                
                for fmt in fecha_formats:
                    try:
                        parsed_date = datetime.strptime(str(fecha)[:10], fmt)
                        break
                    except ValueError:
                        continue
                
                if not parsed_date:
                    errors.append("Formato de fecha inválido")
                    compliance_flags.append("Fecha con formato irregular")
                    
            except Exception:
                errors.append("Fecha no procesable")
                compliance_flags.append("Fecha corrupta")
    
    def _calculate_risk_factors(self, state: EnhancedProcessingState, errors: List, 
                               amount_risk: float, data: Dict) -> Dict[str, float]:
        """Calculate individual risk factor scores """
        risk_factors = {}
        
        # Factor 1: Validation errors (40% weight)
        validation_risk = min(len(errors) * 0.25, 1.0)
        risk_factors['validation_errors'] = validation_risk
        
        # Factor 2: Document type (20% weight)  
        doc_type = state["document_type"]
        doc_rules = self.policies.get_document_rules(doc_type)
        document_risk = (doc_rules['risk_multiplier'] - 1.0) * 2  # Normalize to 0-1
        risk_factors['document_type'] = document_risk
        
        # Factor 3: Amount threshold (20% weight)
        risk_factors['amount_threshold'] = amount_risk
        
        # Factor 4: Data completeness (20% weight)
        total_fields = len(self.policies.CRITICAL_FIELDS)
        complete_fields = sum(
            1 for field in self.policies.CRITICAL_FIELDS 
            if data.get(field) and str(data.get(field)).strip()
        )
        completeness_risk = 1.0 - (complete_fields / total_fields) if total_fields > 0 else 0.0
        risk_factors['data_completeness'] = completeness_risk
        
        return risk_factors
    
    def _calculate_final_risk_score(self, risk_factors: Dict[str, float]) -> float:
        """Calculate weighted final risk score """
        final_risk_score = (
            risk_factors['validation_errors'] * self.policies.RISK_FACTORS['validation_errors'] +
            risk_factors['document_type'] * self.policies.RISK_FACTORS['document_type'] +
            risk_factors['amount_threshold'] * self.policies.RISK_FACTORS['amount_threshold'] +
            risk_factors['data_completeness'] * self.policies.RISK_FACTORS['data_completeness']
        )
        
        return final_risk_score
    
    def _detect_critical_anomalies(self, anomalies: List, compliance_flags: List) -> None:
        """Detect and flag critical anomalies """
        critical_anomalies = [
            anom for anom in anomalies 
            if self.policies.is_critical_anomaly(anom)
        ]
        
        if critical_anomalies:
            self.metrics.critical_anomalies_detected += 1
            compliance_flags.append("Anomalías críticas detectadas")
    
    def _update_metrics(self, errors: List, final_risk_score: float) -> None:
        """Update processing metrics """
        if errors:
            self.metrics.validation_errors_count += 1
        if final_risk_score > 0.7:
            self.metrics.high_risk_scores += 1