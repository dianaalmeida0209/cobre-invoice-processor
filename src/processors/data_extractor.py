# src/processors/data_extractor.py
"""
Data extraction processor using LLM
"""
import json
import time
from typing import Dict, Tuple
from langchain_anthropic import ChatAnthropic

from ..models.state import EnhancedProcessingState
from ..models.metrics import ProcessingMetrics
from ..config.settings import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

class DataExtractor:
    """Extracts structured data from invoice content using LLM"""
    
    def __init__(self, metrics: ProcessingMetrics):
        self.metrics = metrics
        self.settings = get_settings()
        
        # Initialize LLM with your API key
        self.llm = ChatAnthropic(
            model_name=self.settings.model_name,
            anthropic_api_key=self.settings.anthropic_api_key,
            max_tokens=self.settings.max_tokens,
            temperature=self.settings.temperature
        )
        
        logger.info("DataExtractor initialized successfully")
    
    def extract_data_with_optimization(self, state: EnhancedProcessingState) -> EnhancedProcessingState:
        """
        Main data extraction function with error handling and optimization
        """
        logger.info(f"Starting data extraction for invoice {state['invoice_id']}")
        
        doc_type = state["document_type"]
        language = state["language"]
        content = state["raw_content"][:self.settings.max_content_length]
        
        # Get appropriate prompt 
        prompt = self._get_extraction_prompt(doc_type, language, content)
        
        try:
            # Apply rate limiting
            if self.settings.rate_limit_delay > 0:
                time.sleep(self.settings.rate_limit_delay)
            
            # Call LLM
            logger.debug(f"Calling LLM for invoice {state['invoice_id']}")
            response = self.llm.invoke(prompt)
            self.metrics.api_calls_used += 1
            
            # Parse response 
            extracted_data = self._parse_llm_response(response.content)
            
            # Update state
            state["extracted_data"] = extracted_data
            state["processing_status"] = "data_extracted"
            
            logger.info(
                f"Invoice {state['invoice_id']}: extraction successful, "
                f"extracted {len(extracted_data)} fields"
            )
                
        except Exception as e:
            error_msg = f"Extraction failed: {str(e)[:100]}"
            logger.error(f"Invoice {state['invoice_id']}: {error_msg}")
            
            state["extracted_data"] = {}
            state["validation_errors"] = [error_msg]
            state["processing_status"] = "extraction_failed"
            self.metrics.errors.append(f"ID {state['invoice_id']}: {error_msg}")
        
        return state
    
    def _get_extraction_prompt(self, doc_type: str, language: str, content: str) -> str:
        """
        Get appropriate extraction prompt based on document type and language
        
        """
        # extraction prompts
        extraction_prompts = {
            ("formal_invoice", "spanish"): f"""Factura formal española. Extrae JSON:
{content}
Retorna: {{"numero_factura":"","proveedor":"","monto_total":0,"moneda":"","fecha":"YYYY-MM-DD"}}""",
            
            ("email", "english"): f"""Email invoice. Extract JSON:
{content}
Return: {{"numero_factura":"","proveedor":"","monto_total":0,"moneda":"","fecha":"YYYY-MM-DD"}}""",
            
            ("credit_note", "spanish"): f"""Nota de crédito. Extrae JSON:
{content}
Formato: {{"numero_factura":"","proveedor":"","monto_total":0,"moneda":"","fecha":"YYYY-MM-DD"}}""",
            
            ("json", "english"): f"""JSON invoice normalization:
{content}
Format: {{"numero_factura":"","proveedor":"","monto_total":0,"moneda":"","fecha":"YYYY-MM-DD"}}"""
        }
        
        prompt_key = (doc_type, language)
        if prompt_key in extraction_prompts:
            return extraction_prompts[prompt_key]
        else:
            return f"""Extract invoice data JSON:
{content}
Format: {{"numero_factura":"","proveedor":"","monto_total":0,"moneda":"","fecha":"YYYY-MM-DD"}}"""
    
    def _parse_llm_response(self, response_content: str) -> Dict:
        """
        Parse LLM response and extract JSON data 
        """
        json_str = response_content.strip()
        
        # Remove code blocks if present
        if json_str.startswith('```json'):
            json_str = json_str[7:-3]
        elif json_str.startswith('```'):
            json_str = json_str[3:-3]
        
        # Parse JSON
        try:
            extracted = json.loads(json_str)
            return extracted
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed: {e}")
            # Fallback to regex patterns
            return self._fallback_extraction(response_content)
    
    def _fallback_extraction(self, content: str) -> Dict:
        """
        Fallback extraction using regex patterns when JSON parsing fails
        """
        import re
        
        extracted = {
            "numero_factura": "",
            "proveedor": "",
            "monto_total": 0,
            "moneda": "",
            "fecha": ""
        }
        
        # Basic regex patterns for fallback
        patterns = {
            "numero_factura": r'(?:factura|invoice|number)[\s:]*([A-Z0-9\-]+)',
            "monto_total": r'(?:total|amount)[\s:]*[\$]?([0-9,\.]+)',
            "moneda": r'(USD|COP|EUR|MXN)',
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if field == "monto_total":
                    try:
                        extracted[field] = float(value.replace(',', ''))
                    except ValueError:
                        extracted[field] = 0
                else:
                    extracted[field] = value
        
        logger.warning("Used fallback extraction method")
        return extracted