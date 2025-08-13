# --- Make sure to run this cell first in Google Colab: !pip install dash dash-bootstrap-components ---

from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

# --- 1. Load and Prepare Data ---
# Ensure 'mineral_production_flourish_ready.csv' is in the same folder as this script.
try:
    df = pd.read_csv('mineral_production_flourish_ready.csv')
except FileNotFoundError:
    print("Error: 'mineral_production_flourish_ready.csv' not found.")
    print("Please make sure the CSV file is in the same directory as this script.")
    exit()

# --- Data Cleaning and Preparation ---
df['Year'] = pd.to_numeric(df['Year'], errors='coerce').dropna().astype(int)
years = sorted(df['Year'].unique())
home_country = "India"
home_country_color = '#20c997'
unit = "(tonnes)"

# Get unique lists for dropdowns
prod_minerals = sorted(df['Production Mineral'].dropna().unique())
import_minerals = sorted(df['Import Mineral Name'].dropna().unique())
all_minerals = sorted(list(set(prod_minerals + import_minerals)))
all_minerals_with_total = ["--- All Minerals ---"] + all_minerals

known_cols = ['Country', 'Year', 'Production Mineral', 'Production Qty', 'Import Mineral Name', 'Import Qty']
indicator_cols = sorted([col for col in df.columns if df[col].dtype in ['int64', 'float64'] and col not in known_cols and col != 'Year'])

# --- 2. Initialize the Dash App with a modern theme ---
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
app.title = "Global Mineral Dashboard"

# --- 3. Define the App Layout ---
app.layout = dbc.Container(fluid=True, children=[
    # --- Header ---
    html.Div([
        html.H1("Global Mineral & Economic Dashboard", className="display-4 text-center"),
        html.P("Explore mineral trade and economic indicators across the globe.", className="lead text-center")
    ], className="my-4"),

    # --- Control Panel Card ---
    dbc.Card(
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label('Select Mineral', className='fw-bold'),
                    dcc.Dropdown(id='mineral-dropdown', options=[{'label': m, 'value': m} for m in all_minerals_with_total], value='--- All Minerals ---')
                ], width=12, md=4),
                dbc.Col([
                    html.Label('Select Data Type', className='fw-bold'),
                    dcc.Dropdown(id='data-type-dropdown', options=[{'label': 'Production', 'value': 'Production'}, {'label': 'Import', 'value': 'Import'}, {'label': 'Production & Import', 'value': 'Combined'}], value='Combined')
                ], width=12, md=4),
                dbc.Col([
                    html.Label('Select Indicator (Overrides Minerals)', className='fw-bold'),
                    dcc.Dropdown(id='indicator-dropdown', options=[{'label': i, 'value': i} for i in indicator_cols], value=None, placeholder="View an economic indicator...")
                ], width=12, md=4),
            ], className="g-3")
        ]),
        className="mb-4 shadow-sm"
    ),

    # --- Map ---
    dcc.Graph(id='world-map', style={'height': '65vh'}),

    # --- Year Slider ---
    html.Div([
        html.Label('Select Year', className='fw-bold mb-2'),
        dcc.Slider(id='year-slider', min=min(years), max=max(years), value=max(years), marks={str(year): str(year) for year in years}, step=None)
    ], className="p-4")
])

# --- 4. Define Callbacks for Interactivity ---
@app.callback(
    Output('world-map', 'figure'),
    [Input('year-slider', 'value'),
     Input('mineral-dropdown', 'value'),
     Input('data-type-dropdown', 'value'),
     Input('indicator-dropdown', 'value')]
)
def update_map(selected_year, selected_mineral, selected_data_type, selected_indicator):
    year_df = df[df['Year'] == selected_year].copy()
    fig = go.Figure()
    
    # --- Refined Logic: Indicator view takes precedence ---
    if selected_indicator:
        map_data = year_df[['Country', selected_indicator]].dropna()
        z_data, locations, hover_template, colorbar_title, custom_data = map_data[selected_indicator], map_data['Country'], f'<b>%{{location}}</b><br>{selected_indicator}: %{{z:,.2f}}<extra></extra>', selected_indicator, None
    # --- Fallback to Mineral View ---
    else:
        prod_df = year_df.groupby('Country')['Production Qty'].sum().reset_index() if selected_mineral == "--- All Minerals ---" else year_df[df['Production Mineral'] == selected_mineral].groupby('Country')['Production Qty'].sum().reset_index()
        import_df = year_df.groupby('Country')['Import Qty'].sum().reset_index() if selected_mineral == "--- All Minerals ---" else year_df[df['Import Mineral Name'] == selected_mineral].groupby('Country')['Import Qty'].sum().reset_index()

        merged_df = pd.merge(prod_df, import_df, on='Country', how='outer').fillna(0)
        merged_df['Production Qty'] = pd.to_numeric(merged_df['Production Qty'], errors='coerce').fillna(0)
        merged_df['Import Qty'] = pd.to_numeric(merged_df['Import Qty'], errors='coerce').fillna(0)

        if selected_data_type == 'Production':
            display_df = merged_df[merged_df['Production Qty'] > 0].copy()
            z_data, hover_template, custom_data = display_df['Production Qty'], f'<b>%{{location}}</b><br>Production: %{{z:,.0f}} {unit}<extra></extra>', None
        elif selected_data_type == 'Import':
            display_df = merged_df[merged_df['Import Qty'] > 0].copy()
            z_data, hover_template, custom_data = display_df['Import Qty'], f'<b>%{{location}}</b><br>Import: %{{z:,.0f}} {unit}<extra></extra>', None
        else: # Combined
            display_df = merged_df[(merged_df['Production Qty'] > 0) | (merged_df['Import Qty'] > 0)].copy()
            display_df['Combined'] = display_df['Production Qty'] + display_df['Import Qty']
            z_data, hover_template, custom_data = display_df['Combined'], f'<b>%{{location}}</b><br>Production: %{{customdata[0]:,.0f}}<br>Import: %{{customdata[1]:,.0f}}<extra></extra>', display_df[['Production Qty', 'Import Qty']].values

        locations = display_df['Country']
        colorbar_title = f'Quantity {unit}'

    # --- Add Main Map Trace ---
    fig.add_trace(go.Choropleth(
        locations=locations, z=z_data, customdata=custom_data,
        locationmode="country names", colorscale="YlOrRd", showscale=True,
        colorbar_title=colorbar_title, hovertemplate=hover_template, name=''
    ))

    # --- Add Home Country Highlight ---
    if home_country in locations.values:
        fig.add_trace(go.Choropleth(
            locations=[home_country], z=[1], locationmode="country names",
            colorscale=[[0, home_country_color], [1, home_country_color]],
            showscale=False, hoverinfo='none'
        ))

    # --- Update Layout ---
    fig.update_layout(
        geo=dict(
            showframe=False, showcoastlines=False, projection_type='natural earth',
            bgcolor='rgba(0,0,0,0)', landcolor='#E5ECF6'
        ),
        margin=dict(t=10, b=10, l=10, r=10),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )

    return fig

# --- 5. Run the App Locally ---
if __name__ == '__main__':
    app.run(debug=True)
