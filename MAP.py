# --- Make sure to run this cell first in Google Colab: !pip install dash dash-bootstrap-components gunicorn ---

from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

# --- 1. Initialize the Dash App with a modern theme ---
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server # This line is crucial for Render/Gunicorn
app.title = "Global Mineral Dashboard"

# --- 2. Load Data and Define Layout ---
# This approach ensures the layout is always defined, preventing crashes.
try:
    df = pd.read_csv('mineral_production_flourish_ready.csv')
    
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

    # --- Define the Main App Layout ---
    app.layout = dbc.Container(fluid=True, children=[
        html.Div([
            html.H1("Global Mineral & Economic Dashboard", className="display-4 text-center"),
            html.P("Explore mineral trade and economic indicators across the globe.", className="lead text-center")
        ], className="my-4"),
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
        dcc.Graph(id='world-map', style={'height': '65vh'}),
        html.Div([
            html.Label('Select Year', className='fw-bold mb-2'),
            dcc.Slider(id='year-slider', min=min(years), max=max(years), value=max(years), marks={str(year): str(year) for year in years}, step=None)
        ], className="p-4")
    ])

except FileNotFoundError:
    # --- Define an Error Layout if the data file is not found ---
    app.layout = dbc.Container([
        html.H1("Error: Data File Not Found", className="text-danger"),
        html.Hr(),
        html.P("The application could not start because the required data file 'mineral_production_flourish_ready.csv' was not found."),
        html.P("Please ensure the file has been uploaded to the root of the GitHub repository and then trigger a new deployment on Render.")
    ], className="p-5 mt-5 bg-light border rounded")


# --- 4. Define Callbacks for Interactivity ---
# We only define callbacks if the data was loaded successfully
if 'df' in locals():
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
        
        if selected_indicator:
            map_data = year_df[['Country', selected_indicator]].dropna()
            z_data, locations, hover_template, colorbar_title, custom_data = map_data[selected_indicator], map_data['Country'], f'<b>%{{location}}</b><br>{selected_indicator}: %{{z:,.2f}}<extra></extra>', selected_indicator, None
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
                z_data, hover_template, custom_data = display_df['Combined'], '<b>%{location}</b><br>Production: %{customdata[0]:,.0f}<br>Import: %{customdata[1]:,.0f}<extra></extra>', display_df[['Production Qty', 'Import Qty']].values

            locations = display_df['Country']
            colorbar_title = f'Quantity {unit}'

        fig.add_trace(go.Choropleth(
            locations=locations, z=z_data, customdata=custom_data,
            locationmode="country names", colorscale="YlOrRd", showscale=True,
            colorbar_title=colorbar_title, hovertemplate=hover_template, name=''
        ))

        if home_country in locations.values:
            fig.add_trace(go.Choropleth(
                locations=[home_country], z=[1], locationmode="country names",
                colorscale=[[0, home_country_color], [1, home_country_color]],
                showscale=False, hoverinfo='none'
            ))

        fig.update_layout(
            geo=dict(showframe=False, showcoastlines=False, projection_type='natural earth', bgcolor='rgba(0,0,0,0)', landcolor='#E5ECF6'),
            margin=dict(t=10, b=10, l=10, r=10),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        return fig

# --- 5. Run the App ---
if __name__ == '__main__':
    app.run_server(debug=True)
