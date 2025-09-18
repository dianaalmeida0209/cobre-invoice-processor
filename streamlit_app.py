# streamlit_app.py
"""
Cobre Invoice Processing Dashboard
Simple Streamlit interface for invoice processing and analytics
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from datetime import datetime
from typing import Dict, List
import time

# Import your modular workflow
from src.workflows.invoice_workflow import InvoiceWorkflow

# Page configuration
st.set_page_config(
    page_title="Cobre Invoice Processor",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data
def load_sample_results():
    """Load sample results for demonstration"""
    try:
        with open('cobre_enhanced_results_20250917_213113.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def create_approval_distribution_chart(results: List[Dict]):
    """Create approval distribution visualization"""
    if not results:
        return None
    
    # Count approvals by decision
    approval_counts = {}
    for result in results:
        decision = result.get('approval', {}).get('decision', 'unknown')
        approval_counts[decision] = approval_counts.get(decision, 0) + 1
    
    # Create pie chart
    fig = px.pie(
        values=list(approval_counts.values()),
        names=list(approval_counts.keys()),
        title="Invoice Approval Distribution",
        color_discrete_map={
            'auto_approved': '#28a745',
            'supervisor_review': '#ffc107', 
            'manager_review': '#fd7e14',
            'executive_review': '#dc3545',
            'rejected': '#6c757d'
        }
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=400)
    
    return fig

def create_risk_score_distribution(results: List[Dict]):
    """Create risk score distribution histogram"""
    if not results:
        return None
    
    risk_scores = [
        result.get('document_metadata', {}).get('risk_score', 0) 
        for result in results
    ]
    
    fig = px.histogram(
        x=risk_scores,
        nbins=15,
        title="Risk Score Distribution",
        labels={'x': 'Risk Score', 'y': 'Number of Invoices'},
        color_discrete_sequence=['#007bff']
    )
    
    fig.update_layout(height=400)
    return fig

def create_document_type_analysis(results: List[Dict]):
    """Create document type analysis"""
    if not results:
        return None
    
    doc_types = [
        result.get('document_metadata', {}).get('type', 'unknown')
        for result in results
    ]
    
    doc_type_counts = pd.Series(doc_types).value_counts()
    
    fig = px.bar(
        x=doc_type_counts.index,
        y=doc_type_counts.values,
        title="Processing Volume by Document Type",
        labels={'x': 'Document Type', 'y': 'Count'},
        color=doc_type_counts.values,
        color_continuous_scale='Blues'
    )
    
    fig.update_layout(height=400)
    return fig

def display_performance_metrics(results: List[Dict]):
    """Display performance KPIs"""
    if not results:
        st.warning("No data available for metrics")
        return
    
    # Calculate metrics
    total_processed = len(results)
    auto_approved = sum(1 for r in results if r.get('approval', {}).get('decision') == 'auto_approved')
    
    avg_processing_time = sum(
        r.get('processing_time_seconds', 0) for r in results
    ) / total_processed if total_processed > 0 else 0
    
    total_api_calls = sum(
        r.get('audit_trail', {}).get('api_calls_used', 0) for r in results
    )
    
    estimated_cost = total_api_calls * 0.015
    
    validation_errors = sum(
        1 for r in results if not r.get('validation', {}).get('is_valid', True)
    )
    
    # Display metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Processed", 
            total_processed,
            help="Total number of invoices processed"
        )
    
    with col2:
        auto_approval_rate = (auto_approved / total_processed * 100) if total_processed > 0 else 0
        st.metric(
            "Auto-Approval Rate", 
            f"{auto_approval_rate:.1f}%",
            help="Percentage of invoices automatically approved"
        )
    
    with col3:
        st.metric(
            "Avg Processing Time", 
            f"{avg_processing_time:.2f}s",
            help="Average time to process each invoice"
        )
    
    with col4:
        st.metric(
            "Estimated Cost", 
            f"${estimated_cost:.2f}",
            help="Estimated cost based on API usage"
        )
    
    # Second row of metrics
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        throughput = (total_processed / (avg_processing_time * total_processed / 60)) if avg_processing_time > 0 else 0
        st.metric(
            "Throughput", 
            f"{throughput:.1f}/min",
            help="Invoices processed per minute"
        )
    
    with col6:
        error_rate = (validation_errors / total_processed * 100) if total_processed > 0 else 0
        st.metric(
            "Error Rate", 
            f"{error_rate:.1f}%",
            help="Percentage of invoices with validation errors"
        )
    
    with col7:
        st.metric(
            "API Calls", 
            total_api_calls,
            help="Total API calls made to process invoices"
        )
    
    with col8:
        avg_risk_score = sum(
            r.get('document_metadata', {}).get('risk_score', 0) for r in results
        ) / total_processed if total_processed > 0 else 0
        st.metric(
            "Avg Risk Score", 
            f"{avg_risk_score:.3f}",
            help="Average risk score across all invoices"
        )

def process_uploaded_csv(uploaded_file):
    """Process uploaded CSV file"""
    try:
        # Read CSV
        df = pd.read_csv(uploaded_file)
        
        # Validate columns
        if not {'id', 'content'}.issubset(df.columns):
            st.error("CSV must contain 'id' and 'content' columns")
            return None
        
        st.success(f"CSV loaded successfully: {len(df)} invoices found")
        
        # Show preview
        st.subheader("Data Preview")
        st.dataframe(df.head(), use_container_width=True)
        
        # Processing options
        col1, col2 = st.columns(2)
        with col1:
            start_idx = st.number_input("Start Index", 0, len(df)-1, 0)
        with col2:
            end_idx = st.number_input("End Index", start_idx+1, len(df), min(len(df), start_idx+10))
        
        if st.button("🔄 Process Invoices", type="primary"):
            return process_csv_subset(df, start_idx, end_idx)
        
        return None
    
    except Exception as e:
        st.error(f"Error reading CSV: {str(e)}")
        return None

def process_csv_subset(df: pd.DataFrame, start_idx: int, end_idx: int):
    """Process subset of CSV data"""
    subset_df = df.iloc[start_idx:end_idx]
    
    # Initialize workflow
    workflow = InvoiceWorkflow()
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    results = []
    start_time = time.time()
    
    for i, (_, row) in enumerate(subset_df.iterrows()):
        progress = (i + 1) / len(subset_df)
        progress_bar.progress(progress)
        status_text.text(f"Processing invoice {i+1}/{len(subset_df)}: ID {row['id']}")
        
        try:
            result = workflow.process_single_invoice(
                invoice_id=int(row['id']),
                content=row['content']
            )
            results.append(result)
        except Exception as e:
            st.error(f"Error processing invoice {row['id']}: {str(e)}")
    
    processing_time = time.time() - start_time
    
    progress_bar.empty()
    status_text.empty()
    
    st.success(f"Processing completed! {len(results)} invoices processed in {processing_time:.1f}s")
    
    return results

def main():
    # Header
    st.title("🚀 Cobre Invoice Processing Platform")
    st.markdown("**AI-Powered Invoice Processing with Enhanced Risk Analytics**")
    
    # Sidebar
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose Section",
        ["📊 Analytics Dashboard", "📤 Process New Invoices", "⚙️ System Status"]
    )
    
    if page == "📊 Analytics Dashboard":
        show_analytics_dashboard()
    elif page == "📤 Process New Invoices":
        show_processing_interface()
    elif page == "⚙️ System Status":
        show_system_status()

def show_analytics_dashboard():
    """Show main analytics dashboard"""
    st.header("📊 Invoice Processing Analytics")
    
    # Load sample data
    results = load_sample_results()
    
    if not results:
        st.warning("No processing results found. Process some invoices first.")
        st.info("Upload a CSV file in the 'Process New Invoices' section to get started.")
        return
    
    st.info(f"Displaying analytics for {len(results)} processed invoices")
    
    # Performance Metrics
    st.subheader("Performance Metrics")
    display_performance_metrics(results)
    
    # Charts
    st.subheader("Visual Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        approval_chart = create_approval_distribution_chart(results)
        if approval_chart:
            st.plotly_chart(approval_chart, use_container_width=True)
    
    with col2:
        risk_chart = create_risk_score_distribution(results)
        if risk_chart:
            st.plotly_chart(risk_chart, use_container_width=True)
    
    # Document type analysis
    doc_type_chart = create_document_type_analysis(results)
    if doc_type_chart:
        st.plotly_chart(doc_type_chart, use_container_width=True)
    
    # Detailed results table
    st.subheader("Detailed Results")
    
    # Convert to DataFrame for display
    display_data = []
    for result in results:
        display_data.append({
            "Invoice ID": result.get('invoice_id'),
            "Document Type": result.get('document_metadata', {}).get('type', ''),
            "Vendor": result.get('extracted_data', {}).get('proveedor', ''),
            "Amount": result.get('extracted_data', {}).get('monto_total', 0),
            "Currency": result.get('extracted_data', {}).get('moneda', ''),
            "Risk Score": result.get('document_metadata', {}).get('risk_score', 0),
            "Approval Decision": result.get('approval', {}).get('decision', ''),
            "Valid": result.get('validation', {}).get('is_valid', False),
            "Processing Time": f"{result.get('processing_time_seconds', 0):.3f}s"
        })
    
    df_display = pd.DataFrame(display_data)
    st.dataframe(df_display, use_container_width=True)

def show_processing_interface():
    """Show invoice processing interface"""
    st.header("📤 Process New Invoices")
    
    upload_method = st.radio(
        "Choose Upload Method",
        ["CSV File Upload", "Single Invoice Text"]
    )
    
    if upload_method == "CSV File Upload":
        st.subheader("Upload CSV File")
        uploaded_file = st.file_uploader(
            "Choose CSV file",
            type=['csv'],
            help="CSV should have 'id' and 'content' columns"
        )
        
        if uploaded_file:
            results = process_uploaded_csv(uploaded_file)
            
            if results:
                st.subheader("Processing Results")
                display_performance_metrics(results)
                
                # Download results
                results_json = json.dumps(results, indent=2, ensure_ascii=False)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                
                st.download_button(
                    label="📥 Download Results (JSON)",
                    data=results_json,
                    file_name=f"cobre_results_{timestamp}.json",
                    mime="application/json"
                )
    
    else:
        st.subheader("Single Invoice Processing")
        invoice_content = st.text_area(
            "Invoice Content",
            height=200,
            placeholder="Paste your invoice content here..."
        )
        
        if st.button("🔄 Process Invoice", type="primary") and invoice_content.strip():
            with st.spinner("Processing invoice..."):
                workflow = InvoiceWorkflow()
                result = workflow.process_single_invoice(1, invoice_content)
            
            st.success("Invoice processed successfully!")
            
            # Display result
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Extracted Data")
                extracted_data = result.get('extracted_data', {})
                for key, value in extracted_data.items():
                    st.write(f"**{key.replace('_', ' ').title()}:** {value}")
            
            with col2:
                st.subheader("Risk Analysis")
                risk_score = result.get('document_metadata', {}).get('risk_score', 0)
                approval_decision = result.get('approval', {}).get('decision', '')
                
                st.metric("Risk Score", f"{risk_score:.3f}")
                st.write(f"**Approval Decision:** {approval_decision}")
                
                if result.get('validation', {}).get('errors'):
                    st.error("Validation Errors:")
                    for error in result['validation']['errors']:
                        st.write(f"• {error}")

def show_system_status():
    """Show system status and configuration"""
    st.header("⚙️ System Status")
    
    try:
        from src.config.settings import get_settings
        settings = get_settings()
        
        st.subheader("Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Model Configuration:**")
            st.write(f"• Model: {settings.model_name}")
            st.write(f"• Max Tokens: {settings.max_tokens}")
            st.write(f"• Temperature: {settings.temperature}")
            
        with col2:
            st.write("**Processing Configuration:**")
            st.write(f"• Caching Enabled: {settings.enable_caching}")
            st.write(f"• Rate Limit Delay: {settings.rate_limit_delay}s")
            st.write(f"• Max Content Length: {settings.max_content_length}")
        
        st.subheader("Business Rules")
        from src.config.policies import ApprovalPolicies
        policies = ApprovalPolicies()
        
        st.write("**Approval Thresholds:**")
        st.write(f"• Auto Approval: ${policies.AUTO_APPROVAL_USD:,} USD / ${policies.AUTO_APPROVAL_COP:,} COP")
        st.write(f"• Supervisor Max: ${policies.SUPERVISOR_MAX_USD:,} USD / ${policies.SUPERVISOR_MAX_COP:,} COP")
        st.write(f"• Manager Max: ${policies.MANAGER_MAX_USD:,} USD / ${policies.MANAGER_MAX_COP:,} COP")
        
        st.success("✅ System configuration loaded successfully")
        
    except Exception as e:
        st.error(f"❌ Configuration error: {str(e)}")

if __name__ == "__main__":
    main()