

from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
import pandas as pd

# --- 1. Load and Prepare Data ---
# This line assumes the CSV is in the same folder.
df = pd.read_csv('mineral_production_flourish_ready.csv')

# ... (all your data cleaning and preparation code remains the same) ...

# --- 2. Initialize the Dash App ---
app = Dash(__name__)
server = app.server # <--- ADD THIS LINE

app.title = "Global Mineral Dashboard"

# ... (the rest of your app.layout and @app.callback code remains the same) ...

# --- 5. Run the App Locally ---
# This part is for running it on your Mac. Render will ignore it.
if __name__ == '__main__':
    app.run(debug=True)