#!/usr/bin/env python3
"""
IRS Tax Form Parser - Data Visualization Demo
Creates comprehensive charts and graphs for tax form analysis
"""

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Set style for professional plots
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

def create_sample_data():
    """Create comprehensive sample tax data for visualization"""
    
    # Expanded sample data
    tax_data = {
        'form_id': ['F001', 'F002', 'F003', 'F004', 'F005', 'F006', 'F007', 'F008', 'F009', 'F010'],
        'taxpayer_name': ['John Smith', 'Jane Johnson', 'Robert Davis', 'Maria Garcia', 'David Wilson',
                         'Sarah Brown', 'Michael Lee', 'Lisa Chen', 'James Miller', 'Anna Taylor'],
        'filing_status': ['Single', 'Married Filing Jointly', 'Head of Household', 'Single', 
                         'Married Filing Jointly', 'Single', 'Married Filing Separately', 
                         'Head of Household', 'Single', 'Married Filing Jointly'],
        'wages': [75000, 95000, 68500, 82000, 105000, 58000, 72000, 89000, 63000, 98000],
        'federal_tax_withheld': [8500, 12000, 7200, 9800, 14500, 6200, 8100, 11200, 6800, 13500],
        'tax_year': [2024, 2024, 2024, 2024, 2024, 2024, 2024, 2024, 2024, 2024],
        'state': ['IL', 'IL', 'IL', 'CA', 'CA', 'TX', 'TX', 'NY', 'NY', 'FL'],
        'refund_amount': [1200, 850, 950, 1100, 750, 1300, 1050, 900, 1150, 800],
        'processing_time': [1.2, 1.8, 1.1, 1.5, 2.1, 1.0, 1.4, 1.9, 1.3, 1.7]
    }
    
    return pd.DataFrame(tax_data)

def create_wages_distribution(df):
    """Create wages distribution visualization"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Histogram with KDE
    ax1.hist(df['wages'], bins=8, alpha=0.7, color='skyblue', edgecolor='black')
    ax1.axvline(df['wages'].mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: ${df["wages"].mean():,.0f}')
    ax1.axvline(df['wages'].median(), color='green', linestyle='--', linewidth=2, label=f'Median: ${df["wages"].median():,.0f}')
    ax1.set_xlabel('Annual Wages ($)')
    ax1.set_ylabel('Number of Taxpayers')
    ax1.set_title('Distribution of Annual Wages')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Box plot by filing status
    filing_order = df.groupby('filing_status')['wages'].median().sort_values(ascending=False).index
    sns.boxplot(data=df, y='filing_status', x='wages', order=filing_order, ax=ax2)
    ax2.set_xlabel('Annual Wages ($)')
    ax2.set_ylabel('Filing Status')
    ax2.set_title('Wages Distribution by Filing Status')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('wages_distribution.png', dpi=300, bbox_inches='tight')
    plt.show()

def create_tax_analysis(df):
    """Create tax withholding analysis"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Tax rate calculation
    df['effective_tax_rate'] = (df['federal_tax_withheld'] / df['wages']) * 100
    
    # Scatter plot: Wages vs Tax Withheld
    scatter = ax1.scatter(df['wages'], df['federal_tax_withheld'], 
                         c=df['effective_tax_rate'], cmap='viridis', 
                         s=100, alpha=0.7, edgecolors='black')
    ax1.set_xlabel('Annual Wages ($)')
    ax1.set_ylabel('Federal Tax Withheld ($)')
    ax1.set_title('Tax Withholding vs Wages')
    ax1.grid(True, alpha=0.3)
    
    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax1)
    cbar.set_label('Effective Tax Rate (%)')
    
    # Tax rate by filing status
    avg_tax_rate = df.groupby('filing_status')['effective_tax_rate'].mean().sort_values(ascending=True)
    bars = ax2.bar(range(len(avg_tax_rate)), avg_tax_rate.values, color='lightcoral')
    ax2.set_xlabel('Filing Status')
    ax2.set_ylabel('Average Effective Tax Rate (%)')
    ax2.set_title('Average Tax Rate by Filing Status')
    ax2.set_xticks(range(len(avg_tax_rate)))
    ax2.set_xticklabels(avg_tax_rate.index, rotation=45, ha='right')
    ax2.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{height:.1f}%', ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig('tax_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()

def create_state_analysis(df):
    """Create state-wise analysis"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # State distribution pie chart
    state_counts = df['state'].value_counts()
    colors = plt.cm.Set3(np.linspace(0, 1, len(state_counts)))
    wedges, texts, autotexts = ax1.pie(state_counts.values, labels=state_counts.index, 
                                      autopct='%1.1f%%', colors=colors, startangle=90)
    ax1.set_title('Taxpayers by State')
    
    # Average wages by state
    state_wages = df.groupby('state')['wages'].mean().sort_values(ascending=True)
    bars = ax2.barh(range(len(state_wages)), state_wages.values, color='lightgreen')
    ax2.set_yticks(range(len(state_wages)))
    ax2.set_yticklabels(state_wages.index)
    ax2.set_xlabel('Average Wages ($)')
    ax2.set_title('Average Wages by State')
    ax2.grid(True, alpha=0.3, axis='x')
    
    # Add value labels
    for i, bar in enumerate(bars):
        width = bar.get_width()
        ax2.text(width + 1000, bar.get_y() + bar.get_height()/2,
                f'${width:,.0f}', ha='left', va='center')
    
    plt.tight_layout()
    plt.savefig('state_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()

def create_processing_metrics(df):
    """Create processing performance metrics"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Processing time distribution
    ax1.hist(df['processing_time'], bins=6, alpha=0.7, color='orange', edgecolor='black')
    ax1.axvline(df['processing_time'].mean(), color='red', linestyle='--', linewidth=2, 
                label=f'Mean: {df["processing_time"].mean():.2f}s')
    ax1.set_xlabel('Processing Time (seconds)')
    ax1.set_ylabel('Number of Forms')
    ax1.set_title('Form Processing Time Distribution')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Processing efficiency timeline
    df_sorted = df.sort_values('processing_time')
    cumulative_time = df_sorted['processing_time'].cumsum()
    ax2.plot(range(1, len(df_sorted)+1), cumulative_time, marker='o', linewidth=2, markersize=6)
    ax2.set_xlabel('Number of Forms Processed')
    ax2.set_ylabel('Cumulative Processing Time (seconds)')
    ax2.set_title('Cumulative Processing Performance')
    ax2.grid(True, alpha=0.3)
    
    # Add annotations
    total_time = cumulative_time.iloc[-1]
    avg_time = total_time / len(df_sorted)
    ax2.text(0.7, 0.3, f'Total Time: {total_time:.1f}s\nAvg per Form: {avg_time:.2f}s', 
             transform=ax2.transAxes, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig('processing_metrics.png', dpi=300, bbox_inches='tight')
    plt.show()

def create_refund_analysis(df):
    """Create refund amount analysis"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Refund vs Wages scatter
    ax1.scatter(df['wages'], df['refund_amount'], alpha=0.7, s=100, color='purple')
    
    # Add trend line
    z = np.polyfit(df['wages'], df['refund_amount'], 1)
    p = np.poly1d(z)
    ax1.plot(df['wages'], p(df['wages']), "r--", alpha=0.8, linewidth=2)
    
    ax1.set_xlabel('Annual Wages ($)')
    ax1.set_ylabel('Refund Amount ($)')
    ax1.set_title('Tax Refund vs Annual Wages')
    ax1.grid(True, alpha=0.3)
    
    # Refund distribution by filing status
    sns.violinplot(data=df, x='filing_status', y='refund_amount', ax=ax2)
    ax2.set_xlabel('Filing Status')
    ax2.set_ylabel('Refund Amount ($)')
    ax2.set_title('Refund Distribution by Filing Status')
    ax2.tick_params(axis='x', rotation=45)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('refund_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()

def create_comprehensive_dashboard(df):
    """Create a comprehensive dashboard"""
    fig = plt.figure(figsize=(20, 12))
    
    # Create grid layout
    gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)
    
    # 1. Summary statistics
    ax1 = fig.add_subplot(gs[0, 0])
    stats_text = f"""
    📊 DATASET SUMMARY
    
    Total Forms: {len(df)}
    Avg Wages: ${df['wages'].mean():,.0f}
    Total Tax Withheld: ${df['federal_tax_withheld'].sum():,.0f}
    Avg Processing Time: {df['processing_time'].mean():.2f}s
    Success Rate: 100%
    """
    ax1.text(0.1, 0.5, stats_text, transform=ax1.transAxes, fontsize=12, 
             bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis('off')
    
    # 2. Wages histogram
    ax2 = fig.add_subplot(gs[0, 1:3])
    ax2.hist(df['wages'], bins=8, alpha=0.7, color='skyblue', edgecolor='black')
    ax2.set_title('Wages Distribution')
    ax2.set_xlabel('Annual Wages ($)')
    ax2.set_ylabel('Frequency')
    ax2.grid(True, alpha=0.3)
    
    # 3. Filing status pie
    ax3 = fig.add_subplot(gs[0, 3])
    filing_counts = df['filing_status'].value_counts()
    ax3.pie(filing_counts.values, labels=filing_counts.index, autopct='%1.0f%%', startangle=90)
    ax3.set_title('Filing Status Distribution')
    
    # 4. Tax withholding scatter
    ax4 = fig.add_subplot(gs[1, 0:2])
    scatter = ax4.scatter(df['wages'], df['federal_tax_withheld'], 
                         c=df['refund_amount'], cmap='viridis', s=100, alpha=0.7)
    ax4.set_xlabel('Annual Wages ($)')
    ax4.set_ylabel('Federal Tax Withheld ($)')
    ax4.set_title('Tax Withholding vs Wages (colored by refund)')
    plt.colorbar(scatter, ax=ax4, label='Refund Amount ($)')
    ax4.grid(True, alpha=0.3)
    
    # 5. State analysis
    ax5 = fig.add_subplot(gs[1, 2:4])
    state_wages = df.groupby('state')['wages'].mean()
    bars = ax5.bar(state_wages.index, state_wages.values, color='lightgreen')
    ax5.set_title('Average Wages by State')
    ax5.set_xlabel('State')
    ax5.set_ylabel('Average Wages ($)')
    ax5.grid(True, alpha=0.3)
    
    # 6. Processing performance
    ax6 = fig.add_subplot(gs[2, 0:2])
    ax6.plot(range(1, len(df)+1), df['processing_time'], marker='o', linewidth=2)
    ax6.set_title('Processing Time per Form')
    ax6.set_xlabel('Form Number')
    ax6.set_ylabel('Processing Time (seconds)')
    ax6.grid(True, alpha=0.3)
    
    # 7. Tax rate analysis
    ax7 = fig.add_subplot(gs[2, 2:4])
    df['tax_rate'] = (df['federal_tax_withheld'] / df['wages']) * 100
    avg_rates = df.groupby('filing_status')['tax_rate'].mean()
    bars = ax7.bar(range(len(avg_rates)), avg_rates.values, color='coral')
    ax7.set_title('Average Tax Rate by Filing Status')
    ax7.set_xlabel('Filing Status')
    ax7.set_ylabel('Tax Rate (%)')
    ax7.set_xticks(range(len(avg_rates)))
    ax7.set_xticklabels(avg_rates.index, rotation=45, ha='right')
    ax7.grid(True, alpha=0.3)
    
    plt.suptitle('IRS Tax Form Parser - Comprehensive Data Analysis Dashboard', 
                 fontsize=16, fontweight='bold', y=0.98)
    
    plt.savefig('comprehensive_dashboard.png', dpi=300, bbox_inches='tight')
    plt.show()

def main():
    """Run the complete visualization demo"""
    print("🎨 IRS Tax Form Parser - Data Visualization Demo")
    print("=" * 60)
    print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Create sample data
    print("📊 Creating sample tax data...")
    df = create_sample_data()
    print(f"✅ Generated dataset with {len(df)} tax forms")
    print()
    
    # Generate visualizations
    print("📈 Generating visualizations...")
    
    print("1. Creating wages distribution charts...")
    create_wages_distribution(df)
    
    print("2. Creating tax analysis charts...")
    create_tax_analysis(df)
    
    print("3. Creating state-wise analysis...")
    create_state_analysis(df)
    
    print("4. Creating processing metrics...")
    create_processing_metrics(df)
    
    print("5. Creating refund analysis...")
    create_refund_analysis(df)
    
    print("6. Creating comprehensive dashboard...")
    create_comprehensive_dashboard(df)
    
    print("\n✅ All visualizations generated successfully!")
    print("📁 Files saved:")
    print("   • wages_distribution.png")
    print("   • tax_analysis.png") 
    print("   • state_analysis.png")
    print("   • processing_metrics.png")
    print("   • refund_analysis.png")
    print("   • comprehensive_dashboard.png")
    print("\n🎯 Ready for presentation and analysis!")

if __name__ == "__main__":
    main()