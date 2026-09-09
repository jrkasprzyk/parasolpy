"""Live leaderboard dashboard for a Borg MOEA runtime file.

Watches a runtime file while the optimization writes it and renders the
archive as a live leaderboard: one row per archived solution, sorted by a key
you choose, annotated with how each solution moved in that order since the
previous snapshot. Sorting is an ordering and not a verdict, so nothing here
treats a row near the top as a better solution than one near the bottom. New archive members are tinted green and labelled "born"; members
that dropped out linger for a few snapshots as struck-through red "died" rows
before disappearing, so a death is something you see rather than a row that
vanishes between refreshes.

Run it against a live run::

    parasolpy-runtime path/to/runtime.txt --sort-column "Cora Avg Storage" --descending

or replay a finished run (or the bundled sample) to see the widget move::

    parasolpy-runtime path/to/runtime.txt --replay
    parasolpy-runtime --demo

State is held in a module-level :class:`_Monitor` because this is a
single-user local tool: the Dash callback fires on a timer, and the file
reader must keep its byte offset and its previous-snapshot positions between
callbacks. Serving it to several users at once would need per-session state.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dash_table, dcc, html, no_update
from plotly.subplots import make_subplots

from parasolpy.runtime_monitor import (
    SORT_AGE,
    SORT_ID,
    STATUS_BORN,
    STATUS_DIED,
    STATUS_DOWN,
    STATUS_HELD,
    STATUS_UP,
    LeaderboardState,
    ReplaySource,
    RuntimeTail,
)

#: Sort keys that are not data columns, shown ahead of them in the picker.
_BUILTIN_SORTS = [
    {"label": "Solution ID", "value": SORT_ID},
    {"label": "Age (NFE)", "value": SORT_AGE},
]

#: What a user may type after ``--sort-column`` to reach the built-in keys.
_SORT_ALIASES = {
    "id": SORT_ID,
    "solution id": SORT_ID,
    "age": SORT_AGE,
    "nfe": SORT_ID,
}

#: Bundled runtime file used by ``--demo``.
DEMO_RUNTIME = Path(__file__).parent / "data" / "RunTime_with-headers.txt"

# Status palette (fixed, never themed) for the two states the user cares
# about, plus categorical blue for the archive-size trace. Green and red are
# reserved for birth and death alone, so movement through the sort order is
# drawn with ink and arrow glyphs instead of borrowing them.
_GOOD = "#0ca30c"
_CRITICAL = "#d03b3b"
_SERIES_BLUE = "#2a78d6"

# Ink and grid steps that clear both surfaces, for the Plotly figure.
_INK_NEUTRAL = "#898781"
_GRID_NEUTRAL = "rgba(137, 135, 129, 0.28)"

# Row tints: the same status hues at low alpha, so the table reads as a field
# of neutral rows with births and deaths standing out.
_TINT_BORN = "rgba(12, 163, 12, 0.14)"
_TINT_DIED = "rgba(208, 59, 59, 0.14)"

#: Label shown in the Status column. Paired with the row tint so state is
#: never carried by color alone.
_STATUS_LABEL = {
    STATUS_BORN: "born",
    STATUS_DIED: "died",
    STATUS_UP: "up",
    STATUS_DOWN: "down",
    STATUS_HELD: "held",
}

_MAX_DEFAULT_COLUMNS = 6


def _options(names):
    """Dropdown options for a list of column names."""
    return [{"label": name, "value": name} for name in names]


def _sort_options(names):
    """Sort-key options: the built-in keys first, then the data columns."""
    return _BUILTIN_SORTS + _options(names)


def resolve_sort_column(name):
    """Map a user-supplied sort key to a column name or a built-in sort key.

    Accepts the built-in keys by friendly name (``id``, ``age``) so the CLI
    does not have to expose the sentinel values.

    Args:
        name (str | None): Column name, alias, or ``None``.

    Returns:
        str: A data column name, :data:`SORT_ID`, or :data:`SORT_AGE`.
    """
    if not name:
        return SORT_ID
    return _SORT_ALIASES.get(name.strip().lower(), name)


def _move_text(row):
    """Render how far a row moved in the sort order, as an arrow plus count."""
    status = row["status"]
    if status == STATUS_BORN:
        return "★ new"
    if status == STATUS_DIED:
        return "✝ out"
    move = row.get("move") or 0
    if status == STATUS_UP:
        return f"▲ {move}"
    if status == STATUS_DOWN:
        return f"▼ {move}"
    return "–"


class _Monitor:
    """Holds the poll source and leaderboard state across Dash callbacks.

    Args:
        source: Either a :class:`~parasolpy.runtime_monitor.RuntimeTail` or a
            :class:`~parasolpy.runtime_monitor.ReplaySource`; both expose
            ``poll()`` and a ``restarted`` flag.
        board (LeaderboardState): Accumulates the polled snapshots.
    """

    def __init__(self, source, board):
        self.source = source
        self.board = board
        self.restarts_seen = 0

    def poll(self):
        """Advance the leaderboard with whatever snapshots are available.

        Returns:
            int: Number of snapshots applied on this poll.
        """
        snapshots = self.source.poll()
        if getattr(self.source, "restarted", False):
            # The runtime file was rewritten: previous positions describe a run
            # that no longer exists, so start the leaderboard over.
            self.board.reset()
            self.restarts_seen += 1
        for snapshot in snapshots:
            self.board.update(snapshot)
        return len(snapshots)

    @property
    def waiting(self):
        """bool: True while no snapshot has arrived yet."""
        return self.board.nfe is None


def _stat_tile(label, value, accent=None):
    """One labelled number in the header strip."""
    return html.Div(
        [
            html.Div(label, className="tile-label"),
            html.Div(value, className="tile-value", style={"color": accent} if accent else {}),
        ],
        className="tile",
    )


def _header_tiles(board):
    """Build the row of stat tiles summarizing the latest snapshot."""
    meta = board.metadata
    return [
        _stat_tile("NFE", f"{board.nfe:,}" if board.nfe is not None else "—"),
        _stat_tile("Archive", str(meta.get("archive_size", "—"))),
        _stat_tile("Population", str(meta.get("population_size", "—"))),
        _stat_tile("Improvements", str(meta.get("improvements", "—"))),
        _stat_tile("Restarts", str(meta.get("restarts", "—"))),
        _stat_tile("Born ↑", str(len(board.born)), accent=_GOOD),
        _stat_tile("Died ↓", str(len(board.died)), accent=_CRITICAL),
        _stat_tile("Snapshots", str(board.snapshot_count)),
    ]


def _churn_figure(board):
    """Archive size over NFE, with per-snapshot births and deaths beneath.

    Two stacked panels sharing one x-axis rather than one panel with two
    y-scales: archive size and churn count have unrelated ranges, and a
    dual-axis chart would invite reading a crossing as meaningful.
    """
    history = board.history_frame()
    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.12,
        row_heights=[0.6, 0.4],
        subplot_titles=("Archive size", "Born / died per snapshot"),
    )
    if not history.empty:
        figure.add_trace(
            go.Scatter(
                x=history["nfe"],
                y=history["archive_size"],
                mode="lines",
                line={"color": _SERIES_BLUE, "width": 2},
                name="archive size",
                hovertemplate="NFE %{x:,}<br>archive %{y}<extra></extra>",
            ),
            row=1,
            col=1,
        )
        figure.add_trace(
            go.Bar(
                x=history["nfe"],
                y=history["born"],
                marker_color=_GOOD,
                name="born",
                hovertemplate="NFE %{x:,}<br>born %{y}<extra></extra>",
            ),
            row=2,
            col=1,
        )
        figure.add_trace(
            go.Bar(
                x=history["nfe"],
                y=-history["died"],
                marker_color=_CRITICAL,
                name="died",
                customdata=history["died"],
                hovertemplate="NFE %{x:,}<br>died %{customdata}<extra></extra>",
            ),
            row=2,
            col=1,
        )
    figure.update_layout(
        height=300,
        margin={"l": 48, "r": 16, "t": 32, "b": 32},
        barmode="relative",
        showlegend=True,
        legend={"orientation": "h", "y": -0.18, "x": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        # Plotly colors are baked server-side and cannot read the CSS
        # tokens, so the chart uses the one ink step that is legible on
        # both the light and the dark surface.
        font={"size": 11, "color": _INK_NEUTRAL},
        hovermode="x unified",
    )
    figure.update_xaxes(showgrid=False, zeroline=False, title_text="NFE", row=2, col=1)
    figure.update_yaxes(gridcolor=_GRID_NEUTRAL, zeroline=False)
    figure.update_annotations(font_size=12)
    return figure


def _table_columns(value_columns):
    """Column spec for the leaderboard table: fixed columns then chosen values."""
    from dash.dash_table.Format import Format, Scheme, Trim

    columns = [
        {"name": "#", "id": "position", "type": "text"},
        {"name": "Move", "id": "move_text", "type": "text"},
        {"name": "Status", "id": "status_label", "type": "text"},
        {"name": "ID", "id": "id", "type": "numeric"},
        {"name": "Age (NFE)", "id": "age", "type": "numeric"},
    ]
    # Trim insignificant zeros: objectives here span 0.01 to 260000, and
    # a fixed decimal count makes one end unreadable and the other noisy.
    numeric = Format(precision=6, scheme=Scheme.decimal_or_exponent, trim=Trim.yes)
    columns += [
        {"name": name, "id": name, "type": "numeric", "format": numeric}
        for name in value_columns
    ]
    return columns


#: Row styling. Each rule pairs a tint with a Status label already present in
#: the row, so the state never depends on color alone.
_CONDITIONAL_STYLES = [
    {
        "if": {"filter_query": f'{{status}} = "{STATUS_BORN}"'},
        "backgroundColor": _TINT_BORN,
        "fontWeight": "600",
    },
    {
        "if": {"filter_query": f'{{status}} = "{STATUS_DIED}"'},
        "backgroundColor": _TINT_DIED,
        "textDecoration": "line-through",
        "opacity": "0.72",
    },
    {
        "if": {"filter_query": f'{{status}} = "{STATUS_BORN}"', "column_id": "status_label"},
        "color": _GOOD,
    },
    {
        "if": {"filter_query": f'{{status}} = "{STATUS_DIED}"', "column_id": "status_label"},
        "color": _CRITICAL,
    },
    {
        "if": {"filter_query": f'{{status}} = "{STATUS_UP}"', "column_id": "move_text"},
        "color": _SERIES_BLUE,
    },
]

_INDEX_STRING = """<!DOCTYPE html>
<html>
    <head>
        {%metas%}<title>{%title%}</title>{%favicon%}{%css%}
        <style>
          :root {
            --surface: #fcfcfb; --panel: #ffffff; --ink: #0b0b0b;
            --ink-2: #52514e; --ink-3: #898781; --rule: #e1e0d9;
          }
          @media (prefers-color-scheme: dark) {
            :root {
              --surface: #1a1a19; --panel: #232322; --ink: #ffffff;
              --ink-2: #c3c2b7; --ink-3: #898781; --rule: #383835;
            }
          }
          body { margin: 0; background: var(--surface); color: var(--ink);
                 font-family: -apple-system, "Segoe UI", Roboto, sans-serif; }
          .wrap { max-width: 1500px; margin: 0 auto; padding: 16px 20px 32px; }
          h1 { font-size: 18px; margin: 0 0 2px; letter-spacing: -0.01em; }
          .sub { font-size: 12px; color: var(--ink-3); margin-bottom: 14px;
                 word-break: break-all; }
          .tiles { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
          .tile { background: var(--panel); border: 1px solid var(--rule);
                  border-radius: 8px; padding: 8px 14px; min-width: 84px; }
          .tile-label { font-size: 10px; text-transform: uppercase;
                        letter-spacing: 0.06em; color: var(--ink-3); }
          .tile-value { font-size: 20px; font-weight: 600;
                        font-variant-numeric: tabular-nums; }
          .controls { display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-end;
                      margin-bottom: 14px; }
          .control { min-width: 190px; }
          .control > label { display: block; font-size: 10px; text-transform: uppercase;
                             letter-spacing: 0.06em; color: var(--ink-3); margin-bottom: 3px; }
          .pill { display: inline-block; font-size: 11px; font-weight: 600;
                  padding: 3px 10px; border-radius: 999px; border: 1px solid var(--rule); }
          button.pause { font: inherit; font-size: 13px; padding: 7px 16px;
                         border-radius: 8px; border: 1px solid var(--rule);
                         background: var(--panel); color: var(--ink); cursor: pointer; }

          /* Dash paints the DataTable and its dropdowns with hard-coded light
             values, which vanish against a dark surface. The cells themselves
             are themed through style_cell/style_header instead of here: those
             become inline styles, which the per-row tints from
             style_data_conditional can still override. An !important rule on
             td would outrank those and erase the born/died coloring. */
          .dash-spreadsheet, .dash-spreadsheet-container, .dash-spreadsheet-inner {
            background-color: var(--panel) !important;
            border-color: var(--rule) !important;
          }
          .dash-dropdown-trigger, .dash-dropdown-content,
          .dash-dropdown-search, .dash-dropdown-value-item {
            background-color: var(--panel) !important;
            color: var(--ink) !important;
            border-color: var(--rule) !important;
          }
          .dash-dropdown-value, .dash-dropdown-option, .dash-options-list-option {
            color: var(--ink) !important;
          }
          .dash-dropdown-placeholder { color: var(--ink-3) !important; }
          .dash-options-list-option.selected,
          .dash-options-list-option:hover { background-color: var(--surface) !important; }
        </style>
    </head>
    <body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body>
</html>"""


def build_runtime_dashboard_app(
    monitor,
    title="Borg Runtime Leaderboard",
    interval_seconds=2.0,
    max_rows=200,
):
    """Build the Dash app that renders a live archive leaderboard.

    Args:
        monitor (_Monitor): Poll source plus leaderboard state.
        title (str, optional): Heading shown above the table.
        interval_seconds (float, optional): Seconds between polls.
        max_rows (int, optional): Cap on rows rendered, applied from the top
            of the sort order. Large archives are slow to re-render in the
            browser; ghost rows within the cap are kept.

    Returns:
        dash.Dash: A configured app. Call ``app.run(...)`` to serve it.
    """
    app = Dash(__name__, title=title)
    app.index_string = _INDEX_STRING
    board = monitor.board
    source_label = str(getattr(monitor.source, "path", "unknown source"))

    app.layout = html.Div(
        className="wrap",
        children=[
            html.H1(title),
            html.Div(
                [html.Span(source_label), " · ", html.Span(id="run-state", className="pill")],
                className="sub",
            ),
            html.Div(id="tiles", className="tiles"),
            html.Div(
                className="controls",
                children=[
                    html.Div(
                        className="control",
                        children=[
                            html.Label("Sort by"),
                            dcc.Dropdown(id="sort-column",
                                         options=_sort_options(board.columns),
                                         value=board.sort_column,
                                         clearable=False),
                        ],
                    ),
                    html.Div(
                        className="control",
                        children=[
                            html.Label("Direction"),
                            dcc.Dropdown(
                                id="direction",
                                options=[
                                    {"label": "ascending", "value": "asc"},
                                    {"label": "descending", "value": "desc"},
                                ],
                                value="asc" if board.ascending else "desc",
                                clearable=False,
                            ),
                        ],
                    ),
                    html.Div(
                        className="control",
                        style={"flex": "1 1 320px"},
                        children=[
                            html.Label("Columns shown"),
                            dcc.Dropdown(id="value-columns", options=[], value=[], multi=True),
                        ],
                    ),
                    html.Div(
                        className="control",
                        style={"minWidth": "150px"},
                        children=[
                            html.Label("Refresh"),
                            dcc.Dropdown(
                                id="refresh",
                                options=[
                                    {"label": f"{s:g} s", "value": s}
                                    for s in (0.5, 1, 2, 5, 10)
                                ],
                                value=interval_seconds,
                                clearable=False,
                            ),
                        ],
                    ),
                    html.Button("Pause", id="pause", className="pause", n_clicks=0),
                ],
            ),
            dash_table.DataTable(
                id="leaderboard",
                data=[],
                columns=_table_columns([]),
                style_as_list_view=True,
                style_table={"overflowX": "auto", "maxHeight": "58vh", "overflowY": "auto"},
                style_cell={
                    "fontFamily": "ui-monospace, SFMono-Regular, Menlo, monospace",
                    "fontSize": "12px",
                    "padding": "5px 10px",
                    "textAlign": "right",
                    "border": "none",
                    # Inline, so the conditional row tints below can override it.
                    "backgroundColor": "var(--panel)",
                    "color": "var(--ink)",
                },
                style_header={
                    "fontWeight": "600",
                    "textTransform": "uppercase",
                    "fontSize": "10px",
                    "letterSpacing": "0.06em",
                    "backgroundColor": "var(--surface)",
                    "color": "var(--ink-2)",
                    "borderBottom": "1px solid var(--rule)",
                    "whiteSpace": "normal",
                    "height": "auto",
                },
                style_data_conditional=_CONDITIONAL_STYLES,
                style_cell_conditional=[
                    {"if": {"column_id": c}, "textAlign": "left"}
                    for c in ("position", "move_text", "status_label")
                ],
                fixed_rows={"headers": True},
                hidden_columns=["status"],
                css=[{"selector": ".show-hide", "rule": "display: none"}],
            ),
            dcc.Graph(id="churn", figure=_churn_figure(board), config={"displayModeBar": False}),
            dcc.Interval(id="tick", interval=int(interval_seconds * 1000), n_intervals=0),
        ],
    )

    @app.callback(
        Output("tick", "interval"),
        Output("tick", "disabled"),
        Output("pause", "children"),
        Input("refresh", "value"),
        Input("pause", "n_clicks"),
    )
    def _timer(refresh, n_clicks):
        paused = bool(n_clicks % 2)
        return int(float(refresh) * 1000), paused, "Resume" if paused else "Pause"

    @app.callback(
        Output("leaderboard", "data"),
        Output("leaderboard", "columns"),
        Output("tiles", "children"),
        Output("churn", "figure"),
        Output("run-state", "children"),
        Input("tick", "n_intervals"),
        Input("sort-column", "value"),
        Input("direction", "value"),
        Input("value-columns", "value"),
        State("tick", "disabled"),
    )
    def _refresh(_n, sort_column, direction, value_columns, paused):
        return render(
            monitor,
            sort_column=sort_column,
            ascending=direction != "desc",
            value_columns=value_columns,
            paused=bool(paused),
            max_rows=max_rows,
        )

    # Column pickers are populated in their own callback, driven by the same
    # tick but reading the value as State: a dropdown that is both Input and
    # Output of one callback re-triggers itself on every change.
    @app.callback(
        Output("sort-column", "options"),
        Output("value-columns", "options"),
        Output("value-columns", "value"),
        Input("tick", "n_intervals"),
        State("value-columns", "value"),
    )
    def _columns(_n, chosen):
        options = _options(board.columns)
        sort_options = _sort_options(board.columns)
        if chosen or not board.columns:
            return sort_options, options, no_update
        return sort_options, options, board.columns[:_MAX_DEFAULT_COLUMNS]

    return app


def render(monitor, sort_column=None, ascending=True, value_columns=None,
           paused=False, max_rows=200):
    """Poll the monitor once and build every piece the dashboard displays.

    Kept separate from the Dash callback so the rendering can be exercised
    without a browser or a running server.

    Args:
        monitor (_Monitor): Poll source plus leaderboard state.
        sort_column (str, optional): Data column, ``SORT_ID`` or
            ``SORT_AGE``; ``None`` sorts by solution ID.
        ascending (bool, optional): Sort direction.
        value_columns (list of str, optional): Data columns to show. Empty
            or ``None`` falls back to the first few columns of the file.
        paused (bool, optional): Skip the poll and render current state.
        max_rows (int, optional): Cap on rendered rows.

    Returns:
        tuple: ``(rows, columns, tiles, figure, state_label)``, matching the
        outputs of the dashboard's refresh callback.
    """
    board = monitor.board
    if not paused:
        monitor.poll()

    if (sort_column or SORT_ID, ascending) != (board.sort_column, board.ascending):
        board.set_sorting(sort_column, ascending)

    if not value_columns:
        value_columns = board.columns[:_MAX_DEFAULT_COLUMNS]
    shown = [name for name in value_columns if name in board.columns]
    # The column driving the sort is always shown, first: a table whose
    # ordering comes from a hidden number is unreadable. The built-in sort
    # keys need no pinning, since ID and age have columns of their own.
    if sort_column and sort_column in board.columns:
        shown = [sort_column] + [name for name in shown if name != sort_column]

    rows = [
        {
            "position": row["position"],
            "move_text": _move_text(row),
            "status_label": _STATUS_LABEL[row["status"]],
            "status": row["status"],
            "id": row["id"],
            "age": row["age"],
            **{name: row.get(name) for name in shown},
        }
        for row in board.rows()[:max_rows]
    ]

    if monitor.waiting:
        state = "waiting for first snapshot"
    elif getattr(monitor.source, "exhausted", False):
        state = "replay finished"
    elif paused:
        state = "paused"
    else:
        state = "live"

    return rows, _table_columns(shown), _header_tiles(board), _churn_figure(board), state


def build_monitor(
    runtime_path,
    columns=None,
    sort_column=None,
    ascending=True,
    ghost_snapshots=2,
    replay=False,
    snapshots_per_poll=1,
    loop=False,
):
    """Assemble the poll source and leaderboard state for the dashboard.

    Args:
        runtime_path (str | PathLike): Runtime file to follow or replay.
        columns (list of str, optional): Data column names, for runtime files
            whose layout carries no column-header row.
        sort_column (str, optional): Initial sort key: a data column,
            ``SORT_ID`` or ``SORT_AGE``. ``None`` sorts by solution ID.
        ascending (bool, optional): Sort direction.
        ghost_snapshots (int, optional): Snapshots a dead solution stays
            visible as a struck-through row.
        replay (bool, optional): Replay a finished file instead of tailing a
            live one.
        snapshots_per_poll (int, optional): Replay speed, in snapshots per
            poll. Ignored when tailing.
        loop (bool, optional): Restart a replay when it reaches the end.

    Returns:
        _Monitor: Ready to be passed to :func:`build_runtime_dashboard_app`.
    """
    if replay:
        source = ReplaySource(
            runtime_path,
            columns=columns,
            snapshots_per_poll=snapshots_per_poll,
            loop=loop,
        )
    else:
        source = RuntimeTail(runtime_path, columns=columns)
    board = LeaderboardState(
        sort_column=sort_column,
        ascending=ascending,
        ghost_snapshots=ghost_snapshots,
    )
    return _Monitor(source, board)


def main(argv=None):
    """CLI entry point: serve the live leaderboard for a Borg runtime file.

    Usage:
        parasolpy-runtime RUNTIME_FILE [--replay] [--sort-column NAME]
            [--descending] [--columns A,B,C] [--interval 2.0] [--ghosts 2]
        parasolpy-runtime --demo
    """
    parser = argparse.ArgumentParser(
        description="Live leaderboard for a Borg MOEA runtime file.",
    )
    parser.add_argument("runtime_file", nargs="?",
                        help="Borg runtime file to follow (it need not exist yet).")
    parser.add_argument("--demo", action="store_true",
                        help="Replay the bundled sample runtime file on a loop.")
    parser.add_argument("--replay", action="store_true",
                        help="Replay a finished runtime file one snapshot per refresh.")
    parser.add_argument("--speed", type=int, default=1,
                        help="Replay snapshots per refresh (default 1).")
    parser.add_argument("--loop", action="store_true",
                        help="Restart a replay when it reaches the end.")
    parser.add_argument("--sort-column", default=None,
                        help="What to sort by: a data column name, or 'id' or "
                             "'age' (default: id, which is oldest first).")
    parser.add_argument("--descending", action="store_true",
                        help="Sort largest first instead of smallest first.")
    parser.add_argument("--columns", default=None,
                        help="Comma-separated names for the data columns after the "
                             "solution ID, for runtime files with no header row.")
    parser.add_argument("--ghosts", type=int, default=2,
                        help="Snapshots a dead solution stays visible (default 2).")
    parser.add_argument("--interval", type=float, default=2.0,
                        help="Seconds between polls (default 2.0).")
    parser.add_argument("--max-rows", type=int, default=200,
                        help="Maximum leaderboard rows rendered (default 200).")
    parser.add_argument("--title", default="Borg Runtime Leaderboard", help="Page heading.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=8051, help="Port to serve on.")
    parser.add_argument("--debug", action="store_true", help="Run Dash in debug mode.")
    args = parser.parse_args(argv)

    if args.demo:
        runtime_file, replay, loop = DEMO_RUNTIME, True, True
    elif args.runtime_file:
        runtime_file, replay, loop = args.runtime_file, args.replay, args.loop
    else:
        parser.error("a runtime file is required unless --demo is given")

    monitor = build_monitor(
        runtime_file,
        columns=args.columns.split(",") if args.columns else None,
        sort_column=resolve_sort_column(args.sort_column),
        ascending=not args.descending,
        ghost_snapshots=args.ghosts,
        replay=replay,
        snapshots_per_poll=args.speed,
        loop=loop,
    )
    # Poll once before building the layout so the column pickers open
    # populated when the runtime file already has content.
    monitor.poll()
    app = build_runtime_dashboard_app(
        monitor,
        title=args.title,
        interval_seconds=args.interval,
        max_rows=args.max_rows,
    )
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
