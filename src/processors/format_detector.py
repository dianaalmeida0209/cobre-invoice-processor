# src/processors/format_detector.py
"""
Document format and language detection processor
"""
import hashlib
from typing import List, Tuple
from ..models.state import EnhancedProcessingState
from ..utils.logger import get_logger

logger = get_logger(__name__)

class FormatDetector:
    """Detects document format and language from content"""
    
    def __init__(self, enable_caching: bool = True):
        self.enable_caching = enable_caching
        self.content_cache = {} if enable_caching else None
        
        # Document type detection patterns 
        self.doc_patterns = [
            ("email", ["from:", "to:", "subject:", "@", "sent:", "received:"]),
            ("json", ["{", "}", "invoice", "vendor", '"', "null"]),
            ("credit_note", ["nota de crédito", "credit note", "devolución", "refund", "nc-"]),
            ("formal_invoice", ["factura", "invoice", "nit", "tax id", "ruc", "rfc"])
        ]
        
        # Language detection patterns 
        self.lang_patterns = {
            "spanish": ["factura", "cliente", "proveedor", "fecha", "importe", "nit"],
            "english": ["invoice", "client", "vendor", "date", "amount", "tax"],
            "portuguese": ["fatura", "cliente", "fornecedor", "data", "valor"]
        }
    
    def detect_format_and_language(self, state: EnhancedProcessingState) -> EnhancedProcessingState:
        """
        Main processing function for format and language detection
        """
        logger.info(f"Starting format detection for invoice {state['invoice_id']}")
        
        content = state["raw_content"].lower()
        
        # Handle caching if enabled
        if self.enable_caching:
            content_hash = hashlib.md5(state["raw_content"].encode()).hexdigest()
            state["content_hash"] = content_hash
            
            if content_hash in self.content_cache:
                cached_result = self.content_cache[content_hash]
                state.update(cached_result)
                logger.info(f"Cache hit for invoice {state['invoice_id']}")
                return state
        
        # Detect document type 
        doc_type = self._detect_document_type(content)
        
        # Detect language 
        language = self._detect_language(content)
        
        # Update state
        state["document_type"] = doc_type
        state["language"] = language
        state["processing_status"] = "format_detected"
        
        # Cache result if enabled
        if self.enable_caching:
            cache_data = {
                "document_type": doc_type,
                "language": language,
                "processing_status": "format_detected"
            }
            self.content_cache[content_hash] = cache_data
        
        logger.info(
            f"Invoice {state['invoice_id']}: detected type={doc_type}, language={language}"
        )
        
        return state
    
    def _detect_document_type(self, content: str) -> str:
        """
        Detect document type based on content patterns 
        """
        doc_type = "unknown"
        max_score = 0
        
        for dtype, patterns in self.doc_patterns:
            score = sum(1 for pattern in patterns if pattern in content)
            if score > max_score:
                max_score = score
                doc_type = dtype
        
        return doc_type
    
    def _detect_language(self, content: str) -> str:
        """
        Detect content language based on keyword patterns 
        """
        language = "unknown"
        max_lang_score = 0
        
        for lang, patterns in self.lang_patterns.items():
            score = sum(1 for pattern in patterns if pattern in content)
            if score > max_lang_score:
                max_lang_score = score
                language = lang
        
        return language