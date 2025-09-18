# src/models/metrics.py
"""
Metrics and measurement classes for invoice processing
"""
from dataclasses import dataclass, field
from typing import List

@dataclass 
class ProcessingMetrics:
    """Enhanced metrics with anomaly tracking"""
    total_processed: int = 0
    auto_approved: int = 0
    supervisor_review: int = 0
    manager_review: int = 0
    executive_review: int = 0
    rejected: int = 0
    
    # Enhanced anomaly metrics
    validation_errors_count: int = 0
    critical_anomalies_detected: int = 0
    document_type_escalations: int = 0
    high_risk_scores: int = 0
    
    # Performance metrics
    processing_time_total: float = 0.0
    api_calls_used: int = 0
    errors: List[str] = field(default_factory=list)
    
    def get_approval_summary(self) -> dict:
        """Returns approval distribution summary"""
        if self.total_processed == 0:
            return {}
        
        return {
            "auto_approved_pct": round(self.auto_approved / self.total_processed * 100, 1),
            "supervisor_review_pct": round(self.supervisor_review / self.total_processed * 100, 1),
            "manager_review_pct": round(self.manager_review / self.total_processed * 100, 1),
            "executive_review_pct": round(self.executive_review / self.total_processed * 100, 1),
            "rejected_pct": round(self.rejected / self.total_processed * 100, 1)
        }
    
    def get_processing_stats(self) -> dict:
        """Returns processing performance stats"""
        if self.total_processed == 0:
            return {}
        
        return {
            "avg_processing_time": round(self.processing_time_total / self.total_processed, 3),
            "throughput_per_minute": round(self.total_processed / (self.processing_time_total / 60), 1),
            "estimated_cost_usd": round(self.api_calls_used * 0.015, 2),
            "error_rate_pct": round(len(self.errors) / self.total_processed * 100, 1)
        }