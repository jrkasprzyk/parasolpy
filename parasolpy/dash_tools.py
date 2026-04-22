import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, dcc, html

from parasolpy.tradeoff import load_objectives_and_solutions


def load_dash_inputs(output_folder, config_filename=None, solutions_filename=None):
    """Load objective names and solutions DataFrame for a tradeoff Dash app."""
    objective_names, solutions = load_objectives_and_solutions(
        output_folder,
        config_filename=config_filename,
        solutions_filename=solutions_filename,
        return_paths=False,
    )

    default_color_column = next((name for name in objective_names if name in solutions.columns), solutions.columns[0])
    return objective_names, solutions, default_color_column


def build_tradeoff_dash_app(solutions,
                            default_color_column,
                            title="Tradeoff Explorer",
                            default_colorscale="viridis"):
    """Create a Dash app for exploring solution tradeoffs via parallel coordinates."""
    if not isinstance(solutions, pd.DataFrame):
        raise TypeError("Input 'solutions' must be a pandas DataFrame.")
    if solutions.empty:
        raise ValueError("Input 'solutions' cannot be empty.")
    if not isinstance(default_color_column, str) or default_color_column not in solutions.columns:
        raise ValueError("Input 'default_color_column' must be a column name in 'solutions'.")

    colorscales = px.colors.named_colorscales()
    if default_colorscale not in colorscales:
        default_colorscale = "viridis"

    app = Dash()
    app.layout = [
        html.H1(children=title, style={"textAlign": "center"}),
        dcc.Dropdown(options=list(solutions.columns), value=default_color_column, id="colorcolumn"),
        dcc.Dropdown(options=colorscales, value=default_colorscale, id="colorscale"),
        dcc.Graph(figure={}, id="tradeoff-plot"),
    ]

    @app.callback(
        Output("tradeoff-plot", "figure"),
        Input("colorcolumn", "value"),
        Input("colorscale", "value"),
    )
    def update_graph(colorcolumn, colorscale):
        return px.parallel_coordinates(
            solutions,
            color=colorcolumn,
            color_continuous_scale=colorscale,
        )

    return app
