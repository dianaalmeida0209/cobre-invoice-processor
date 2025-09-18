# src/workflows/invoice_workflow.py
"""
Main LangGraph workflow that orchestrates invoice processing
"""
import time
from typing import Dict, Any
from langgraph.graph import StateGraph, END

from ..models.state import EnhancedProcessingState
from ..models.metrics import ProcessingMetrics
from ..config.policies import ApprovalPolicies
from ..config.settings import get_settings
from ..processors.format_detector import FormatDetector
from ..processors.data_extractor import DataExtractor
from ..processors.risk_validator import RiskValidator
from ..processors.approval_router import ApprovalRouter
from ..processors.output_generator import OutputGenerator
from ..utils.logger import get_logger

logger = get_logger(__name__)

class InvoiceWorkflow:
    """
    Main workflow class that orchestrates the entire invoice processing pipeline
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.policies = ApprovalPolicies()
        self.metrics = ProcessingMetrics()
        
        # Initialize all processors 
        self.format_detector = FormatDetector(enable_caching=self.settings.enable_caching)
        self.data_extractor = DataExtractor(metrics=self.metrics)
        self.risk_validator = RiskValidator(policies=self.policies, metrics=self.metrics)
        self.approval_router = ApprovalRouter(policies=self.policies, metrics=self.metrics)
        self.output_generator = OutputGenerator(policies=self.policies)
        
        # Create and compile workflow
        self.workflow = self._create_workflow()
        
        logger.info("InvoiceWorkflow initialized successfully with all processors")
    
    def _create_workflow(self) -> Any:
        """
        Create and configure the LangGraph workflow 
        """
        logger.info("Creating LangGraph workflow with 5 processing nodes")
        
        # Create state graph
        workflow = StateGraph(EnhancedProcessingState)
        
        # Add processing nodes 
        workflow.add_node("detect_format", self.format_detector.detect_format_and_language)
        workflow.add_node("extract_data", self.data_extractor.extract_data_with_optimization)
        workflow.add_node("validate_risk", self.risk_validator.enhanced_validate_and_score_risk)
        workflow.add_node("route_approval", self.approval_router.intelligent_approval_routing_with_compliance)
        workflow.add_node("generate_output", self.output_generator.generate_enhanced_integration_output)
        
        # Define workflow edges (linear processing )
        workflow.set_entry_point("detect_format")
        workflow.add_edge("detect_format", "extract_data")
        workflow.add_edge("extract_data", "validate_risk")
        workflow.add_edge("validate_risk", "route_approval")
        workflow.add_edge("route_approval", "generate_output")
        workflow.add_edge("generate_output", END)
        
        # Compile workflow
        compiled_workflow = workflow.compile()
        
        logger.info("LangGraph workflow compiled successfully")
        return compiled_workflow
    
    def process_single_invoice(self, invoice_id: int, content: str) -> Dict[str, Any]:
        """
        Process a single invoice through the complete workflow 
        
        Args:
            invoice_id: Unique identifier for the invoice
            content: Raw invoice content (text, email, JSON, etc.)
            
        Returns:
            Complete processing results with enhanced analytics
        """
        logger.info(f"Starting invoice processing workflow for ID {invoice_id}")
        
        # Create initial state 
        initial_state = EnhancedProcessingState(
            invoice_id=invoice_id,
            raw_content=content,
            content_hash="",
            document_type="",
            language="",
            extracted_data={},
            validation_errors=[],
            risk_score=0.0,
            risk_factors={},
            anomalies_detected=[],
            compliance_flags=[],
            approval_decision="",
            processing_status="started",
            final_output={},
            processing_start_time=time.time()
        )
        
        try:
            # Execute workflow
            final_state = self.workflow.invoke(initial_state)
            
            # Update global metrics
            self._update_global_metrics(initial_state["processing_start_time"])
            
            result = final_state["final_output"]
            
            logger.info(
                f"Invoice {invoice_id} processed successfully: "
                f"decision={result.get('approval', {}).get('decision', 'unknown')}, "
                f"risk={result.get('document_metadata', {}).get('risk_score', 0)}"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Critical processing error: {str(e)}"
            logger.error(f"Invoice {invoice_id} processing failed: {error_msg}", exc_info=True)
            
            self.metrics.errors.append(f"Invoice {invoice_id}: {error_msg}")
            
            # Return error response 
            return {
                "invoice_id": invoice_id,
                "processing_timestamp": time.time(),
                "processing_status": "failed",
                "error": error_msg,
                "enhanced_risk_analytics": {"processing_failed": True},
                "integration_ready": {
                    "payment_system": False, 
                    "erp_system": False,
                    "reporting_system": True,
                    "compliance_check": False
                }
            }
    
    def _update_global_metrics(self, start_time: float) -> None:
        """Update global processing metrics"""
        self.metrics.total_processed += 1
        self.metrics.processing_time_total += (time.time() - start_time)
    
    def get_processing_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive processing metrics and statistics 
        """
        return {
            "summary": self.metrics.get_approval_summary(),
            "performance": self.metrics.get_processing_stats(),
            "raw_metrics": {
                "total_processed": self.metrics.total_processed,
                "auto_approved": self.metrics.auto_approved,
                "supervisor_review": self.metrics.supervisor_review,
                "manager_review": self.metrics.manager_review,
                "executive_review": self.metrics.executive_review,
                "rejected": self.metrics.rejected,
                "validation_errors": self.metrics.validation_errors_count,
                "critical_anomalies": self.metrics.critical_anomalies_detected,
                "document_escalations": self.metrics.document_type_escalations,
                "high_risk_scores": self.metrics.high_risk_scores,
                "api_calls_used": self.metrics.api_calls_used,
                "errors": len(self.metrics.errors)
            }
        }
    
    def reset_metrics(self) -> None:
        """Reset all processing metrics (useful for testing)"""
        self.metrics = ProcessingMetrics()
        logger.info("Processing metrics reset")