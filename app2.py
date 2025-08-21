# --- Make sure to run this cell first: !pip install dash dash-bootstrap-components gunicorn pandas scikit-learn ---

from dash import Dash, dcc, html, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

# --- 1. Initialize the Dash App with a modern theme ---
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server
app.title = "Global Mineral Dashboard"

# --- 2. Load Data and Define Layout ---
try:
    df = pd.read_csv('final 1.csv')

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

    # Identify numeric columns for indicators
    known_cols = ['Country', 'Year', 'Production Mineral', 'Production Qty', 'Import Mineral Name', 'Import Qty']
    indicator_cols = sorted([col for col in df.columns if df[col].dtype in ['int64', 'float64'] and col not in known_cols and col != 'Year'])

    # --- Define the Main App Layout with Tabs ---
    app.layout = dbc.Container(fluid=True, children=[
        # Header section
        html.Div([
            html.H1("Global Mineral & Economic Dashboard", className="display-4 text-center"),
            html.P("Explore mineral trade and economic indicators across the globe.", className="lead text-center")
        ], className="my-4"),

        # Tab structure
        dcc.Tabs(id="app-tabs", value='tab-overview', children=[
            # Overview Tab
            dcc.Tab(label='Overview', value='tab-overview', children=[
                dbc.Card(
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col(dcc.Dropdown(id='mineral-dropdown', options=[{'label': m, 'value': m} for m in all_minerals_with_total], value='--- All Minerals ---'), width=12, md=4),
                            dbc.Col(dcc.Dropdown(id='data-type-dropdown', options=[{'label': 'Production', 'value': 'Production'}, {'label': 'Import', 'value': 'Import'}, {'label': 'Production & Import', 'value': 'Combined'}], value='Combined'), width=12, md=4),
                            dbc.Col(dcc.Dropdown(id='indicator-dropdown', options=[{'label': i, 'value': i} for i in indicator_cols], value=None, placeholder="View an economic indicator..."), width=12, md=4),
                        ], className="g-3")
                    ]), className="mt-4 mb-4 shadow-sm"
                ),
                dcc.Graph(id='world-map', style={'height': '65vh'}),
            ]),
            # Analysis Tab
            dcc.Tab(label='Analysis', value='tab-analysis', children=[
                dbc.Card(
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Label('Select Mineral to Analyze', className='fw-bold'),
                                dcc.Dropdown(id='analysis-mineral-dropdown', options=[{'label': m, 'value': m} for m in all_minerals], placeholder="Select a mineral...")
                            ], width=12, md=8),
                            dbc.Col(dbc.Button("Run Analysis", id="run-analysis-button", color="primary", className="w-100 mt-4"), width=12, md=4),
                        ], className="g-3 align-items-end")
                    ]), className="mt-4 mb-4 shadow-sm"
                ),
                dbc.Row([
                    dbc.Col(dcc.Graph(id='analysis-map', style={'height': '65vh'}), md=8),
                    dbc.Col(html.Div([html.H4("Top 10 Potential Trading Partners"), html.Div(id='analysis-results')]), md=4)
                ])
            ]),
        ]),
        
        # Shared Year Slider
        html.Div([
            html.Label('Select Year', className='fw-bold mb-2'),
            dcc.Slider(id='year-slider', min=min(years), max=max(years), value=max(years), marks={str(year): str(year) for year in years}, step=None)
        ], className="p-4")
    ])

except FileNotFoundError:
    app.layout = dbc.Container([
        html.H1("Error: Data File Not Found", className="text-danger"),
        html.P("'final 1.csv' was not found. Please ensure it's in the same directory.")
    ], className="p-5 mt-5 bg-light border rounded")

# --- 4. Define Callbacks ---
if 'df' in locals():
    # Callback for the Overview Tab
    @app.callback(
        Output('world-map', 'figure'),
        [Input('year-slider', 'value'),
         Input('mineral-dropdown', 'value'),
         Input('data-type-dropdown', 'value'),
         Input('indicator-dropdown', 'value')]
    )
    def update_overview_map(selected_year, selected_mineral, data_type, indicator):
        year_df = df[df['Year'] == selected_year].copy()
        fig = go.Figure()
        
        locations = pd.Series(dtype='str')
        z_data, custom_data, hover_template, colorbar_title = None, None, '', ''

        if indicator:
            map_data = year_df[['Country', indicator]].dropna()
            z_data, locations = map_data[indicator], map_data['Country']
            hover_template, colorbar_title = f'<b>%{{location}}</b><br>{indicator}: %{{z:,.2f}}<extra></extra>', indicator
        else:
            prod_df = year_df.groupby('Country')['Production Qty'].sum().reset_index() if selected_mineral == "--- All Minerals ---" else year_df[year_df['Production Mineral'] == selected_mineral].groupby('Country')['Production Qty'].sum().reset_index()
            import_df = year_df.groupby('Country')['Import Qty'].sum().reset_index() if selected_mineral == "--- All Minerals ---" else year_df[year_df['Import Mineral Name'] == selected_mineral].groupby('Country')['Import Qty'].sum().reset_index()
            merged_df = pd.merge(prod_df, import_df, on='Country', how='outer').fillna(0)

            if data_type == 'Production':
                display_df = merged_df[merged_df['Production Qty'] > 0]
                z_data, hover_template = display_df['Production Qty'], f'<b>%{{location}}</b><br>Production: %{{z:,.0f}} {unit}<extra></extra>'
            elif data_type == 'Import':
                display_df = merged_df[merged_df['Import Qty'] > 0]
                z_data, hover_template = display_df['Import Qty'], f'<b>%{{location}}</b><br>Import: %{{z:,.0f}} {unit}<extra></extra>'
            else:
                display_df = merged_df[(merged_df['Production Qty'] > 0) | (merged_df['Import Qty'] > 0)]
                display_df['Combined'] = display_df['Production Qty'] + display_df['Import Qty']
                z_data, hover_template, custom_data = display_df['Combined'], '<b>%{location}</b><br>Production: %{customdata[0]:,.0f}<br>Import: %{customdata[1]:,.0f}<extra></extra>', display_df[['Production Qty', 'Import Qty']].values
            
            locations = display_df['Country']
            colorbar_title = f'Quantity {unit}'

        if not locations.empty:
            fig.add_trace(go.Choropleth(locations=locations, z=z_data, customdata=custom_data, locationmode="country names", colorscale="YlOrRd", colorbar_title=colorbar_title, hovertemplate=hover_template, name=''))
        
        fig.add_trace(go.Choropleth(locations=[home_country], z=[1], locationmode="country names", colorscale=[[0, home_country_color], [1, home_country_color]], showscale=False, hoverinfo='skip'))
        fig.update_layout(geo=dict(showframe=False, showcoastlines=False, projection_type='natural earth', bgcolor='rgba(0,0,0,0)', landcolor='#E5ECF6'), margin=dict(t=10, b=10, l=10, r=10))
        return fig

    # Callback for the Analysis Tab
    @app.callback(
        [Output('analysis-map', 'figure'),
         Output('analysis-results', 'children')],
        [Input('run-analysis-button', 'n_clicks')],
        [State('year-slider', 'value'),
         State('analysis-mineral-dropdown', 'value')]
    )
    def update_analysis_tab(n_clicks, selected_year, selected_mineral):
        if n_clicks is None or not selected_mineral:
            return go.Figure().update_layout(title="Please select a mineral and run the analysis."), "Please make your selection and click 'Run Analysis'."

        # 1. Filter data for the selected year
        year_df = df[df['Year'] == selected_year].copy()

        # 2. Get trade data (production and import) for the selected mineral
        prod_df = year_df[year_df['Production Mineral'] == selected_mineral].groupby('Country')['Production Qty'].sum().reset_index()
        import_df = year_df[year_df['Import Mineral Name'] == selected_mineral].groupby('Country')['Import Qty'].sum().reset_index()
        trade_df = pd.merge(prod_df, import_df, on='Country', how='outer').fillna(0)

        # 3. Get indicator data for all countries
        indicator_data_df = year_df[['Country'] + indicator_cols].drop_duplicates(subset=['Country'])

        # 4. Merge trade data with indicator data
        analysis_df = pd.merge(trade_df, indicator_data_df, on='Country', how='left')
        
        # --- MODIFICATION START: Handle missing indicator values ---
        # Instead of dropping rows with missing data, fill them with the mean of that column for the year.
        # This makes the analysis more robust to incomplete data.
        for col in indicator_cols:
            mean_value = analysis_df[col].mean()
            analysis_df[col].fillna(mean_value, inplace=True)
        # --- MODIFICATION END ---
        
        # 5. Define all factors and ensure there are countries to analyze
        factors = ['Production Qty', 'Import Qty'] + indicator_cols
        analysis_df.dropna(subset=['Production Qty', 'Import Qty'], inplace=True) # Still drop if trade data is missing

        if analysis_df.empty:
            return go.Figure().update_layout(title=f"No trade data available for {selected_mineral} in {selected_year}."), "No countries found with production or import data for the selected mineral."

        # 6. Normalize the factor columns (scale to 0-1 range)
        scaler = MinMaxScaler()
        analysis_df[factors] = scaler.fit_transform(analysis_df[factors])

        # 7. Calculate a composite score (equal weighting for simplicity)
        analysis_df['Score'] = analysis_df[factors].mean(axis=1)
        
        # 8. Rank countries based on the score
        analysis_df['Rank'] = analysis_df['Score'].rank(ascending=False, method='dense').astype(int)
        analysis_df = analysis_df.sort_values('Rank')

        # Create the analysis map
        fig = go.Figure(go.Choropleth(
            locations=analysis_df['Country'],
            z=analysis_df['Rank'],
            locationmode='country names',
            colorscale='viridis_r',
            reversescale=True,
            colorbar_title='Rank',
            hovertemplate='<b>%{location}</b><br>Rank: %{z}<br>Score: %{customdata[0]:.3f}<extra></extra>',
            customdata=analysis_df[['Score']].values
        ))
        fig.update_layout(title=f'Top Trading Partners for {selected_mineral} in {selected_year}', geo=dict(landcolor='#E5ECF6'), margin=dict(t=40, b=10, l=10, r=10))

        # Create the results table for the Top 10
        top_10_df = analysis_df.head(10)
        table_header = [html.Thead(html.Tr([html.Th("Rank"), html.Th("Country"), html.Th("Score")]))]
        table_body = [html.Tbody([
            html.Tr([
                html.Td(row['Rank']),
                html.Td(row['Country']),
                html.Td(f"{row['Score']:.3f}")
            ]) for index, row in top_10_df.iterrows()
        ])]
        results_table = dbc.Table(table_header + table_body, bordered=True, striped=True, hover=True, responsive=True, className="mt-3")

        return fig, results_table

# --- 5. Run the App ---
if __name__ == '__main__':
    app.run(debug=True)
