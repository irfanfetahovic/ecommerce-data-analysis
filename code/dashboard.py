import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# -----------------------------
# Page configuration
# -----------------------------
st.set_page_config(
    page_title="Sales Analytics Dashboard",
    page_icon=":bar_chart:",
    layout="wide"
)

# -----------------------------
# Data paths
# -----------------------------
base_path = os.path.dirname(__file__)
data_path = os.path.join(base_path, "../data")

# -----------------------------
# Simple styling
# -----------------------------
st.markdown("""
    <style>
    .metric-card {
        border: 1px solid #eee;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #0f2537;
    }
    .metric-label {
        font-size: 14px;
        color: #666;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------
# Load data
# -----------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(os.path.join(data_path, "data.csv"), encoding='ISO-8859-1')
    df = df.dropna(subset=['CustomerID'])
    df = df[df['Quantity'] > 0]
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    df['TotalPrice'] = df['Quantity'] * df['UnitPrice']
    df = df.drop_duplicates()
    return df

df = load_data()

# Last updated
last_updated = df['InvoiceDate'].max().strftime('%Y-%m-%d')

# -----------------------------
# Dashboard Title
# -----------------------------
st.title("Sales Analytics Dashboard")
st.markdown("Interactive analysis of sales performance and customer behavior")

# -----------------------------
# Sidebar Filters
# -----------------------------
st.sidebar.header("Filters")

# Date range
min_date = df['InvoiceDate'].min().date()
max_date = df['InvoiceDate'].max().date()
date_range = st.sidebar.date_input(
    "Date Range",
    [min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

# Country filter
countries = ['All'] + sorted(df['Country'].unique().tolist())
selected_country = st.sidebar.selectbox("Country", countries)

# Apply filters
mask = (df['InvoiceDate'].dt.date >= date_range[0]) & (df['InvoiceDate'].dt.date <= date_range[1])
if selected_country != 'All':
    mask &= (df['Country'] == selected_country)
filtered_df = df[mask].copy()

# -----------------------------
# Key Metrics
# -----------------------------
col1, col2, col3, col4 = st.columns(4)

total_sales = filtered_df['TotalPrice'].sum()
total_orders = filtered_df['InvoiceNo'].nunique()
total_customers = filtered_df['CustomerID'].nunique()
avg_order_value = total_sales / total_orders if total_orders > 0 else 0

metrics = [
    ("Total Sales", f"${total_sales:,.2f}"),
    ("Total Orders", f"{total_orders:,}"),
    ("Total Customers", f"{total_customers:,}"),
    ("Avg Order Value", f"${avg_order_value:.2f}")
]

for col, (label, value) in zip([col1, col2, col3, col4], metrics):
    col.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{value}</div>
            <div class="metric-label">{label}</div>
        </div>
    """, unsafe_allow_html=True)

# -----------------------------
# Sales Trends
# -----------------------------
st.header("Sales Analysis")
sales_tabs = st.tabs(["Monthly Trend", "Country Trends", "Hourly Pattern"])

# Monthly sales trend
with sales_tabs[0]:
    monthly_sales = filtered_df.groupby(filtered_df['InvoiceDate'].dt.to_period('M'))['TotalPrice'].sum()
    fig_sales = px.line(
        x=monthly_sales.index.astype(str),
        y=monthly_sales.values,
        title='Monthly Sales Trend',
        labels={'x': 'Month', 'y': 'Sales ($)'}
    )
    st.plotly_chart(fig_sales, use_container_width=True)
    # CSV download
    csv = monthly_sales.to_frame(name='Sales').to_csv(index=True).encode('utf-8')
    st.download_button("Download monthly sales (CSV)", data=csv, file_name="monthly_sales.csv", mime="text/csv")

# Monthly sales by country
with sales_tabs[1]:
    monthly_country_sales = (filtered_df.groupby([filtered_df['InvoiceDate'].dt.to_period('M'), 'Country'])
                            ['TotalPrice'].sum().reset_index())
    monthly_country_sales.rename(columns={'InvoiceDate': 'Month', 'TotalPrice':'Revenue'}, inplace=True)
    monthly_country_sales['Month'] = monthly_country_sales['Month'].astype(str)
    top_countries = (filtered_df.groupby('Country')['TotalPrice'].sum()
                     .sort_values(ascending=False).head(10).index)
    monthly_country_sales = monthly_country_sales[monthly_country_sales['Country'].isin(top_countries)]
    fig_country_trend = px.line(
        monthly_country_sales,
        x='Month',
        y='Revenue',
        color='Country',
        category_orders={'Country': top_countries},
        title='Monthly Sales by Top 10 Countries',
        labels={'Revenue': 'Sales ($)'}
    )
    st.plotly_chart(fig_country_trend, use_container_width=True)

# Hourly sales pattern
with sales_tabs[2]:
    filtered_df['Hour'] = filtered_df['InvoiceDate'].dt.hour
    hourly_sales = filtered_df.groupby('Hour')['TotalPrice'].sum()
    fig_hourly = px.bar(
        x=hourly_sales.index,
        y=hourly_sales.values,
        title='Sales Distribution by Hour of Day',
        labels={'x': 'Hour', 'y': 'Sales ($)'}
    )
    st.plotly_chart(fig_hourly, use_container_width=True)

# -----------------------------
# Product & Country Performance
# -----------------------------
st.header("Product & Country Performance")
col1, col2 = st.columns(2)

# Top Products
with col1:
    top_products_data = (filtered_df.groupby('Description')['Quantity']
                         .sum()
                         .sort_values(ascending=True)
                         .tail(10))
    fig_products = px.bar(
        x=top_products_data.values,
        y=top_products_data.index,
        orientation='h',
        labels={'x': 'Units Sold', 'y': 'Product'},
        title='Top 10 Products by Quantity'
    )
    st.plotly_chart(fig_products, use_container_width=True)

# Top Countries
with col2:
    top_countries_data = (filtered_df.groupby('Country')['TotalPrice']
                          .sum()
                          .sort_values(ascending=True)
                          .tail(10))
    fig_countries = px.bar(
        x=top_countries_data.values,
        y=top_countries_data.index,
        orientation='h',
        labels={'x': 'Sales ($)', 'y': 'Country'},
        title='Top 10 Countries by Sales'
    )
    st.plotly_chart(fig_countries, use_container_width=True)

# -----------------------------
# Customer & Correlation Insights
# -----------------------------
st.header("Customer & Product Insights")
col1, col2 = st.columns(2)

# Customer orders distribution
with col1:
    customer_orders = filtered_df.groupby('CustomerID')['InvoiceNo'].nunique()
    customer_orders.name = "Number of Orders"
    fig_customer_orders = px.histogram(
        customer_orders,
        title='Distribution of Orders per Customer',
        labels={'value': 'Number of Orders', 'count': 'Number of Customers'}
    )
    fig_customer_orders.update_yaxes(title_text="Number of Customers")
    st.plotly_chart(fig_customer_orders, use_container_width=True)

# Correlation heatmap
with col2:
    corr_matrix = filtered_df[['Quantity', 'UnitPrice', 'TotalPrice']].corr()
    fig_corr = px.imshow(
        corr_matrix,
        title='Correlation Heatmap',
        color_continuous_scale='RdBu_r',
        aspect='auto'
    )
    fig_corr.update_traces(text=corr_matrix.round(2), texttemplate="%{text}")
    st.plotly_chart(fig_corr, use_container_width=True)

# -----------------------------
# Footer
# -----------------------------
st.markdown("---")
st.caption(f"Data last updated: {last_updated}")
