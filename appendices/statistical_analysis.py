"""
 Umbrales de Aprobación 
Análisis cuantitativo de los datos procesados para establecer políticas basadas en sample
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
from collections import Counter


def load_processed_data():
    """Cargar los datos ya procesados por el sistema"""
    try:
        # Usar el archivo más reciente de resultados
        with open('cobre_complete_results_20250917_110238.json', 'r', encoding='utf-8') as f:
            processed_data = json.load(f)
        print(f"Cargados {len(processed_data)} registros procesados")
        return processed_data
    except FileNotFoundError:
        print("Error: No se encontraron los resultados procesados")
        return []

def normalize_amounts_to_cop(data):
    """Normalizar todos los montos a COP para comparación uniforme"""
    COP_USD_RATE = 4200
    normalized_amounts = []
    amount_details = []
    
    for record in data:
        extracted = record.get('extracted_data', {})
        if not extracted:
            continue
            
        try:
            monto = float(extracted.get('monto_total', 0))
            currency = extracted.get('moneda', '').upper()
            
            if currency == 'USD':
                monto_cop = monto * COP_USD_RATE
            else:
                monto_cop = monto
            
            if monto_cop > 0:  # Solo montos válidos
                normalized_amounts.append(monto_cop)
                amount_details.append({
                    'invoice_id': record['invoice_id'],
                    'original_amount': monto,
                    'currency': currency,
                    'cop_normalized': monto_cop,
                    'vendor': extracted.get('proveedor', 'Unknown')
                })
                
        except (ValueError, TypeError):
            continue
    
    return normalized_amounts, amount_details

def calculate_statistical_thresholds(amounts):
    """Calcular percentiles para establecer umbrales estadísticamente fundamentados"""
    amounts_array = np.array(amounts)
    
    percentiles = {
        'P10': np.percentile(amounts_array, 10),
        'P25': np.percentile(amounts_array, 25),
        'P50': np.percentile(amounts_array, 50),  # Mediana
        'P75': np.percentile(amounts_array, 75),
        'P90': np.percentile(amounts_array, 90),
        'P95': np.percentile(amounts_array, 95),
        'P99': np.percentile(amounts_array, 99)
    }
    
    stats = {
        'count': len(amounts),
        'mean': np.mean(amounts_array),
        'median': np.median(amounts_array),
        'std': np.std(amounts_array),
        'min': np.min(amounts_array),
        'max': np.max(amounts_array)
    }
    
    return percentiles, stats

def analyze_vendor_patterns(amount_details):
    """Analizar patrones de vendors para identificar confiables"""
    vendor_stats = {}
    
    for detail in amount_details:
        vendor = detail['vendor'].lower()
        if vendor not in vendor_stats:
            vendor_stats[vendor] = {
                'count': 0,
                'amounts': [],
                'avg_amount': 0,
                'currencies': []
            }
        
        vendor_stats[vendor]['count'] += 1
        vendor_stats[vendor]['amounts'].append(detail['cop_normalized'])
        vendor_stats[vendor]['currencies'].append(detail['currency'])
    
    # Calcular promedios
    for vendor in vendor_stats:
        amounts = vendor_stats[vendor]['amounts']
        vendor_stats[vendor]['avg_amount'] = np.mean(amounts)
        vendor_stats[vendor]['total_volume'] = np.sum(amounts)
        vendor_stats[vendor]['std'] = np.std(amounts) if len(amounts) > 1 else 0
    
    return vendor_stats

def generate_risk_based_thresholds(percentiles, stats, vendor_stats):
    """Generar umbrales basados en análisis de riesgo y distribución"""
    
    # Estrategia: Distributir facturas en 4 niveles de aprobación
    recommendations = {
        'conservative': {
            'auto_approval_cop': int(percentiles['P10']),  # 10% más bajo - muy conservador
            'supervisor_max_cop': int(percentiles['P25']), # Hasta 25%
            'manager_max_cop': int(percentiles['P75']),    # Hasta 75%
            'executive_threshold': int(percentiles['P75']) + 1,
            'description': "Muy conservador - solo 10% auto-aprobación"
        },
        'balanced': {
            'auto_approval_cop': int(percentiles['P25']),  # 25% auto-aprobación
            'supervisor_max_cop': int(percentiles['P50']), # Hasta mediana
            'manager_max_cop': int(percentiles['P90']),    # Hasta 90%
            'executive_threshold': int(percentiles['P90']) + 1,
            'description': "Balanceado - 25% auto-aprobación"
        },
        'aggressive': {
            'auto_approval_cop': int(percentiles['P50']),  # 50% auto-aprobación
            'supervisor_max_cop': int(percentiles['P75']), # Hasta 75%
            'manager_max_cop': int(percentiles['P95']),    # Hasta 95%
            'executive_threshold': int(percentiles['P95']) + 1,
            'description': "Agresivo - 50% auto-aprobación"
        }
    }
    
    # Ajustar por vendors confiables
    frequent_vendors = [vendor for vendor, data in vendor_stats.items() 
                       if data['count'] >= 2 and data['std'] < stats['mean']]
    
    return recommendations, frequent_vendors

def generate_approval_simulation(amounts, amount_details, thresholds, trusted_vendors):
    """Simular aprobaciones con diferentes umbrales"""
    simulation_results = {}
    
    for strategy_name, strategy in thresholds.items():
        auto_approved = 0
        supervisor_review = 0
        manager_review = 0
        executive_review = 0
        
        for detail in amount_details:
            amount = detail['cop_normalized']
            vendor = detail['vendor'].lower()
            is_trusted = any(tv in vendor for tv in trusted_vendors)
            
            if amount <= strategy['auto_approval_cop'] and is_trusted:
                auto_approved += 1
            elif amount <= strategy['supervisor_max_cop']:
                supervisor_review += 1
            elif amount <= strategy['manager_max_cop']:
                manager_review += 1
            else:
                executive_review += 1
        
        total = len(amount_details)
        simulation_results[strategy_name] = {
            'auto_approved': auto_approved,
            'auto_approved_pct': (auto_approved / total) * 100,
            'supervisor_review': supervisor_review,
            'supervisor_pct': (supervisor_review / total) * 100,
            'manager_review': manager_review,
            'manager_pct': (manager_review / total) * 100,
            'executive_review': executive_review,
            'executive_pct': (executive_review / total) * 100,
        }
    
    return simulation_results

def main():
    print("="*70)
    print("ANÁLISIS ESTADÍSTICO REAL - UMBRALES DE APROBACIÓN COBRE")
    print("="*70)
    
    # 1. Cargar datos procesados
    processed_data = load_processed_data()
    if not processed_data:
        return
    
    # 2. Normalizar montos a COP
    print("\n📊 NORMALIZANDO MONTOS...")
    amounts, amount_details = normalize_amounts_to_cop(processed_data)
    print(f"Facturas con montos válidos: {len(amounts)}/{len(processed_data)}")
    
    # 3. Análisis estadístico
    print("\n📈 CALCULANDO ESTADÍSTICAS...")
    percentiles, stats = calculate_statistical_thresholds(amounts)
    
    print(f"\nESTADÍSTICAS DESCRIPTIVAS:")
    print(f"  Facturas válidas: {stats['count']}")
    print(f"  Media: ${stats['mean']:,.0f} COP")
    print(f"  Mediana: ${stats['median']:,.0f} COP")
    print(f"  Desv. Estándar: ${stats['std']:,.0f} COP")
    print(f"  Rango: ${stats['min']:,.0f} - ${stats['max']:,.0f} COP")
    
    print(f"\nPERCENTILES:")
    for p, value in percentiles.items():
        print(f"  {p}: ${value:,.0f} COP (${value/4200:,.0f} USD)")
    
    # 4. Análisis de vendors
    print("\n🏢 ANALIZANDO PATRONES DE VENDORS...")
    vendor_stats = analyze_vendor_patterns(amount_details)
    
    print(f"Vendors únicos encontrados: {len(vendor_stats)}")
    top_vendors = sorted(vendor_stats.items(), 
                        key=lambda x: x[1]['total_volume'], reverse=True)[:10]
    
    print("\nTop 10 vendors por volumen:")
    for vendor, data in top_vendors:
        print(f"  {vendor}: {data['count']} facturas, ${data['total_volume']:,.0f} COP total")
    
    # 5. Generar recomendaciones de umbrales
    print("\n🎯 GENERANDO UMBRALES RECOMENDADOS...")
    threshold_strategies, trusted_vendors = generate_risk_based_thresholds(
        percentiles, stats, vendor_stats
    )
    
    print(f"\nVendors confiables identificados: {len(trusted_vendors)}")
    print(f"  {trusted_vendors}")
    
    # 6. Simular aprobaciones
    print("\n🔄 SIMULANDO APROBACIONES...")
    simulation_results = generate_approval_simulation(
        amounts, amount_details, threshold_strategies, trusted_vendors
    )
    
    print(f"\nRESULTADOS DE SIMULACIÓN:")
    print("-" * 80)
    for strategy, results in simulation_results.items():
        print(f"\n{strategy.upper()}: {threshold_strategies[strategy]['description']}")
        print(f"  Auto-aprobadas: {results['auto_approved']} ({results['auto_approved_pct']:.1f}%)")
        print(f"  Supervisión: {results['supervisor_review']} ({results['supervisor_pct']:.1f}%)")
        print(f"  Gerencia: {results['manager_review']} ({results['manager_pct']:.1f}%)")
        print(f"  Ejecutivos: {results['executive_review']} ({results['executive_pct']:.1f}%)")
    
    # 7. Recomendación final
    print("\n" + "="*70)
    print("🎯 RECOMENDACIÓN PARA COBRE")
    print("="*70)
    
    recommended_strategy = 'balanced'  # Mejor balance para startup fintech
    recommended = threshold_strategies[recommended_strategy]
    
    print(f"\nESTRATEGIA RECOMENDADA: {recommended_strategy.upper()}")
    print(f"Descripción: {recommended['description']}")
    print(f"\nUMBRALES RECOMENDADOS:")
    print(f"  AUTO_APPROVAL_COP = {recommended['auto_approval_cop']:,}")
    print(f"  SUPERVISOR_MAX_COP = {recommended['supervisor_max_cop']:,}")
    print(f"  MANAGER_MAX_COP = {recommended['manager_max_cop']:,}")
    print(f"  EXECUTIVE_THRESHOLD = {recommended['executive_threshold']:,}")
    
    # Equivalentes en USD
    print(f"\nEQUIVALENTES USD (tasa: 1 USD = 4,200 COP):")
    print(f"  AUTO_APPROVAL_USD = {recommended['auto_approval_cop']/4200:,.0f}")
    print(f"  SUPERVISOR_MAX_USD = {recommended['supervisor_max_cop']/4200:,.0f}")
    print(f"  MANAGER_MAX_USD = {recommended['manager_max_cop']/4200:,.0f}")
    
    # Justificación
    print(f"\n📋 JUSTIFICACIÓN:")
    expected_results = simulation_results[recommended_strategy]
    print(f"  - {expected_results['auto_approved_pct']:.1f}% auto-aprobación (apropiado para fintech startup)")
    print(f"  - {expected_results['supervisor_pct'] + expected_results['manager_pct']:.1f}% revisión humana (control de riesgo)")
    print(f"  - {expected_results['executive_pct']:.1f}% escalación ejecutiva (decisiones estratégicas)")
    
    # Guardar resultados
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f"threshold_analysis_{timestamp}.json"
    
    analysis_results = {
        'analysis_date': datetime.now().isoformat(),
        'data_source': 'cobre_complete_results_20250917_110238.json',
        'statistics': {
            'percentiles': {k: float(v) for k, v in percentiles.items()},
            'descriptive': {k: float(v) for k, v in stats.items()}
        },
        'recommended_thresholds': recommended,
        'simulation_results': simulation_results,
        'trusted_vendors': trusted_vendors,
        'vendor_analysis': {k: {
            'count': v['count'],
            'avg_amount': float(v['avg_amount']),
            'total_volume': float(v['total_volume'])
        } for k, v in vendor_stats.items()}
    }
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Análisis detallado guardado en: {results_file}")
    print(f"\n🚀 Estos umbrales pueden implementarse en scalable_invoice_processor.py")

if __name__ == "__main__":
    main()