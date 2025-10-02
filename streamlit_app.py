import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import requests

# Page configuration
st.set_page_config(
    page_title="Global Macro Dashboard",
    page_icon="🌍",
    layout="wide"
)

# Title and description
st.title("🌍 Global Macroeconomic Data Dashboard")
st.markdown("Explore key economic indicators from countries around the world using World Bank data")

# World Bank API endpoint
WB_API = "https://api.worldbank.org/v2"

@st.cache_data(ttl=3600)
def get_countries():
    """Fetch list of countries from World Bank API"""
    url = f"{WB_API}/country?format=json&per_page=300"
    try:
        response = requests.get(url)
        data = response.json()
        countries = []
        for country in data[1]:
            if country['capitalCity']:  # Filter for actual countries
                countries.append({
                    'id': country['id'],
                    'name': country['name'],
                    'region': country['region']['value']
                })
        return pd.DataFrame(countries)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_indicator_data(country_codes, indicator_code, start_year=2000, end_year=2023):
    """Fetch indicator data for specified countries"""
    all_data = []
    
    for country in country_codes:
        url = f"{WB_API}/country/{country}/indicator/{indicator_code}?format=json&per_page=100&date={start_year}:{end_year}"
        try:
            response = requests.get(url)
            data = response.json()
            
            if len(data) > 1 and data[1]:
                for entry in data[1]:
                    if entry['value'] is not None:
                        all_data.append({
                            'Country': entry['country']['value'],
                            'Year': int(entry['date']),
                            'Value': entry['value']
                        })
        except:
            continue
    
    return pd.DataFrame(all_data)

# Define economic indicators
indicators = {
    'GDP Growth (annual %)': 'NY.GDP.MKTP.KD.ZG',
    'GDP per capita (current US$)': 'NY.GDP.PCAP.CD',
    'Inflation (consumer prices %)': 'FP.CPI.TOTL.ZG',
    'Unemployment (% of labor force)': 'SL.UEM.TOTL.ZS',
    'Foreign Direct Investment (% of GDP)': 'BX.KLT.DINV.WD.GD.ZS',
    'Trade (% of GDP)': 'NE.TRD.GNFS.ZS',
    'Government Debt (% of GDP)': 'GC.DOD.TOTL.GD.ZS',
    'Population, total': 'SP.POP.TOTL'
}

# Sidebar for user inputs
st.sidebar.header("📊 Data Selection")

# Load countries
countries_df = get_countries()

if not countries_df.empty:
    # Region filter
    regions = ['All'] + sorted(countries_df['region'].unique().tolist())
    selected_region = st.sidebar.selectbox("Select Region", regions)
    
    # Filter countries by region
    if selected_region != 'All':
        filtered_countries = countries_df[countries_df['region'] == selected_region]
    else:
        filtered_countries = countries_df
    
    # Country selection
    default_countries = ['United States', 'China', 'Germany', 'Japan', 'United Kingdom']
    available_defaults = [c for c in default_countries if c in filtered_countries['name'].values]
    
    selected_countries = st.sidebar.multiselect(
        "Select Countries",
        options=filtered_countries['name'].tolist(),
        default=available_defaults[:3] if available_defaults else filtered_countries['name'].head(3).tolist()
    )
    
    # Indicator selection
    selected_indicator = st.sidebar.selectbox(
        "Select Economic Indicator",
        options=list(indicators.keys())
    )
    
    # Year range
    col1, col2 = st.sidebar.columns(2)
    start_year = col1.number_input("Start Year", min_value=1960, max_value=2023, value=2000)
    end_year = col2.number_input("End Year", min_value=1960, max_value=2023, value=2023)
    
    if start_year > end_year:
        st.sidebar.error("⚠️ Start year must be before end year")
    
    # Fetch and display data
    if selected_countries and st.sidebar.button("📈 Load Data", type="primary"):
        if start_year > end_year:
            st.error("⚠️ Start year must be before end year")
        else:
            with st.spinner("Fetching data from World Bank..."):
                # Get country codes
                country_codes = filtered_countries[filtered_countries['name'].isin(selected_countries)]['id'].tolist()
                
                # Fetch data
                indicator_code = indicators[selected_indicator]
                df = get_indicator_data(country_codes, indicator_code, start_year, end_year)
                
                if not df.empty:
                    # Check actual data range
                    actual_start = df['Year'].min()
                    actual_end = df['Year'].max()
                    
                    if actual_start > start_year or actual_end < end_year:
                        st.info(f"ℹ️ Data available from {actual_start} to {actual_end}. Some requested years may not have data.")
                    
                    # Display metrics
                    st.subheader(f"📊 {selected_indicator}")
                    
                    # Latest year metrics
                    latest_year = df['Year'].max()
                    latest_data = df[df['Year'] == latest_year]
                    
                    cols = st.columns(len(selected_countries))
                    for idx, country in enumerate(selected_countries):
                        country_latest = latest_data[latest_data['Country'] == country]
                        if not country_latest.empty:
                            value = country_latest['Value'].values[0]
                            cols[idx].metric(
                                label=country,
                                value=f"{value:,.2f}",
                                delta=f"Year: {latest_year}"
                            )
                    
                    # Time series chart
                    st.subheader("📈 Time Series")
                    fig = px.line(
                        df,
                        x='Year',
                        y='Value',
                        color='Country',
                        title=f"{selected_indicator} Over Time",
                        labels={'Value': selected_indicator},
                        markers=True
                    )
                    fig.update_layout(
                        hovermode='x unified',
                        height=500,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Bar chart comparison for latest year
                    st.subheader(f"📊 Comparison for {latest_year}")
                    fig_bar = px.bar(
                        latest_data.sort_values('Value', ascending=False),
                        x='Country',
                        y='Value',
                        color='Value',
                        title=f"{selected_indicator} - {latest_year}",
                        labels={'Value': selected_indicator},
                        color_continuous_scale='viridis'
                    )
                    fig_bar.update_layout(height=400)
                    st.plotly_chart(fig_bar, use_container_width=True)
                    
                    # Data table
                    with st.expander("📋 View Raw Data"):
                        pivot_df = df.pivot(index='Year', columns='Country', values='Value')
                        st.dataframe(pivot_df.sort_index(ascending=False), use_container_width=True)
                        
                        # Download button
                        csv = pivot_df.to_csv()
                        st.download_button(
                            label="⬇️ Download CSV",
                            data=csv,
                            file_name=f"{selected_indicator.replace(' ', '_')}_{start_year}_{end_year}.csv",
                            mime="text/csv"
                        )
                else:
                    st.warning("⚠️ No data available for the selected countries and time period. Try a different year range (most data starts from 1960).")
    
    # Information section
    with st.sidebar.expander("ℹ️ About"):
        st.markdown("""
        This dashboard provides access to key macroeconomic indicators from the World Bank database.
        
        **Data Source:** World Bank Open Data
        
        **Data Availability:** Most indicators have data from 1960 onwards. Some indicators may have limited historical data.
        
        **Available Indicators:**
        - GDP Growth & Per Capita
        - Inflation Rates
        - Unemployment
        - Foreign Investment
        - Trade & Government Debt
        - Population Statistics
        """)
else:
    st.error("Unable to load country data. Please check your internet connection.")