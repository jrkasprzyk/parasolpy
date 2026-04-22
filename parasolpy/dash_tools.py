import argparse

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
    """Build a Dash app for exploring solution tradeoffs via parallel coordinates.

    The returned app renders a parallel-coordinates plot of ``solutions`` and
    exposes two dropdowns: one to select which column drives the color scale
    and one to pick a named Plotly colorscale. Both dropdowns are wired to a
    callback that redraws the figure; no other state is maintained.

    Args:
        solutions: Non-empty ``pandas.DataFrame`` where each row is a candidate
            solution and each column is either an objective or a decision
            variable. All columns are shown as axes in the parallel-coordinates
            plot.
        default_color_column: Name of the column used to color lines on initial
            render. Must be a column of ``solutions``.
        title: Heading rendered above the plot.
        default_colorscale: Name of a Plotly continuous colorscale (see
            ``plotly.express.colors.named_colorscales()``). Falls back to
            ``"viridis"`` if the given name is not recognized.

    Returns:
        dash.Dash: A configured app. Call ``app.run(...)`` (or pass it to
        :func:`run_tradeoff_dash_app`) to serve it.

    Raises:
        TypeError: If ``solutions`` is not a DataFrame.
        ValueError: If ``solutions`` is empty, or if ``default_color_column``
            is not one of its columns.

    Example:
        >>> names, solutions, default_col = load_dash_inputs("output/run_01")
        >>> app = build_tradeoff_dash_app(solutions, default_col)
        >>> app.run(debug=True)
    """
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


def main(argv=None):
    """CLI entry point: launch the tradeoff explorer against a results folder.

    Usage:
        python -m parasolpy.dash_tools OUTPUT_FOLDER [--config ...] [--solutions ...]
            [--title ...] [--colorscale ...] [--host 127.0.0.1] [--port 8050] [--debug]
    """
    parser = argparse.ArgumentParser(
        description="Launch the parasolpy tradeoff explorer for a results folder.",
    )
    parser.add_argument("output_folder", help="Folder containing config and solutions files.")
    parser.add_argument("--config", dest="config_filename", default=None,
                        help="Optional config XML filename (auto-discovered when omitted).")
    parser.add_argument("--solutions", dest="solutions_filename", default=None,
                        help="Optional solutions CSV filename (auto-discovered when omitted).")
    parser.add_argument("--title", default="Tradeoff Explorer", help="Plot heading.")
    parser.add_argument("--colorscale", default="viridis", help="Named Plotly colorscale.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=8050, help="Port to serve on.")
    parser.add_argument("--debug", action="store_true", help="Run Dash in debug mode.")
    args = parser.parse_args(argv)

    _, solutions, default_color_column = load_dash_inputs(
        args.output_folder,
        config_filename=args.config_filename,
        solutions_filename=args.solutions_filename,
    )
    app = build_tradeoff_dash_app(
        solutions,
        default_color_column,
        title=args.title,
        default_colorscale=args.colorscale,
    )
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
