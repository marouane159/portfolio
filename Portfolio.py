import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import time

# Configure the Streamlit page
st.set_page_config(
    page_title="Bourse de Casablanca | Analyse de Portefeuille",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Color scheme
BLACK = "#000000"
RED = "#FF0000"
YELLOW = "#FFFF00"
DARK_RED = "#CC0000"
DARK_YELLOW = "#CCCC00"
WHITE = "#FFFFFF"
GREEN = "#00FF00"

# Fonction pour calculer les métriques du portefeuille
def calculate_portfolio_metrics(stocks_data):
    if not stocks_data:
        return None
    
    # Calcul des métriques de base
    total_investment = sum(stock["quantity"] * stock["buy_price"] for stock in stocks_data)
    current_value = sum(stock["quantity"] * stock["current_price"] for stock in stocks_data)
    pnl = current_value - total_investment
    pnl_percentage = (pnl / total_investment * 100) if total_investment > 0 else 0
    
    # Calcul du drawdown maximum
    max_drawdown = 0 if pnl > 0 else abs(pnl_percentage)
    
    # Calcul des performances par action
    stock_performances = []
    total_dividends = 0  # Assuming we'll add dividend data later
    
    for stock in stocks_data:
        stock_value = stock["quantity"] * stock["current_price"]
        stock_investment = stock["quantity"] * stock["buy_price"]
        stock_pnl = stock_value - stock_investment
        stock_pnl_percentage = (stock_pnl / stock_investment * 100) if stock_investment > 0 else 0
        
        # Calculate individual stock metrics
        cost_basis = stock["buy_price"]
        market_price = stock["current_price"]
        unrealized_gain = stock_pnl
        position_weight = (stock_value / current_value * 100) if current_value > 0 else 0
        
        # Calculate breakeven price
        breakeven_price = cost_basis  # Will be adjusted when we add transaction costs
        
        # Calculate distance to breakeven
        distance_to_breakeven = ((breakeven_price - market_price) / market_price * 100)
        
        stock_performances.append({
            "symbol": stock["symbol"],
            "name": stock["name"],
            "current_price": stock["current_price"],
            "buy_price": stock["buy_price"],
            "quantity": stock["quantity"],
            "value": stock_value,
            "investment": stock_investment,
            "pnl": stock_pnl,
            "pnl_percentage": stock_pnl_percentage,
            "weight": position_weight,
            "sector": stock.get("sector", "Autre"),
            "unrealized_gain": unrealized_gain,
            "cost_basis": cost_basis,
            "breakeven_price": breakeven_price,
            "distance_to_breakeven": distance_to_breakeven
        })
    
    # Portfolio Risk Metrics
    # Note: These are simplified calculations. In a real application, these would use historical data
    volatility = 15  # Simplified - should use historical price data
    beta = 0.8  # Simplified - should calculate using market correlation
    alpha = 2.5  # Simplified - should calculate vs benchmark
    sharpe_ratio = 1.2  # Simplified - should use risk-free rate and std dev
    sortino_ratio = 1.5  # Simplified - should use downside deviation
    
    # Portfolio Concentration Metrics
    sector_distribution = {}
    for stock in stock_performances:
        sector = stock["sector"]
        if sector not in sector_distribution:
            sector_distribution[sector] = 0
        sector_distribution[sector] += stock["value"]
    
    # Calculate sector concentration
    total_value = sum(sector_distribution.values())
    sector_weights = {k: (v/total_value)*100 for k, v in sector_distribution.items()}
    
    # Calculate Herfindahl-Hirschman Index (HHI) for concentration
    hhi_sectors = sum((weight/100)**2 for weight in sector_weights.values()) * 10000
    hhi_stocks = sum((stock["weight"]/100)**2 for stock in stock_performances) * 10000
    
    # Portfolio Quality Metrics
    avg_pnl_percentage = sum(stock["pnl_percentage"] for stock in stock_performances) / len(stock_performances)
    winning_positions = sum(1 for stock in stock_performances if stock["pnl"] > 0)
    losing_positions = len(stock_performances) - winning_positions
    win_rate = (winning_positions / len(stock_performances) * 100) if stock_performances else 0
    
    # Calculate risk level based on multiple factors
    risk_factors = {
        "volatility": volatility / 20,  # Normalize to 0-1 scale
        "beta": beta,
        "concentration": hhi_stocks / 10000,  # Already 0-1 scale
        "max_drawdown": abs(max_drawdown) / 100  # Convert to 0-1 scale
    }
    
    risk_score = sum(risk_factors.values()) / len(risk_factors)
    
    if risk_score < 0.3:
        risk_level = "Faible"
        risk_color = YELLOW
    elif risk_score < 0.6:
        risk_level = "Modéré"
        risk_color = DARK_YELLOW
    else:
        risk_level = "Élevé"
        risk_color = RED
    
    # Return enhanced metrics
    return {
        "total_investment": total_investment,
        "current_value": current_value,
        "pnl": pnl,
        "pnl_percentage": pnl_percentage,
        "stock_performances": stock_performances,
        "sector_distribution": sector_distribution,
        "sector_weights": sector_weights,
        
        # Risk Metrics
        "ratios": {
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "beta": beta,
            "alpha": alpha,
            "volatility": f"{volatility}%",
            "max_drawdown": f"{max_drawdown}%",
            "risk_level": risk_level,
            "risk_color": risk_color
        },
        
        # Concentration Metrics
        "concentration": {
            "hhi_sectors": hhi_sectors,
            "hhi_stocks": hhi_stocks,
            "sector_concentration": max(sector_weights.values()) if sector_weights else 0,
            "top_holding_weight": max(stock["weight"] for stock in stock_performances)
        },
        
        # Performance Metrics
        "performance": {
            "total_return": pnl_percentage,
            "avg_position_return": avg_pnl_percentage,
            "win_rate": win_rate,
            "winning_positions": winning_positions,
            "losing_positions": losing_positions,
            "best_position": max(stock["pnl_percentage"] for stock in stock_performances),
            "worst_position": min(stock["pnl_percentage"] for stock in stock_performances)
        },
        
        # Portfolio Health Metrics
        "health": {
            "diversification_score": 100 - (hhi_stocks / 100),  # Higher is better
            "risk_adjusted_return": pnl_percentage / (volatility if volatility > 0 else 1),
            "total_dividends": total_dividends,
            "dividend_yield": (total_dividends / current_value * 100) if current_value > 0 else 0
        }
    }

# Add compound interest calculator
def calculate_compound_interest(initial_investment, years, annual_return=10):
    """
    Calculate compound interest based on MASI average performance
    """
    final_amount = initial_investment * (1 + annual_return/100) ** years
    total_return = final_amount - initial_investment
    return {
        "initial_investment": initial_investment,
        "final_amount": final_amount,
        "total_return": total_return,
        "annual_return": annual_return,
        "years": years
    }

# Base stock data with symbols and sectors
BASE_STOCKS = [
    {"symbol": "ADH", "name": "DOUJA PROM ADDOHA", "sector": "Immobilier"},
    {"symbol": "ADI", "name": "ALLIANCES", "sector": "Divers"},
    {"symbol": "AFI", "name": "AFRIC INDUSTRIES", "sector": "Industrie"},
    {"symbol": "AFM", "name": "AFMA", "sector": "Finance"},
    {"symbol": "AKT", "name": "AKDITAL S.A", "sector": "Santé"},
    {"symbol": "ALM", "name": "ALUMINIUM DU MAROC", "sector": "Matériaux"},
    {"symbol": "ARD", "name": "ARADEI CAPITAL", "sector": "Immobilier"},
    {"symbol": "ATH", "name": "AUTO HALL", "sector": "Automobile"},
    {"symbol": "ATL", "name": "ATLANTASANAD", "sector": "Distribution"},
    {"symbol": "ATW", "name": "ATTIJARIWAFA BANK", "sector": "Banque"},
    {"symbol": "BAL", "name": "BALIMA", "sector": "Distribution"},
    {"symbol": "BCI", "name": "BANQUE CENTRALE POPULAIRE", "sector": "Banque"},
    {"symbol": "CDM", "name": "CARTIER SAADA", "sector": "Distribution"},
    {"symbol": "CIH", "name": "CREDIT IMMOBILIER ET HOTELIER", "sector": "Banque"},
    {"symbol": "CMT", "name": "CIMENTS DU MAROC", "sector": "Matériaux"},
    {"symbol": "COL", "name": "COLORADO", "sector": "Distribution"},
    {"symbol": "CTM", "name": "COMPAGNIE DE TRANSPORTS AU MAROC", "sector": "Transport"},
    {"symbol": "DIM", "name": "DELATTRE LEVIVIER MAROC", "sector": "Industrie"},
    {"symbol": "DOW", "name": "DARI COUSPATE", "sector": "Agroalimentaire"},
    {"symbol": "EQD", "name": "EQDOM", "sector": "Immobilier"},
    {"symbol": "FEN", "name": "FENIE BROSSETTE", "sector": "Distribution"},
    {"symbol": "IAM", "name": "MAROC TELECOM", "sector": "Télécom"},
    {"symbol": "INM", "name": "INDUSTRIE DU MAROC", "sector": "Industrie"},
    {"symbol": "JET", "name": "JET CONTRACTORS", "sector": "Construction"},
    {"symbol": "LES", "name": "LESIEUR CRISTAL", "sector": "Agroalimentaire"},
    {"symbol": "MAD", "name": "MAGHREB OXYGENE", "sector": "Industrie"},
    {"symbol": "MNG", "name": "MANAGEM", "sector": "Mines"},
    {"symbol": "MUT", "name": "MUTANDIS", "sector": "Agroalimentaire"},
    {"symbol": "NEO", "name": "NEO PHARMA", "sector": "Pharma"},
    {"symbol": "PUM", "name": "PUMATECH", "sector": "Industrie"},
    {"symbol": "RCS", "name": "RÉSIDENCES DAR SAADA", "sector": "Immobilier"},
    {"symbol": "SAM", "name": "SAMIR", "sector": "Énergie"},
    {"symbol": "SID", "name": "SONASID", "sector": "Agroalimentaire"},
    {"symbol": "SNP", "name": "SNEP", "sector": "Industrie"},
    {"symbol": "SOT", "name": "SOTHEMA", "sector": "Pharma"},
    {"symbol": "SRM", "name": "REALISATIONS MECANIQUES", "sector": "Industrie"},
    {"symbol": "STR", "name": "STROC INDUSTRIE", "sector": "Industrie"},
    {"symbol": "TGC", "name": "TRAVAUX GENERAUX DE CONSTRUCTIONS", "sector": "Construction"},
    {"symbol": "TMA", "name": "TOTALENERGIES MARKETING MAROC", "sector": "Énergie"},
    {"symbol": "TQM", "name": "TAQA MOROCCO", "sector": "Énergie"},
    {"symbol": "UMR", "name": "UNIMER", "sector": "Agroalimentaire"},
    {"symbol": "WAA", "name": "WAFA ASSURANCE", "sector": "Assurance"},
    {"symbol": "ZDJ", "name": "ZELLIDJA S.A", "sector": "Mines"},
    {"symbol": "MSA", "name": "SODEP MARSA MAROC", "sector": "Transport"},
    {"symbol": "RDS", "name": "RESIDENCE DAR SAADA", "sector": "Construction"},
    {"symbol": "CSR", "name": "COSUMAR", "sector": "Industrie"},
    {"symbol": "CFG", "name": "CFG BANK", "sector": "Banque"},
    {"symbol": "CMG", "name": "CMGP CAS", "sector": "Agriculture"},
    {"symbol": "HPS", "name": "HPS", "sector": "Paiment"},
    {"symbol": "RIS", "name": "RISMA", "sector": "Hotel Management"},
    {"symbol": "DHO", "name": "DELTA HOLDING", "sector": "Industrie"}
    {"symbol": "DWY", "name": "DISWAY", "sector": "Distribution éléctro"}
]

def get_moroccan_stocks():
    try:
        # Set up headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # Make the request
        url = "https://www.tradingview.com/markets/stocks-morocco/market-movers-all-stocks/"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            st.error(f"Failed to fetch data. Status code: {response.status_code}")
            return None
            
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the table
        table = soup.find('table')
        if not table:
            st.error("Could not find stock table on the page")
            return None
            
        # Extract data from table rows
        stocks_data = []
        for row in table.find_all('tr')[1:]:  # Skip header row
            try:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    # Extract symbol and price
                    symbol_cell = cells[0].find('a')
                    if symbol_cell:
                        symbol = symbol_cell.text.strip()
                        price_text = cells[1].text.strip()
                        
                        # Clean and convert price
                        try:
                            price = float(price_text.replace('MAD', '').replace(',', '').strip())
                            
                            # Find matching stock in BASE_STOCKS
                            stock_info = next((s for s in BASE_STOCKS if s["symbol"] == symbol), None)
                            if stock_info:
                                stocks_data.append({
                                    "symbol": symbol,
                                    "name": stock_info["name"],
                                    "price": price,
                                    "sector": stock_info["sector"]
                                })
                        except ValueError:
                            st.warning(f"Could not parse price for {symbol}: {price_text}")
                            continue
            except Exception as e:
                st.warning(f"Error processing row: {str(e)}")
                continue
        
        if not stocks_data:
            st.error("No valid stock data could be retrieved from TradingView")
            return None
            
        return pd.DataFrame(stocks_data)
        
    except Exception as e:
        st.error(f"Error while fetching stock data: {str(e)}")
        return None

# Custom CSS for the new design
st.markdown(f"""
    <style>
    /* Main background */
    .main {{
        background-color: {BLACK};
    }}
    .stApp {{
        background-color: {BLACK};
    }}
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {{
        color: {YELLOW};
    }}
    
    /* Sidebar */
    .css-1lcbmhc {{
        background-color: {BLACK};
        color: {YELLOW};
        border: 2px solid {RED};
    }}
    .css-1lcbmhc h1, .css-1lcbmhc h2, .css-1lcbmhc h3 {{
        color: {YELLOW};
    }}
    
    /* Buttons */
    .stButton>button {{
        background-color: {RED};
        color: {BLACK};
        border: none;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: bold;
        width: 100%;
    }}
    .stButton>button:hover {{
        background-color: {DARK_RED};
        color: {BLACK};
    }}
    
    /* Inputs */
    .stTextInput>div>div>input, .stNumberInput>div>div>input {{
        background-color: {BLACK};
        border: 1px solid {RED};
        color: {YELLOW};
    }}
    
    /* Metrics */
    .stMetric {{
        background-color: {BLACK};
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 5px rgba(255,0,0,0.2);
        border: 1px solid {RED};
    }}
    
    /* Cards */
    .card {{
        background-color: {BLACK};
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 10px rgba(255,0,0,0.2);
        border: 1px solid {RED};
    }}
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 10px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: {BLACK};
        border-radius: 5px 5px 0 0;
        padding: 10px 20px;
        border: 1px solid {RED};
        color: {YELLOW};
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {RED};
        color: {BLACK};
    }}
    
    /* Tables */
    .dataframe {{
        background-color: {BLACK};
        color: {YELLOW};
    }}

    /* Mobile Responsive Styles */
    @media (max-width: 768px) {{
        /* Header adjustments */
        .header-container {{
            flex-direction: column;
            text-align: center;
            gap: 15px;
        }}
        
        /* Portfolio summary grid */
        .portfolio-summary {{
            grid-template-columns: 1fr !important;
            gap: 10px;
        }}
        
        /* Chart containers */
        .element-container {{
            padding: 10px !important;
        }}
        
        /* Sidebar adjustments */
        .css-1lcbmhc {{
            width: 100% !important;
            max-width: 100% !important;
        }}
        
        /* Input fields */
        .stTextInput, .stNumberInput {{
            width: 100% !important;
        }}
        
        /* Tables */
        .dataframe {{
            font-size: 12px;
        }}
        
        /* Metrics */
        .stMetric {{
            padding: 10px;
        }}
        
        /* Footer */
        .footer-container {{
            flex-direction: column;
            gap: 10px;
        }}
    }}

    /* Tablet Responsive Styles */
    @media (min-width: 769px) and (max-width: 1024px) {{
        .portfolio-summary {{
            grid-template-columns: repeat(2, 1fr) !important;
        }}
    }}

    /* General Responsive Utilities */
    .responsive-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 15px;
    }}

    .responsive-flex {{
        display: flex;
        flex-wrap: wrap;
        gap: 15px;
    }}

    .responsive-text {{
        font-size: clamp(14px, 2vw, 16px);
    }}

    .responsive-padding {{
        padding: clamp(10px, 2vw, 20px);
    }}

    /* Scrollable tables for mobile */
    .stDataFrame {{
        overflow-x: auto;
    }}

    /* Adjust plotly charts for mobile */
    .js-plotly-plot {{
        width: 100% !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# Add custom HTML for favicon and meta tags
st.markdown("""
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>💰</text></svg>">
    <link rel="apple-touch-icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>💰</text></svg>">
    
    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://risk.ma/bourse-de-casablanca">
    <meta property="og:title" content="Portefeuille Bourse de Casablanca | @risk.maroc">
    <meta property="og:description" content="Tableau de bord d'investissement pour la Bourse de Casablanca avec analyse de portefeuille">
    <meta property="og:image" content="https://www.casablanca-bourse.com/_next/static/media/logo.1b5cfecc.webp">
    <meta property="og:image:width" content="1920">
    <meta property="og:image:height" content="1080">
    <meta property="og:image:type" content="image/webp">
    
    <!-- Twitter -->
    <meta property="twitter:card" content="summary_large_image">
    <meta property="twitter:url" content="https://risk.ma/bourse-de-casablanca">
    <meta property="twitter:title" content="Portefeuille Bourse de Casablanca | @risk.maroc">
    <meta property="twitter:description" content="Tableau de bord d'investissement pour la Bourse de Casablanca avec analyse de portefeuille">
    <meta property="twitter:image" content="https://www.casablanca-bourse.com/_next/static/media/logo.1b5cfecc.webp">
""", unsafe_allow_html=True)

# Header with logo and title
st.markdown(f"""
    <div style='background-color: {BLACK}; color: {YELLOW}; padding: 20px; border-radius: 10px; margin-bottom: 20px; border: 2px solid {RED};' class='responsive-padding'>
        <div style='display: flex; align-items: center; justify-content: space-between;' class='header-container responsive-flex'>
            <div style='flex: 1;'>
                <h1 style='margin: 0; color: {YELLOW}; font-size: clamp(24px, 4vw, 32px);'>Portefeuille Bourse de Casablanca</h1>
                <p style='margin: 0; font-size: clamp(14px, 2vw, 16px);'>Tableau de bord d'investissement | @dogofallstreets | @risk.maroc</p>
            </div>
            <div style='display: flex; align-items: center; gap: 15px;' class='responsive-flex'>
                <div style='background-color: {RED}; padding: 5px 10px; border-radius: 5px; color: {BLACK}; font-weight: bold;'>
                    <a href='https://risk.ma/bourse-de-casablanca' target='_blank' style='color: {BLACK}; text-decoration: none; font-size: clamp(12px, 2vw, 14px);'>www.risk.ma</a>
                </div>
                <div style='display: flex; gap: 10px;'>
                    <a href='https://instagram.com/risk.maroc' target='_blank' style='color: {YELLOW}; text-decoration: none;'>
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" fill="{YELLOW}"/>
                        </svg>
                    </a>
                    <a href='https://tiktok.com/@risk.maroc' target='_blank' style='color: {YELLOW}; text-decoration: none;'>
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z" fill="{YELLOW}"/>
                        </svg>
                    </a>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Add JavaScript for sidebar control
st.markdown("""
    <script>
        // Function to toggle sidebar visibility
        function toggleSidebar(show) {
            const sidebar = window.parent.document.querySelector('.css-1d391kg');
            if (sidebar) {
                sidebar.style.display = show ? 'block' : 'none';
                sidebar.style.transition = 'all 0.3s ease-in-out';
            }
        }
    </script>
""", unsafe_allow_html=True)

# Sidebar for data input with mobile optimizations
with st.sidebar:
    st.markdown(f"""
        <div style='background-color: {BLACK}; color: {YELLOW}; padding: 15px; border-radius: 10px; margin-bottom: 20px; border: 1px solid {RED};'>
            <h3 style='color: {YELLOW}; margin: 0;'>Configuration du Portefeuille</h3>
        </div>
        """, unsafe_allow_html=True)
    
    # Refresh button
    if st.button("🔄 Actualiser les cours", key="refresh_button"):
        with st.spinner("Chargement des données..."):
            stocks_df = get_moroccan_stocks()
            if stocks_df is not None and not stocks_df.empty:
                st.session_state.stocks_df = stocks_df
                st.success(f"Données chargées avec succès! {len(stocks_df)} actions disponibles.")
            else:
                st.error("Impossible de charger les données des actions.")
    
    # Initialize session state if not already done
    if 'stocks_df' not in st.session_state:
        # Try to get real-time data
        stocks_df = get_moroccan_stocks()
        
        # If scraping fails, use base stocks with default prices
        if stocks_df is None or stocks_df.empty:
            st.warning("Using base stock data as fallback. Prices may not be current.")
            base_data = []
            for stock in BASE_STOCKS:
                base_data.append({
                    "symbol": stock["symbol"],
                    "name": stock["name"],
                    "price": 100.0,  # Default price
                    "sector": stock["sector"]
                })
            st.session_state.stocks_df = pd.DataFrame(base_data)
        else:
            st.session_state.stocks_df = stocks_df

    # Portfolio configuration
    st.markdown("#### Composition du Portefeuille")
    num_stocks = st.number_input("Nombre d'actions", min_value=1, max_value=len(BASE_STOCKS), value=1, step=1)
    
    stocks_data = []
    for i in range(num_stocks):
        st.markdown(f"**Action {i+1}**")
        
        # Stock selection
        stock_options = st.session_state.stocks_df.apply(
            lambda x: f"{x['symbol']} - {x['name']}", 
            axis=1
        ).tolist()
        
        selected_stock = st.selectbox(
            f"Sélectionnez l'action {i+1}",
            options=stock_options,
            key=f"stock_{i}"
        )
        
        # Extract stock info
        symbol = selected_stock.split(' - ')[0]
        stock_info = st.session_state.stocks_df[
            st.session_state.stocks_df['symbol'] == symbol
        ].iloc[0]
        
        # Quantity input
        quantity = st.number_input(
            "Quantité",
            min_value=1,
            value=1,
            key=f"quantity_{i}"
        )
        
        # Buy price input
        buy_price = st.number_input(
            "Prix d'achat (MAD)",
            min_value=0.0,
            value=float(stock_info['price']),
            key=f"buy_price_{i}"
        )
        
        # Display current price
        st.info(f"Prix actuel: {stock_info['price']} MAD | Secteur: {stock_info['sector']}")
        
        stocks_data.append({
            "symbol": symbol,
            "name": stock_info['name'],
            "quantity": quantity,
            "buy_price": buy_price,
            "current_price": stock_info['price'],
            "sector": stock_info['sector']
        })
    
    # Calculate portfolio button
    if st.button("📊 Analyser le Portefeuille", key="calculate_portfolio"):
        if not stocks_data:
            st.error("Veuillez ajouter au moins une action à votre portefeuille.")
        else:
            st.session_state.portfolio_metrics = calculate_portfolio_metrics(stocks_data)
            # Auto-hide the sidebar
            st.markdown("""
                <script>
                    var elements = window.parent.document.getElementsByClassName("css-1d391kg");
                    if (elements.length > 0) {
                        elements[0].style.display = "none";
                    }
                </script>
                """, unsafe_allow_html=True)

# Main content area
if 'portfolio_metrics' in st.session_state:
    metrics = st.session_state.portfolio_metrics
    
    # Single menu button in a fixed position
    st.markdown("""
        <style>
            #menu-button {
                position: fixed;
                top: 10px;
                left: 10px;
                z-index: 999;
                background-color: black;
                border: 1px solid #FF0000;
                color: #FFFF00;
                padding: 8px 12px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 20px;
                transition: all 0.3s ease;
            }
            #menu-button:hover {
                background-color: #FF0000;
                color: black;
            }
        </style>
        <button id="menu-button" onclick="toggleMenu()">☰</button>
        <script>
            function toggleMenu() {
                var sidebar = window.parent.document.getElementsByClassName("css-1d391kg")[0];
                if (sidebar) {
                    sidebar.style.display = sidebar.style.display === 'none' ? 'block' : 'none';
                }
            }
            // Execute once to ensure sidebar is hidden initially on mobile
            if (window.innerWidth <= 768) {
                var sidebar = window.parent.document.getElementsByClassName("css-1d391kg")[0];
                if (sidebar) {
                    sidebar.style.display = 'none';
                }
            }
        </script>
    """, unsafe_allow_html=True)
    
    # Portfolio summary cards
    st.markdown(f"""
        <div style='background-color: {BLACK}; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(255,0,0,0.2);' class='responsive-padding'>
            <h2 style='color: {YELLOW}; margin-top: 0; font-size: clamp(20px, 3vw, 24px);'>Résumé du Portefeuille</h2>
            <div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px;' class='portfolio-summary responsive-grid'>
                <div style='background-color: {BLACK}; padding: 15px; border-radius: 10px; border-left: 4px solid {RED};' class='responsive-padding'>
                    <div style='font-size: clamp(12px, 2vw, 14px); color: {YELLOW};'>Investissement Total</div>
                    <div style='font-size: clamp(18px, 3vw, 24px); font-weight: bold;'>{metrics['total_investment']:,.2f} MAD</div>
                </div>
                <div style='background-color: {BLACK}; padding: 15px; border-radius: 10px; border-left: 4px solid {RED};' class='responsive-padding'>
                    <div style='font-size: clamp(12px, 2vw, 14px); color: {YELLOW};'>Valeur Actuelle</div>
                    <div style='font-size: clamp(18px, 3vw, 24px); font-weight: bold;'>{metrics['current_value']:,.2f} MAD</div>
                </div>
                <div style='background-color: {BLACK}; padding: 15px; border-radius: 10px; border-left: 4px solid {RED};' class='responsive-padding'>
                    <div style='font-size: clamp(12px, 2vw, 14px); color: {YELLOW};'>Gain & Perte</div>
                    <div style='font-size: clamp(18px, 3vw, 24px); font-weight: bold; color: {RED};'>
                        {metrics['pnl']:,.2f} MAD ({metrics['pnl_percentage']:.2f}%)
                    </div>
                </div>
                <div style='background-color: {BLACK}; padding: 15px; border-radius: 10px; border-left: 4px solid {RED};' class='responsive-padding'>
                    <div style='font-size: clamp(12px, 2vw, 14px); color: {YELLOW};'>Niveau de Risque</div>
                    <div style='font-size: clamp(18px, 3vw, 24px); font-weight: bold; color: {RED};'>
                        {metrics['ratios']['risk_level']}
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Performance section
    st.markdown(f"""
        <div style='background-color: {BLACK}; border-radius: 10px; padding: 20px; margin-bottom: 20px;' class='responsive-padding'>
            <h3 style='color: {YELLOW};'>Performance du Portefeuille</h3>
        </div>
        """, unsafe_allow_html=True)
    
    # Create performance data
    performance_data = pd.DataFrame(metrics["stock_performances"])
    
    # Create buy vs current price comparison chart
    fig_price_comparison = go.Figure()
    
    # Sort stocks by performance percentage
    sorted_performance = performance_data.sort_values('pnl_percentage', ascending=True)
    
    for _, stock in sorted_performance.iterrows():
        # Find the original stock data to get buy price
        stock_data = next((s for s in stocks_data if s["symbol"] == stock["symbol"]), None)
        if stock_data:
            buy_price = stock_data["buy_price"]
            current_price = stock["current_price"]
            
            # Add buy price point
            fig_price_comparison.add_trace(go.Scatter(
                x=[stock["symbol"]],
                y=[buy_price],
                mode='markers',
                name=f'Prix d\'achat - {stock["symbol"]}',
                marker=dict(color=DARK_RED, size=12, symbol='circle'),
                showlegend=False
            ))
            
            # Add current price point
            fig_price_comparison.add_trace(go.Scatter(
                x=[stock["symbol"]],
                y=[current_price],
                mode='markers',
                name=f'Prix actuel - {stock["symbol"]}',
                marker=dict(color=YELLOW, size=12, symbol='star'),
                showlegend=False
            ))
            
            # Add connecting line
            fig_price_comparison.add_trace(go.Scatter(
                x=[stock["symbol"], stock["symbol"]],
                y=[buy_price, current_price],
                mode='lines',
                line=dict(color=RED if current_price < buy_price else YELLOW, width=2),
                showlegend=False
            ))

    # Update layout
    fig_price_comparison.update_layout(
        title=dict(
            text="Évolution des Prix par Action",
            font=dict(color=YELLOW),
            x=0.5
        ),
        plot_bgcolor=BLACK,
        paper_bgcolor=BLACK,
        font=dict(color=YELLOW),
        xaxis=dict(
            title="Actions",
            tickfont=dict(color=YELLOW),
            gridcolor=RED,
            linecolor=RED,
            zerolinecolor=RED
        ),
        yaxis=dict(
            title="Prix (MAD)",
            tickfont=dict(color=YELLOW),
            gridcolor=RED,
            linecolor=RED,
            zerolinecolor=RED
        ),
        showlegend=True,
        height=500,
        width=None,
        margin=dict(l=50, r=50, t=50, b=50),
        hovermode='closest'
    )
    
    # Add a custom legend
    fig_price_comparison.add_trace(go.Scatter(
        x=[None],
        y=[None],
        mode='markers',
        marker=dict(color=DARK_RED, size=12, symbol='circle'),
        name='Prix d\'achat'
    ))
    fig_price_comparison.add_trace(go.Scatter(
        x=[None],
        y=[None],
        mode='markers',
        marker=dict(color=YELLOW, size=12, symbol='star'),
        name='Prix actuel'
    ))

    st.plotly_chart(fig_price_comparison, use_container_width=True)
    
    # Individual stock performance
    fig_perf = px.bar(
        performance_data,
        x="symbol",
        y="pnl_percentage",
        title="Performance par Action",
        color="pnl_percentage",
        color_continuous_scale=[RED, YELLOW],
        labels={"pnl_percentage": "Performance (%)", "symbol": "Action"},
        text="pnl_percentage"
    )
    fig_perf.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
    fig_perf.update_layout(
        plot_bgcolor=BLACK,
        paper_bgcolor=BLACK,
        font=dict(color=YELLOW),
        yaxis=dict(showgrid=False),
        xaxis=dict(title=None),
        height=400,
        width=None
    )
    st.plotly_chart(fig_perf, use_container_width=True)

    # Distribution section
    st.markdown(f"""
        <div style='background-color: {BLACK}; border-radius: 10px; padding: 20px; margin-bottom: 20px;' class='responsive-padding'>
            <h3 style='color: {YELLOW};'>Répartition du Portefeuille</h3>
        </div>
        """, unsafe_allow_html=True)
    
    # Sector distribution pie chart
    sector_data = pd.DataFrame({
        "sector": list(metrics["sector_distribution"].keys()),
        "value": list(metrics["sector_distribution"].values())
    })
    
    fig_sector = px.pie(
        sector_data,
        values="value",
        names="sector",
        hole=0.4,
        color_discrete_sequence=[RED, YELLOW, DARK_RED, DARK_YELLOW]
    )
    fig_sector.update_layout(
        plot_bgcolor=BLACK,
        paper_bgcolor=BLACK,
        font=dict(color=YELLOW),
        showlegend=True,
        height=400,
        width=None
    )
    st.plotly_chart(fig_sector, use_container_width=True)
    
    # Asset distribution treemap
    fig_treemap = px.treemap(
        performance_data,
        path=['symbol'],
        values='value',
        color='pnl_percentage',
        color_continuous_scale=[RED, YELLOW],
        hover_data=['pnl_percentage']
    )
    fig_treemap.update_layout(
        plot_bgcolor=BLACK,
        paper_bgcolor=BLACK,
        margin=dict(t=0, l=0, r=0, b=0),
        height=400,
        width=None
    )
    st.plotly_chart(fig_treemap, use_container_width=True)

    # Detailed performance table
    st.markdown(f"""
        <div style='background-color: {BLACK}; border-radius: 10px; padding: 20px; margin-bottom: 20px;' class='responsive-padding'>
            <h3 style='color: {YELLOW};'>Détails des Positions</h3>
        </div>
        """, unsafe_allow_html=True)
    
    detailed_data = pd.DataFrame(metrics["stock_performances"])
    detailed_data = detailed_data[[
        "symbol", "name", "sector", "current_price", 
        "investment", "value", "pnl", "pnl_percentage", "weight"
    ]]
    
    # Create three columns for the table
    col1, col2, col3 = st.columns(3)
    
    # Split the data into three parts
    num_rows = len(detailed_data)
    rows_per_col = (num_rows + 2) // 3  # Round up division
    
    # Function to create a styled table for a subset of data
    def create_styled_table(data_subset, column):
        with column:
            for _, row in data_subset.iterrows():
                st.markdown(f"""
                    <div style='background-color: {BLACK}; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid {YELLOW};'>
                        <div style='color: {YELLOW};'>
                            <h4 style='margin: 0 0 10px 0;'>{row['name']} ({row['symbol']})</h4>
                            <p style='margin: 5px 0;'>• Secteur: {row['sector']}</p>
                            <p style='margin: 5px 0;'>• Prix actuel: {row['current_price']:,.2f} MAD</p>
                            <p style='margin: 5px 0;'>• Investissement: {row['investment']:,.2f} MAD</p>
                            <p style='margin: 5px 0;'>• Valeur: {row['value']:,.2f} MAD</p>
                            <p style='margin: 5px 0; color: {RED if row['pnl'] < 0 else YELLOW};'>
                                • P&L: {row['pnl']:+,.2f} MAD ({row['pnl_percentage']:+.2f}%)
                            </p>
                            <p style='margin: 5px 0;'>• Poids: {row['weight']:.2f}%</p>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
    
    # Display data in three columns
    create_styled_table(detailed_data.iloc[:rows_per_col], col1)
    create_styled_table(detailed_data.iloc[rows_per_col:2*rows_per_col], col2)
    create_styled_table(detailed_data.iloc[2*rows_per_col:], col3)

    # Financial ratios
    st.markdown(f"""
        <div style='background-color: {BLACK}; border-radius: 10px; padding: 20px; margin-bottom: 20px;' class='responsive-padding'>
            <h3 style='color: {YELLOW};'>Ratios Financiers</h3>
            <div style='display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px;' class='responsive-grid'>
                <div style='background-color: {BLACK}; padding: 15px; border-radius: 10px; border-left: 4px solid {RED};' class='responsive-padding'>
                    <div style='font-size: clamp(12px, 2vw, 14px); color: {YELLOW};'>Sharpe Ratio</div>
                    <div style='font-size: clamp(18px, 3vw, 24px); font-weight: bold;'>{metrics['ratios']['sharpe_ratio']:.2f}</div>
                </div>
                <div style='background-color: {BLACK}; padding: 15px; border-radius: 10px; border-left: 4px solid {RED};' class='responsive-padding'>
                    <div style='font-size: clamp(12px, 2vw, 14px); color: {YELLOW};'>Beta</div>
                    <div style='font-size: clamp(18px, 3vw, 24px); font-weight: bold;'>{metrics['ratios']['beta']:.2f}</div>
                </div>
                <div style='background-color: {BLACK}; padding: 15px; border-radius: 10px; border-left: 4px solid {RED};' class='responsive-padding'>
                    <div style='font-size: clamp(12px, 2vw, 14px); color: {YELLOW};'>Volatilité</div>
                    <div style='font-size: clamp(18px, 3vw, 24px); font-weight: bold;'>{metrics['ratios']['volatility']}</div>
                </div>
                <div style='background-color: {BLACK}; padding: 15px; border-radius: 10px; border-left: 4px solid {RED};' class='responsive-padding'>
                    <div style='font-size: clamp(12px, 2vw, 14px); color: {YELLOW};'>Performance Totale</div>
                    <div style='font-size: clamp(18px, 3vw, 24px); font-weight: bold;'>{metrics['performance']['total_return']:.2f}%</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Win Rate and Drawdown Section
    st.markdown(f"""
        <div style='background-color: {BLACK}; border-radius: 10px; padding: 20px; margin-bottom: 20px; border: 1px solid {YELLOW};'>
            <h3 style='color: {YELLOW};'>Performance et Risque</h3>
        </div>
    """, unsafe_allow_html=True)

    # Create two columns for the metrics
    col1, col2 = st.columns(2)
    
    # Performance Metrics Card
    with col1:
        st.markdown(f"""
            <div style='background-color: {BLACK}; padding: 20px; border-radius: 10px; border: 1px solid {YELLOW}; margin-bottom: 20px;'>
                <h4 style='color: {YELLOW}; margin-bottom: 15px;'>📈 Performance</h4>
                <div style='display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;'>
                    <div style='text-align: center; padding: 10px; border-radius: 5px; border: 1px solid {YELLOW};'>
                        <div style='font-size: 14px; color: {YELLOW};'>Taux de Réussite</div>
                        <div style='font-size: 24px; font-weight: bold; color: {YELLOW};'>{metrics['performance']['win_rate']:.1f}%</div>
                    </div>
                    <div style='text-align: center; padding: 10px; border-radius: 5px; border: 1px solid {YELLOW};'>
                        <div style='font-size: 14px; color: {YELLOW};'>Positions Gagnantes</div>
                        <div style='font-size: 24px; font-weight: bold; color: {YELLOW};'>{metrics['performance']['winning_positions']}/{len(metrics['stock_performances'])}</div>
                    </div>
                    <div style='text-align: center; padding: 10px; border-radius: 5px; border: 1px solid {YELLOW};'>
                        <div style='font-size: 14px; color: {YELLOW};'>Meilleure Position</div>
                        <div style='font-size: 24px; font-weight: bold; color: {YELLOW};'>+{metrics['performance']['best_position']:.1f}%</div>
                    </div>
                    <div style='text-align: center; padding: 10px; border-radius: 5px; border: 1px solid {YELLOW};'>
                        <div style='font-size: 14px; color: {YELLOW};'>Performance Moyenne</div>
                        <div style='font-size: 24px; font-weight: bold; color: {YELLOW};'>{metrics['performance']['avg_position_return']:.1f}%</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # Risk Metrics Card
    with col2:
        st.markdown(f"""
            <div style='background-color: {BLACK}; padding: 20px; border-radius: 10px; border: 1px solid {YELLOW}; margin-bottom: 20px;'>
                <h4 style='color: {YELLOW}; margin-bottom: 15px;'>📊 Métriques de Risque</h4>
                <div style='display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;'>
                    <div style='text-align: center; padding: 10px; border-radius: 5px; border: 1px solid {YELLOW};'>
                        <div style='font-size: 14px; color: {YELLOW};'>Drawdown Maximum</div>
                        <div style='font-size: 24px; font-weight: bold; color: {YELLOW};'>{metrics['ratios']['max_drawdown']}</div>
                    </div>
                    <div style='text-align: center; padding: 10px; border-radius: 5px; border: 1px solid {YELLOW};'>
                        <div style='font-size: 14px; color: {YELLOW};'>Pire Position</div>
                        <div style='font-size: 24px; font-weight: bold; color: {YELLOW};'>{metrics['performance']['worst_position']:.1f}%</div>
                    </div>
                    <div style='text-align: center; padding: 10px; border-radius: 5px; border: 1px solid {YELLOW};'>
                        <div style='font-size: 14px; color: {YELLOW};'>Score de Diversification</div>
                        <div style='font-size: 24px; font-weight: bold; color: {YELLOW};'>{metrics['health']['diversification_score']:.0f}/100</div>
                    </div>
                    <div style='text-align: center; padding: 10px; border-radius: 5px; border: 1px solid {YELLOW};'>
                        <div style='font-size: 14px; color: {YELLOW};'>Ratio de Sharpe</div>
                        <div style='font-size: 24px; font-weight: bold; color: {YELLOW};'>{metrics['ratios']['sharpe_ratio']:.2f}</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # Recommendations section
    st.markdown("""
        <div style='background-color: #000000; border-radius: 10px; padding: 20px; margin-bottom: 20px; border: 1px solid #FFFF00;'>
            <h3 style='color: #FFFF00;'>Recommandations</h3>
        </div>
    """, unsafe_allow_html=True)
    
    performance_data = pd.DataFrame(metrics["stock_performances"])
    best_performer = performance_data.loc[performance_data['pnl_percentage'].idxmax()]
    worst_performer = performance_data.loc[performance_data['pnl_percentage'].idxmin()]
    
    # Calculate additional metrics for recommendations
    portfolio_concentration = metrics['concentration']['sector_concentration']
    diversification_score = metrics['health']['diversification_score']
    risk_level = metrics['ratios']['risk_level']
    volatility = float(metrics['ratios']['volatility'].strip('%'))
    beta = metrics['ratios']['beta']
    
    # Generate trading signals
    def generate_trading_signals(stock_data):
        current_price = stock_data['current_price']
        buy_price = stock_data['buy_price']
        weight = stock_data['weight']
        pnl = stock_data['pnl']
        pnl_percentage = stock_data['pnl_percentage']
        
        trend = "haussier" if current_price > buy_price else "baissier"
        
        if weight > 25:
            size_rec = "réduire"
            size_detail = f"Considérer une réduction de {min(10, weight - 20)}% de la position"
        elif weight < 5:
            size_rec = "augmenter"
            size_detail = f"Opportunité d'augmenter jusqu'à {10 - weight}% de la position"
        else:
            size_rec = "maintenir"
            size_detail = "Poids actuel optimal"
            
        if pnl > 0 and weight > 25:
            action = "Prendre des bénéfices partiels"
            action_detail = f"Considérer une prise de bénéfices de {min(30, pnl_percentage)}% de la position"
        elif pnl < 0 and weight < 5:
            action = "Opportunité d'accumulation"
            action_detail = f"Accumulation recommandée avec un objectif de {10 - weight}% du portefeuille"
        elif pnl < 0 and weight > 15:
            action = "Surveiller de près"
            action_detail = "Mettre en place un stop-loss et surveiller les fondamentaux"
        else:
            action = "Maintenir la position"
            action_detail = "La position est bien équilibrée"
            
        return trend, size_rec, size_detail, action, action_detail

    # Generate portfolio health recommendations
    portfolio_health = []
    if portfolio_concentration > 40:
        portfolio_health.append(f"⚠️ Forte concentration sectorielle ({portfolio_concentration:.1f}%) - Envisager une diversification vers d'autres secteurs")
        portfolio_health.append("• Objectif: Réduire la concentration à moins de 30%")
        portfolio_health.append("• Stratégie: Identifier des opportunités dans des secteurs sous-représentés")
    if diversification_score < 60:
        portfolio_health.append(f"⚠️ Score de diversification faible ({diversification_score:.1f}/100) - Ajouter des positions non corrélées")
        portfolio_health.append("• Objectif: Atteindre un score de diversification > 70")
        portfolio_health.append("• Stratégie: Diversifier par secteur et par capitalisation")
    if volatility > 20:
        portfolio_health.append(f"⚠️ Volatilité élevée ({volatility:.1f}%) - Considérer des positions défensives")
        portfolio_health.append("• Objectif: Réduire la volatilité à moins de 15%")
        portfolio_health.append("• Stratégie: Augmenter la part des valeurs défensives")
    if beta > 1.2:
        portfolio_health.append(f"⚠️ Beta élevé ({beta:.2f}) - Le portefeuille est plus volatil que le marché")
        portfolio_health.append("• Objectif: Réduire le beta à moins de 1.0")
        portfolio_health.append("• Stratégie: Ajouter des positions à faible beta")
    
    # Best and worst performers analysis
    best_trend, best_size, best_size_detail, best_action, best_action_detail = generate_trading_signals(best_performer)
    worst_trend, worst_size, worst_size_detail, worst_action, worst_action_detail = generate_trading_signals(worst_performer)
    
    # Create two columns for recommendations
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
            <div style='background-color: {BLACK}; padding: 15px; border-radius: 10px; border-left: 4px solid {YELLOW}; margin-bottom: 15px;'>
                <h4 style='color: {YELLOW}; margin-bottom: 15px;'>🌟 Position Performante</h4>
                <div style='color: {YELLOW};'>
                    <p><strong>{best_performer['name']} ({best_performer['symbol']})</strong></p>
                    <p>• Tendance: {best_trend}</p>
                    <p>• Performance: +{best_performer['pnl_percentage']:.1f}%</p>
                    <p>• Poids: {best_performer['weight']:.1f}%</p>
                    <p>• Recommandation: {best_action}</p>
                    <p>• Détail: {best_action_detail}</p>
                    <p>• Gestion de position: {best_size_detail}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div style='background-color: {BLACK}; padding: 15px; border-radius: 10px; border-left: 4px solid {RED}; margin-bottom: 15px;'>
                <h4 style='color: {YELLOW}; margin-bottom: 15px;'>⚠️ Position à Surveiller</h4>
                <div style='color: {YELLOW};'>
                    <p><strong>{worst_performer['name']} ({worst_performer['symbol']})</strong></p>
                    <p>• Tendance: {worst_trend}</p>
                    <p>• Performance: {worst_performer['pnl_percentage']:.1f}%</p>
                    <p>• Poids: {worst_performer['weight']:.1f}%</p>
                    <p>• Recommandation: {worst_action}</p>
                    <p>• Détail: {worst_action_detail}</p>
                    <p>• Gestion de position: {worst_size_detail}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # Portfolio Health Section
    st.markdown(f"""
        <div style='background-color: {BLACK}; padding: 15px; border-radius: 10px; margin-top: 20px; border: 1px solid {YELLOW};'>
            <h4 style='color: {YELLOW}; margin-bottom: 15px;'>Diagnostic du Portefeuille</h4>
        </div>
    """, unsafe_allow_html=True)
    
    if portfolio_health:
        for health_item in portfolio_health:
            st.markdown(f"""
                <div style='background-color: {BLACK}; color: {YELLOW}; padding: 10px; border-radius: 5px; margin: 5px 0; border: 1px solid {YELLOW};'>
                    {health_item}
                </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div style='background-color: {BLACK}; color: {YELLOW}; padding: 10px; border-radius: 5px; margin: 5px 0; border: 1px solid {YELLOW};'>
                ✅ Le portefeuille est bien équilibré
            </div>
        """, unsafe_allow_html=True)

    # Strategic Recommendations
    st.markdown(f"""
        <div style='background-color: {BLACK}; padding: 15px; border-radius: 10px; margin-top: 20px; border: 1px solid {YELLOW};'>
            <h4 style='color: {YELLOW}; margin-bottom: 15px;'>Recommandations Stratégiques</h4>
        </div>
    """, unsafe_allow_html=True)

    # Create metrics display with yellow styling
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
            <div style='background-color: {BLACK}; color: {YELLOW}; padding: 10px; border-radius: 5px; text-align: center; border: 1px solid {YELLOW};'>
                <div style='font-size: 14px;'>Niveau de Risque</div>
                <div style='font-size: 20px; font-weight: bold;'>{risk_level}</div>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div style='background-color: {BLACK}; color: {YELLOW}; padding: 10px; border-radius: 5px; text-align: center; border: 1px solid {YELLOW};'>
                <div style='font-size: 14px;'>Beta</div>
                <div style='font-size: 20px; font-weight: bold;'>{beta:.2f}</div>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
            <div style='background-color: {BLACK}; color: {YELLOW}; padding: 10px; border-radius: 5px; text-align: center; border: 1px solid {YELLOW};'>
                <div style='font-size: 14px;'>Volatilité</div>
                <div style='font-size: 20px; font-weight: bold;'>{volatility:.1f}%</div>
            </div>
        """, unsafe_allow_html=True)

    # Strategic Actions
    st.markdown(f"""
        <div style='color: {YELLOW}; margin-top: 20px; font-size: 18px; font-weight: bold;'>Actions Recommandées</div>
    """, unsafe_allow_html=True)
    
    if portfolio_concentration > 40:
        st.markdown(f"""
            <div style='background-color: {BLACK}; color: {YELLOW}; padding: 10px; border-radius: 5px; margin: 5px 0; border: 1px solid {YELLOW};'>
                • Rééquilibrage sectoriel nécessaire - concentration actuelle: {portfolio_concentration:.1f}%
                <br>• Objectif: Réduire à moins de 30%
                <br>• Stratégie: Identifier des opportunités dans des secteurs sous-représentés
            </div>
        """, unsafe_allow_html=True)
    if diversification_score < 60:
        st.markdown(f"""
            <div style='background-color: {BLACK}; color: {YELLOW}; padding: 10px; border-radius: 5px; margin: 5px 0; border: 1px solid {YELLOW};'>
                • Améliorer la diversification - score actuel: {diversification_score:.1f}/100
                <br>• Objectif: Atteindre un score > 70
                <br>• Stratégie: Diversifier par secteur et par capitalisation
            </div>
        """, unsafe_allow_html=True)
    if volatility > 20:
        st.markdown(f"""
            <div style='background-color: {BLACK}; color: {YELLOW}; padding: 10px; border-radius: 5px; margin: 5px 0; border: 1px solid {YELLOW};'>
                • Considérer des positions défensives pour réduire la volatilité
                <br>• Objectif: Réduire la volatilité à moins de 15%
                <br>• Stratégie: Augmenter la part des valeurs défensives
            </div>
        """, unsafe_allow_html=True)
    if beta > 1.2:
        st.markdown(f"""
            <div style='background-color: {BLACK}; color: {YELLOW}; padding: 10px; border-radius: 5px; margin: 5px 0; border: 1px solid {YELLOW};'>
                • Surveiller le beta élevé du portefeuille
                <br>• Objectif: Réduire le beta à moins de 1.0
                <br>• Stratégie: Ajouter des positions à faible beta
            </div>
        """, unsafe_allow_html=True)

    # Add compound interest calculator section
    st.markdown(f"""
        <div style='background-color: {BLACK}; border-radius: 10px; padding: 20px; margin-top: 30px; border: 2px solid {YELLOW};'>
            <h3 style='color: {YELLOW}; margin-bottom: 15px;'>💰 Calculateur d'Intérêts Composés</h3>
            <p style='color: {YELLOW}; margin-bottom: 20px;'>
                Estimez vos rendements potentiels sur la Bourse de Casablanca basés sur la performance moyenne annuelle du MASI (10% par an).
                <br><br>
                <span style='color: {RED}; font-weight: bold;'>Note:</span> Les calculs sont basés sur le rendement annuel moyen historique du MASI (10%), qui représente la performance moyenne du marché marocain sur le long terme.
            </p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        initial_investment = st.number_input("Montant initial (MAD)", min_value=1000, value=10000, step=1000)
    with col2:
        years = st.number_input("Nombre d'années", min_value=1, max_value=30, value=5, step=1)

    if st.button("Calculer les rendements"):
        result = calculate_compound_interest(initial_investment, years)
        
        st.markdown(f"""
            <div style='background-color: {BLACK}; padding: 15px; border-radius: 10px; border: 1px solid {YELLOW}; margin-top: 20px;'>
                <div style='color: {YELLOW};'>
                    <h4>Résultats du Calcul</h4>
                    <p>• Investissement initial: {result['initial_investment']:,.0f} MAD</p>
                    <p>• Montant final après {years} ans: {result['final_amount']:,.0f} MAD</p>
                    <p>• Gain total: {result['total_return']:,.0f} MAD</p>
                    <p>• Rendement annuel moyen: {result['annual_return']}%</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Create a line chart showing the growth over time
        years_data = list(range(years + 1))
        amounts = [initial_investment * (1 + result['annual_return']/100) ** year for year in years_data]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=years_data,
            y=amounts,
            mode='lines+markers',
            name='Valeur du Portefeuille',
            line=dict(color=YELLOW, width=2),
            marker=dict(color=YELLOW, size=8)
        ))
        
        fig.update_layout(
            title='Évolution de la Valeur du Portefeuille',
            xaxis_title='Années',
            yaxis_title='Valeur (MAD)',
            plot_bgcolor=BLACK,
            paper_bgcolor=BLACK,
            font=dict(color=YELLOW),
            xaxis=dict(gridcolor=RED),
            yaxis=dict(gridcolor=RED)
        )
        
        st.plotly_chart(fig, use_container_width=True)

    # Coaching Popup (moved to the end)
    st.markdown(f"""
        <div style='background-color: {BLACK}; border-radius: 10px; padding: 20px; margin-top: 30px; border: 2px solid {YELLOW};'>
            <div style='text-align: center;'>
                <h3 style='color: {YELLOW}; margin-bottom: 15px;'>🚀 Coaching Personnalisé Bourse de Casablanca</h3>
                <p style='color: {YELLOW}; margin-bottom: 20px;'>
                    Prêt à investir en Bourse de Casablanca ? Apprenez étape par étape avec un coach expérimenté.
                    <br><br>
                    <span style='color: {RED}; font-weight: bold;'>⚠️ Important:</span> Je ne travaille qu'avec des personnes sérieuses et motivées. Le coaching est un investissement unique qui vous donne accès à :
                </p>
                <div style='display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 20px;'>
                    <div style='background-color: {BLACK}; padding: 15px; border-radius: 5px; border: 1px solid {YELLOW};'>
                        <div style='color: {YELLOW}; font-size: 14px;'>📊 Analyse Technique</div>
                        <div style='color: {YELLOW}; font-size: 12px;'>Apprenez à lire les graphiques et les indicateurs</div>
                    </div>
                    <div style='background-color: {BLACK}; padding: 15px; border-radius: 5px; border: 1px solid {YELLOW};'>
                        <div style='color: {YELLOW}; font-size: 14px;'>📈 Analyse Fondamentale</div>
                        <div style='color: {YELLOW}; font-size: 12px;'>Comprenez les fondamentaux des entreprises</div>
                    </div>
                    <div style='background-color: {BLACK}; padding: 15px; border-radius: 5px; border: 1px solid {YELLOW};'>
                        <div style='color: {YELLOW}; font-size: 14px;'>💰 Gestion de Portefeuille</div>
                        <div style='color: {YELLOW}; font-size: 12px;'>Optimisez votre allocation d'actifs</div>
                    </div>
                </div>
                <div style='background-color: {BLACK}; padding: 15px; border-radius: 5px; border: 1px solid {YELLOW}; margin-bottom: 20px;'>
                    <div style='color: {YELLOW}; font-size: 14px; font-weight: bold;'>🤖 Outils d'IA & Données de Formation</div>
                    <div style='color: {YELLOW}; font-size: 12px; margin-top: 10px;'>
                        • Accès à des outils d'IA pour une meilleure prise de décision financière<br>
                        • Base de données de plus de 10 ans d'historique des actions marocaines<br>
                        • Données disponibles au téléchargement pour l'entraînement de vos modèles d'IA<br>
                        • Analyses prédictives et insights basés sur l'apprentissage automatique
                    </div>
                </div>
                <div style='background-color: {BLACK}; padding: 15px; border-radius: 5px; border: 1px solid {YELLOW}; margin-bottom: 20px;'>
                    <div style='color: {YELLOW}; font-size: 14px; font-weight: bold;'>🎯 Accès au Groupe Privé</div>
                    <div style='color: {YELLOW}; font-size: 12px; margin-top: 10px;'>
                        • Messages audio quotidiens sur la situation du marché<br>
                        • Alertes d'opportunités en temps réel<br>
                        • Réunions en ligne régulières<br>
                        • Réponses à vos questions en privé<br>
                        • Accès à une communauté d'investisseurs sérieux
                    </div>
                </div>
                <div style='margin-top: 20px;'>
                    <a href='https://wa.me/+212679186466' target='_blank' style='
                        background-color: {YELLOW};
                        color: {BLACK};
                        padding: 12px 30px;
                        border-radius: 5px;
                        text-decoration: none;
                        font-weight: bold;
                        display: inline-block;
                        transition: all 0.3s ease;
                    ' onmouseover="this.style.backgroundColor='#CCCC00'" onmouseout="this.style.backgroundColor='#FFFF00'">
                        💬 Contactez-moi sur WhatsApp
                    </a>
                </div>
                <p style='color: {YELLOW}; margin-top: 15px; font-size: 12px;'>
                    Réponse garantie sous 24h | Coaching disponible en français et en arabe
                </p>
            </div>
        </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown(f"""
    <div style='background-color: {BLACK}; color: {YELLOW}; padding: 15px; border-radius: 10px; margin-top: 30px; text-align: center; border: 2px solid {RED};' class='responsive-padding'>
        <div style='display: flex; justify-content: center; gap: 20px; margin-bottom: 10px;' class='footer-container responsive-flex'>
            <a href='https://risk.ma/bourse-de-casablanca' target='_blank' style='color: {YELLOW}; text-decoration: none; font-size: clamp(12px, 2vw, 14px);'>www.risk.ma</a>
            <a href='https://instagram.com/risk.maroc' target='_blank' style='color: {YELLOW}; text-decoration: none; font-size: clamp(12px, 2vw, 14px);'>Instagram</a>
            <a href='https://tiktok.com/@risk.maroc' target='_blank' style='color: {YELLOW}; text-decoration: none; font-size: clamp(12px, 2vw, 14px);'>TikTok</a>
        </div>
        <p style='margin: 0; font-size: clamp(12px, 2vw, 14px);'>© 2025 @risk.maroc - Plateforme d'analyse financière pour la Bourse de Casablanca</p>
        <p style='margin: 0; font-size: clamp(10px, 1.5vw, 12px);'>@dogofallstreets | @risk.maroc | www.risk.ma</p>
    </div>
    """, unsafe_allow_html=True)
