import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import requests
import io

# Page configuration
st.set_page_config(
    page_title="Global Macro Dashboard",
    page_icon="🌍",
    layout="wide"
)

# Title and description
st.title("🌍 Global Macroeconomic Data Dashboard")
st.markdown("Explore key economic indicators from World Bank and OECD")

# API endpoints
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
            if country['capitalCity']:
                countries.append({
                    'id': country['id'],
                    'name': country['name'],
                    'region': country['region']['value']
                })
        return pd.DataFrame(countries)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_wb_indicator_data(country_codes, indicator_code, start_year=2000, end_year=2023):
    """Fetch indicator data for specified countries from World Bank"""
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

@st.cache_data(ttl=3600)
def get_oecd_countries():
    """Get list of OECD countries with their codes"""
    country_map = {
        'AUS': 'Australia', 'AUT': 'Austria', 'BEL': 'Belgium', 'CAN': 'Canada',
        'CHL': 'Chile', 'COL': 'Colombia', 'CRI': 'Costa Rica', 'CZE': 'Czech Republic',
        'DNK': 'Denmark', 'EST': 'Estonia', 'FIN': 'Finland', 'FRA': 'France',
        'DEU': 'Germany', 'GRC': 'Greece', 'HUN': 'Hungary', 'ISL': 'Iceland',
        'IRL': 'Ireland', 'ISR': 'Israel', 'ITA': 'Italy', 'JPN': 'Japan',
        'KOR': 'South Korea', 'LVA': 'Latvia', 'LTU': 'Lithuania', 'LUX': 'Luxembourg',
        'MEX': 'Mexico', 'NLD': 'Netherlands', 'NZL': 'New Zealand', 'NOR': 'Norway',
        'POL': 'Poland', 'PRT': 'Portugal', 'SVK': 'Slovakia', 'SVN': 'Slovenia',
        'ESP': 'Spain', 'SWE': 'Sweden', 'CHE': 'Switzerland', 'TUR': 'Turkey',
        'GBR': 'United Kingdom', 'USA': 'United States'
    }
    
    return pd.DataFrame([
        {'code': code, 'name': name} 
        for code, name in country_map.items()
    ])

@st.cache_data(ttl=3600)
def get_oecd_data_direct(countries, indicator_key):
    """Fetch OECD data using direct data.oecd.org URLs"""
    
    # Simple indicator codes that work with data.oecd.org
    indicator_map = {
        'Labour Productivity (GDP per hour)': 'lprod',
        'GDP per Hour Worked': 'lprod',
        'Unemployment Rate': 'unemp',
    }
    
    if indicator_key not in indicator_map:
        return pd.DataFrame()
    
    indicator_code = indicator_map[indicator_key]
    all_data = []
    
    for country_code in countries:
        try:
            # Using the simple data.oecd.org format
            url = f"https://data.oecd.org/api/v1/data/{indicator_code}/{country_code}"
            
            response = requests.get(url, headers={'Accept': 'application/json'})
            
            if response.status_code == 200:
                data = response.json()
                
                # Parse the response
                if isinstance(data, list):
                    for entry in data:
                        if 'time' in entry and 'value' in entry:
                            country_name = next((c['name'] for c in get_oecd_countries().to_dict('records') 
                                               if c['code'] == country_code), country_code)
                            all_data.append({
                                'Country': country_name,
                                'Year': int(entry['time']),
                                'Value': float(entry['value'])
                            })
        except Exception as e:
            st.error(f"Error fetching {country_code}: {str(e)}")
            continue
    
    return pd.DataFrame(all_data)

# Simpler approach: Use World Bank for everything including productivity proxies
@st.cache_data(ttl=3600) 
def get_productivity_proxy_data(country_codes, start_year=2000, end_year=2023):
    """Get productivity-related indicators from World Bank"""
    # GDP per person employed is a good proxy for labor productivity
    return get_wb_indicator_data(country_codes, 'SL.GDP.PCAP.EM.KD', start_year, end_year)

# Define economic indicators
wb_indicators = {
    'GDP Growth (annual %)': 'NY.GDP.MKTP.KD.ZG',
    'GDP per capita (current US$)': 'NY.GDP.PCAP.CD',
    'GDP per capita, PPP (constant 2017 international $)': 'NY.GDP.PCAP.PP.KD',
    'GDP per person employed (constant 2021 PPP $)': 'SL.GDP.PCAP.EM.KD',
    'Inflation (consumer prices %)': 'FP.CPI.TOTL.ZG',
    'Unemployment (% of labor force)': 'SL.UEM.TOTL.ZS',
    'Labor Force Participation Rate (%)': 'SL.TLF.CACT.ZS',
    'Employment to Population Ratio (%)': 'SL.EMP.TOTL.SP.ZS',
    'Gross Capital Formation (% of GDP)': 'NE.GDI.TOTL.ZS',
    'Foreign Direct Investment (% of GDP)': 'BX.KLT.DINV.WD.GD.ZS',
    'Trade (% of GDP)': 'NE.TRD.GNFS.ZS',
    'Government Debt (% of GDP)': 'GC.DOD.TOTL.GD.ZS',
    'Research and Development (% of GDP)': 'GB.XPD.RSDV.GD.ZS',
    'Population, total': 'SP.POP.TOTL',
}

# Sidebar for user inputs
st.sidebar.header("📊 Data Selection")

countries_df = get_countries()

if not countries_df.empty:
    regions = ['All'] + sorted(countries_df['region'].unique().tolist())
    selected_region = st.sidebar.selectbox("Select Region", regions)
    
    if selected_region != 'All':
        filtered_countries = countries_df[countries_df['region'] == selected_region]
    else:
        filtered_countries = countries_df
    
    default_countries = ['United States', 'China', 'Germany', 'Japan', 'United Kingdom']
    available_defaults = [c for c in default_countries if c in filtered_countries['name'].values]
    
    selected_countries = st.sidebar.multiselect(
        "Select Countries",
        options=filtered_countries['name'].tolist(),
        default=available_defaults[:3] if available_defaults else filtered_countries['name'].head(3).tolist()
    )
    
    selected_indicator = st.sidebar.selectbox(
        "Select Economic Indicator",
        options=list(wb_indicators.keys())
    )
    
    indicator_code = wb_indicators[selected_indicator]
    
    col1, col2 = st.sidebar.columns(2)
    start_year = col1.number_input("Start Year", min_value=1960, max_value=2023, value=2000)
    end_year = col2.number_input("End Year", min_value=1960, max_value=2023, value=2023)
    
    if start_year > end_year:
        st.sidebar.error("⚠️ Start year must be before end year")
    
    if selected_countries and st.sidebar.button("📈 Load Data", type="primary"):
        if start_year > end_year:
            st.error("⚠️ Start year must be before end year")
        else:
            with st.spinner("Fetching data from World Bank..."):
                country_codes = filtered_countries[filtered_countries['name'].isin(selected_countries)]['id'].tolist()
                
                df = get_wb_indicator_data(country_codes, indicator_code, start_year, end_year)
                
                if not df.empty:
                    actual_start = df['Year'].min()
                    actual_end = df['Year'].max()
                    
                    if actual_start > start_year or actual_end < end_year:
                        st.info(f"ℹ️ Data available from {actual_start} to {actual_end}.")
                    
                    st.subheader(f"📊 {selected_indicator}")
                    st.caption("Source: World Bank Open Data")
                    
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
                    
                    with st.expander("📋 View Raw Data"):
                        pivot_df = df.pivot(index='Year', columns='Country', values='Value')
                        st.dataframe(pivot_df.sort_index(ascending=False), use_container_width=True)
                        
                        csv = pivot_df.to_csv()
                        st.download_button(
                            label="⬇️ Download CSV",
                            data=csv,
                            file_name=f"{selected_indicator.replace(' ', '_')}_{start_year}_{end_year}.csv",
                            mime="text/csv"
                        )
                else:
                    st.warning("⚠️ No data available for the selected countries and time period.")
else:
    st.error("Unable to load country data. Please check your internet connection.")

with st.sidebar.expander("ℹ️ About"):
    st.markdown("""
    This dashboard provides access to macroeconomic indicators from the World Bank.
    
    **Available Indicators** (1960-2023)
    
    *Economic Growth & Output:*
    - GDP Growth & Per Capita (current & PPP)
    - GDP per person employed (labor productivity)
    
    *Labor Market:*
    - Unemployment Rate
    - Labor Force Participation
    - Employment to Population Ratio
    
    *Investment & Capital:*
    - Gross Capital Formation (investment rate)
    - Foreign Direct Investment
    - Research and Development expenditure
    
    *Trade & Fiscal:*
    - Trade as % of GDP
    - Government Debt
    - Inflation (CPI)
    
    *Demographics:*
    - Total Population
    
    **Data Source:** World Bank Open Data
    """)