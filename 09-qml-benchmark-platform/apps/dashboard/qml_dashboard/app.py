from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html

from qml_dashboard.client import BenchmarkApiClient


def _metric(label: str, identifier: str) -> html.Div:
    return html.Div(
        [html.Span(label, className="metric-label"), html.Strong(id=identifier)],
        className="metric",
    )


def _shell() -> html.Div:
    return html.Div(
        [
            html.Header(
                [
                    html.Div(
                        [
                            html.P("PATH SOFTWARE ENGINEER · PROJECT 09", className="eyebrow"),
                            html.H1("QML Evidence & Kernel Benchmark Console"),
                            html.P(
                                "Executed encodings, paired model runs and kernel matrices "
                                "under one protocol — without a quantum-advantage claim.",
                                className="lede",
                            ),
                        ]
                    ),
                    html.A("Open Swagger", href="http://127.0.0.1:8080/docs", className="api-link"),
                ],
                className="hero",
            ),
            html.Main(
                [
                    html.Section(
                        [
                            html.H2("Executed configuration"),
                            html.Div(
                                [
                                    html.Label(
                                        ["Dataset", dcc.Dropdown(id="dataset", clearable=False)]
                                    ),
                                    html.Label(
                                        ["Sample", dcc.Dropdown(id="sample", clearable=False)]
                                    ),
                                    html.Label(
                                        ["Encoding", dcc.Dropdown(id="encoding", clearable=False)]
                                    ),
                                ],
                                className="control-grid",
                            ),
                            html.Button("Run encoding", id="run", n_clicks=0),
                            html.P(id="status", role="status", className="status"),
                        ],
                        className="panel controls",
                    ),
                    html.Section(
                        [
                            _metric("Qubits", "qubits"),
                            _metric("Circuit depth", "depth"),
                            _metric("Input features", "features"),
                            _metric("Padding", "padding"),
                            _metric("L2 norm", "norm"),
                        ],
                        className="metrics",
                        **{"aria-label": "Encoding resource summary"},
                    ),
                    html.Div(
                        [
                            html.Section(
                                [
                                    html.H2("Statevector evidence"),
                                    dcc.Graph(id="statevector", config={"displayModeBar": False}),
                                    html.Div(id="state-table", className="table-wrap"),
                                ],
                                className="panel span-two",
                            ),
                            html.Section(
                                [
                                    html.H2("Circuit operations"),
                                    html.Div(id="circuit-table", className="table-wrap"),
                                ],
                                className="panel",
                            ),
                            html.Section(
                                [
                                    html.H2("Provenance"),
                                    html.Dl(id="provenance"),
                                    html.Button(
                                        "Download evidence manifest", id="download", n_clicks=0
                                    ),
                                    dcc.Download(id="manifest-download"),
                                ],
                                className="panel",
                            ),
                            html.Section(
                                [
                                    html.H2("Responsible interpretation"),
                                    html.P(id="warning"),
                                    html.P(
                                        "This visualizer demonstrates deterministic "
                                        "state preparation. "
                                        "It does not benchmark kernels, models, hardware, or "
                                        "quantum advantage."
                                    ),
                                ],
                                className="panel span-two caution",
                            ),
                        ],
                        className="evidence-grid",
                    ),
                    html.Section(
                        [
                            html.Div(
                                [
                                    html.P("SPRINT 2", className="eyebrow dark"),
                                    html.H2("Quantum Kernel Results Visualizer"),
                                    html.P(
                                        "Run QSVM, a bounded VQC and classical baselines on the "
                                        "same immutable snapshot, split, seeds and metrics."
                                    ),
                                ],
                                className="section-heading",
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        [
                                            "Paired repetitions",
                                            dcc.Dropdown(
                                                id="benchmark-repetitions",
                                                options=[
                                                    {"label": "1 seed", "value": 1},
                                                    {"label": "2 seeds", "value": 2},
                                                    {"label": "3 seeds", "value": 3},
                                                ],
                                                value=2,
                                                clearable=False,
                                            ),
                                        ]
                                    ),
                                    html.Label(
                                        [
                                            "VQC iteration budget",
                                            dcc.Dropdown(
                                                id="vqc-iterations",
                                                options=[
                                                    {"label": str(value), "value": value}
                                                    for value in (2, 4, 6)
                                                ],
                                                value=4,
                                                clearable=False,
                                            ),
                                        ]
                                    ),
                                    html.Div(
                                        [
                                            html.Button(
                                                "Run paired benchmark",
                                                id="run-benchmark",
                                                n_clicks=0,
                                            ),
                                            html.P(
                                                id="benchmark-status",
                                                role="status",
                                                className="status block",
                                            ),
                                        ],
                                        className="benchmark-action",
                                    ),
                                ],
                                className="control-grid benchmark-controls",
                            ),
                        ],
                        className="panel benchmark-launch",
                    ),
                    html.Section(
                        [
                            _metric("Models", "benchmark-models"),
                            _metric("Paired runs", "benchmark-runs"),
                            _metric("Kernel matrices", "benchmark-matrices"),
                            _metric("Hardware jobs", "benchmark-hardware"),
                            _metric("Best mean F1", "benchmark-best-f1"),
                        ],
                        className="metrics",
                        **{"aria-label": "Benchmark result summary"},
                    ),
                    html.Div(
                        [
                            html.Section(
                                [
                                    html.H2("Kernel matrix heatmap"),
                                    html.Label(
                                        [
                                            "Kernel matrix",
                                            dcc.Dropdown(id="matrix-selector", clearable=False),
                                        ]
                                    ),
                                    dcc.Graph(
                                        id="kernel-heatmap",
                                        config={"displayModeBar": False},
                                    ),
                                    html.Div(id="kernel-table", className="table-wrap compact"),
                                    html.H2("Similarity projection", className="subheading"),
                                    html.P(
                                        "Centered kernel PCA derived from the selected matrix; "
                                        "this is a projection, not the original feature space."
                                    ),
                                    dcc.Graph(
                                        id="similarity-projection",
                                        config={"displayModeBar": False},
                                    ),
                                    html.Div(
                                        id="projection-table",
                                        className="table-wrap compact",
                                    ),
                                ],
                                className="panel span-two",
                            ),
                            html.Section(
                                [
                                    html.H2("Quality with variability"),
                                    dcc.Graph(id="quality-chart", config={"displayModeBar": False}),
                                    html.Div(id="quality-table", className="table-wrap"),
                                    html.H2("Confusion matrices", className="subheading"),
                                    html.Div(id="confusion-table", className="table-wrap"),
                                ],
                                className="panel",
                            ),
                            html.Section(
                                [
                                    html.H2("Resource comparison"),
                                    dcc.Graph(
                                        id="resource-chart", config={"displayModeBar": False}
                                    ),
                                    html.Div(id="resource-table", className="table-wrap"),
                                ],
                                className="panel",
                            ),
                            html.Section(
                                [
                                    html.H2("Protocol & imported evidence"),
                                    html.Div(id="benchmark-provenance"),
                                    html.Button(
                                        "Download comparison CSV",
                                        id="download-report",
                                        n_clicks=0,
                                    ),
                                    dcc.Download(id="report-download"),
                                ],
                                className="panel span-two",
                            ),
                            html.Section(
                                [
                                    html.H2("Threats to validity"),
                                    html.Ul(id="benchmark-limitations"),
                                    html.P(
                                        "A local difference is not a general quantum advantage.",
                                        className="claim-boundary",
                                    ),
                                ],
                                className="panel span-two caution",
                            ),
                        ],
                        className="evidence-grid benchmark-grid",
                    ),
                    dcc.Store(id="preview-store"),
                    dcc.Store(id="benchmark-store"),
                ]
            ),
        ]
    )


def _table(headers: list[str], rows: list[list[str]]) -> html.Table:
    return html.Table(
        [html.Thead(html.Tr([html.Th(header) for header in headers]))]
        + [html.Tbody([html.Tr([html.Td(value) for value in row]) for row in rows])]
    )


def create_dash_app(client: BenchmarkApiClient | None = None) -> Dash:
    api = client or BenchmarkApiClient()
    assets = Path(__file__).parents[1] / "assets"
    application = Dash(__name__, title="QML Encoding Visualizer", assets_folder=str(assets))
    application.layout = _shell()

    @application.callback(
        Output("dataset", "options"),
        Output("dataset", "value"),
        Output("encoding", "options"),
        Output("encoding", "value"),
        Output("sample", "options"),
        Output("sample", "value"),
        Input("dataset", "id"),
    )
    def initialize(_: str) -> tuple[Any, ...]:
        datasets = api.datasets()
        encodings = api.encodings()
        snapshot = api.snapshot(str(datasets[0]["snapshot_id"]))
        sample_ids = sorted(
            snapshot["split"]["train_ids"]
            + snapshot["split"]["validation_ids"]
            + snapshot["split"]["test_ids"]
        )
        dataset_options = [
            {"label": item["dataset_id"], "value": item["snapshot_id"]} for item in datasets
        ]
        return (
            dataset_options,
            datasets[0]["snapshot_id"],
            [{"label": item["name"], "value": item["id"]} for item in encodings],
            "angle",
            [{"label": value, "value": value} for value in sample_ids],
            sample_ids[0],
        )

    @application.callback(
        Output("preview-store", "data"),
        Output("status", "children"),
        Input("run", "n_clicks"),
        State("dataset", "value"),
        State("sample", "value"),
        State("encoding", "value"),
        prevent_initial_call=True,
    )
    def run_encoding(_: int, snapshot_id: str, sample_id: str, encoding: str) -> tuple[Any, str]:
        preview = api.preview(snapshot_id, sample_id, encoding)
        return preview, f"Executed and persisted as {preview['preview_id']}"

    @application.callback(
        Output("qubits", "children"),
        Output("depth", "children"),
        Output("features", "children"),
        Output("padding", "children"),
        Output("norm", "children"),
        Output("statevector", "figure"),
        Output("state-table", "children"),
        Output("circuit-table", "children"),
        Output("provenance", "children"),
        Output("warning", "children"),
        Input("preview-store", "data"),
    )
    def render_evidence(data: dict[str, Any] | None) -> tuple[Any, ...]:
        if not data:
            empty = go.Figure().update_layout(template="plotly_white", height=300)
            return ("—", "—", "—", "—", "—", empty, "Run an encoding.", "—", [], "—")
        artifact = data["artifact"]
        resources = artifact["resources"]
        state = artifact["statevector_real"]
        labels = [f"|{index:0{resources['qubits']}b}⟩" for index in range(len(state))]
        figure = go.Figure(go.Bar(x=labels, y=state, marker_color="#2563EB"))
        figure.update_layout(
            template="plotly_white",
            height=300,
            margin={"l": 42, "r": 18, "t": 20, "b": 44},
            xaxis_title="Computational basis state",
            yaxis_title="Real amplitude",
        )
        state_table = _table(
            ["Basis state", "Real amplitude"],
            [[label, f"{value:.6f}"] for label, value in zip(labels, state, strict=True)],
        )
        circuit_rows = [
            [
                str(index + 1),
                gate["name"],
                ", ".join(map(str, gate["wires"])),
                str(gate["parameter"] or "—"),
            ]
            for index, gate in enumerate(artifact["gates"])
        ]
        circuit_table = _table(["#", "Operation", "Wires", "Parameter"], circuit_rows)
        provenance = [
            html.Dt("Dataset SHA-256"),
            html.Dd(data["provenance"]["dataset_sha256"]),
            html.Dt("Scaler fitted on"),
            html.Dd(data["provenance"]["preprocessing_fitted_on"]),
            html.Dt("Input derivation"),
            html.Dd(data["provenance"]["input_derivation"]),
            html.Dt("Adapter agreement"),
            html.Dd(str(data["adapters"]["equivalent_magnitudes"])),
        ]
        warning = " ".join(artifact["warnings"]) or "No encoding warnings."
        return (
            resources["qubits"],
            resources["depth"],
            len(artifact["input_values"]),
            artifact["padding"],
            f"{artifact['normalization_norm']:.4f}",
            figure,
            state_table,
            circuit_table,
            provenance,
            warning,
        )

    @application.callback(
        Output("manifest-download", "data"),
        Input("download", "n_clicks"),
        State("preview-store", "data"),
        prevent_initial_call=True,
    )
    def download_manifest(_: int, data: dict[str, Any] | None) -> dict[str, Any] | None:
        if not data:
            return None
        manifest = api.manifest(str(data["preview_id"]))
        return {
            "content": json.dumps(manifest, indent=2),
            "filename": f"{data['preview_id']}.json",
            "type": "application/json",
        }

    @application.callback(
        Output("benchmark-store", "data"),
        Output("benchmark-status", "children"),
        Input("run-benchmark", "n_clicks"),
        State("dataset", "value"),
        State("benchmark-repetitions", "value"),
        State("vqc-iterations", "value"),
        prevent_initial_call=True,
    )
    def run_paired_benchmark(
        _: int,
        snapshot_id: str,
        repetitions: int,
        iterations: int,
    ) -> tuple[dict[str, Any], str]:
        seeds = [2409, 2410, 2411][:repetitions]
        report = api.benchmark(snapshot_id, seeds, iterations)
        return report, f"Completed and persisted as {report['report_id']}"

    @application.callback(
        Output("benchmark-models", "children"),
        Output("benchmark-runs", "children"),
        Output("benchmark-matrices", "children"),
        Output("benchmark-hardware", "children"),
        Output("benchmark-best-f1", "children"),
        Output("matrix-selector", "options"),
        Output("matrix-selector", "value"),
        Output("quality-chart", "figure"),
        Output("quality-table", "children"),
        Output("confusion-table", "children"),
        Output("resource-chart", "figure"),
        Output("resource-table", "children"),
        Output("benchmark-provenance", "children"),
        Output("benchmark-limitations", "children"),
        Input("benchmark-store", "data"),
    )
    def render_benchmark(data: dict[str, Any] | None) -> tuple[Any, ...]:
        empty = go.Figure().update_layout(template="plotly_white", height=320)
        if not data:
            return (
                "—",
                "—",
                "—",
                "—",
                "—",
                [],
                None,
                empty,
                "Run the paired benchmark.",
                "Run the paired benchmark.",
                empty,
                "Run the paired benchmark.",
                "No report persisted yet.",
                [],
            )
        aggregates = data["aggregates"]
        model_ids = [item["model_id"] for item in aggregates]
        f1_means = [item["metrics"]["f1"]["mean"] for item in aggregates]
        f1_stds = [item["metrics"]["f1"]["std"] for item in aggregates]
        quality = go.Figure(
            go.Bar(
                x=model_ids,
                y=f1_means,
                error_y={"type": "data", "array": f1_stds, "visible": True},
                marker_color="#2563EB",
            )
        )
        quality.update_layout(
            template="plotly_white",
            height=320,
            yaxis={"title": "F1 mean ± seed std", "range": [0, 1.05]},
            margin={"l": 42, "r": 18, "t": 20, "b": 74},
        )
        quality_table = _table(
            ["Model", "Mean F1", "Std", "Min", "Max"],
            [
                [
                    item["model_id"],
                    f"{item['metrics']['f1']['mean']:.3f}",
                    f"{item['metrics']['f1']['std']:.3f}",
                    f"{item['metrics']['f1']['minimum']:.3f}",
                    f"{item['metrics']['f1']['maximum']:.3f}",
                ]
                for item in aggregates
            ],
        )
        confusion_rows: list[list[str]] = []
        for model_id in model_ids:
            model_runs = [run for run in data["runs"] if run["model"]["model_id"] == model_id]
            summed = [
                sum(int(run["confusion_matrix"][row][column]) for run in model_runs)
                for row in range(2)
                for column in range(2)
            ]
            confusion_rows.append([model_id, *[str(value) for value in summed]])
        confusion_table = _table(
            ["Model", "TN", "FP", "FN", "TP"],
            confusion_rows,
        )
        resources_by_model: dict[str, dict[str, float]] = {}
        for run in data["runs"]:
            model_id = run["model"]["model_id"]
            entry = resources_by_model.setdefault(
                model_id,
                {"runtime": 0.0, "evaluations": 0.0, "count": 0.0},
            )
            entry["runtime"] += float(run["resources"]["runtime_seconds"])
            entry["evaluations"] += float(run["resources"]["circuit_evaluations"])
            entry["count"] += 1.0
        runtime_values = [
            resources_by_model[model]["runtime"] / resources_by_model[model]["count"]
            for model in model_ids
        ]
        resource_figure = go.Figure(go.Bar(x=model_ids, y=runtime_values, marker_color="#7B61FF"))
        resource_figure.update_layout(
            template="plotly_white",
            height=320,
            yaxis_title="Mean wall-clock seconds",
            margin={"l": 42, "r": 18, "t": 20, "b": 74},
        )
        resource_table = _table(
            ["Model", "Mean runtime (s)", "Circuit evaluations"],
            [
                [
                    model,
                    "{:.4f}".format(
                        resources_by_model[model]["runtime"] / resources_by_model[model]["count"]
                    ),
                    str(int(resources_by_model[model]["evaluations"])),
                ]
                for model in model_ids
            ],
        )
        imported = api.evidence_imports()
        provenance = html.Dl(
            [
                html.Dt("Config SHA-256"),
                html.Dd(data["config_hash"]),
                html.Dt("Dataset SHA-256"),
                html.Dd(data["provenance"]["dataset_sha256"]),
                html.Dt("Protocol seeds"),
                html.Dd(", ".join(map(str, data["protocol"]["seeds"]))),
                html.Dt("Imported sealed bundles"),
                html.Dd(", ".join(item["source_project"] for item in imported)),
            ]
        )
        matrices = data["kernel_matrices"]
        options = [
            {"label": matrix["kernel"]["kernel_id"], "value": matrix["matrix_id"]}
            for matrix in matrices
        ]
        return (
            len(model_ids),
            len(data["runs"]),
            len(matrices),
            data["provenance"]["hardware_jobs"],
            f"{max(f1_means):.3f}",
            options,
            options[0]["value"],
            quality,
            quality_table,
            confusion_table,
            resource_figure,
            resource_table,
            provenance,
            [html.Li(item) for item in data["limitations"]],
        )

    @application.callback(
        Output("kernel-heatmap", "figure"),
        Output("kernel-table", "children"),
        Output("similarity-projection", "figure"),
        Output("projection-table", "children"),
        Input("matrix-selector", "value"),
        State("benchmark-store", "data"),
    )
    def render_matrix(matrix_id: str | None, data: dict[str, Any] | None) -> tuple[Any, ...]:
        if not data or not matrix_id:
            empty = go.Figure().update_layout(template="plotly_white", height=380)
            return empty, "—", empty, "—"
        matrix = next(item for item in data["kernel_matrices"] if item["matrix_id"] == matrix_id)
        values = matrix["values"]
        sample_ids = matrix["sample_ids"]
        figure = go.Figure(
            go.Heatmap(
                z=values,
                x=sample_ids,
                y=sample_ids,
                colorscale="Viridis",
                colorbar={"title": "Similarity"},
            )
        )
        figure.update_layout(
            template="plotly_white",
            height=420,
            margin={"l": 70, "r": 20, "t": 20, "b": 70},
        )
        table = _table(
            ["Row sample", *sample_ids],
            [
                [sample_id, *[f"{float(value):.3f}" for value in row]]
                for sample_id, row in zip(sample_ids, values, strict=True)
            ],
        )
        projection = matrix["projection"]
        projection_figure = go.Figure(
            go.Scatter(
                x=[item["component_1"] for item in projection],
                y=[item["component_2"] for item in projection],
                text=[item["sample_id"] for item in projection],
                mode="markers+text",
                textposition="top center",
                marker={"color": "#7B61FF", "size": 10},
            )
        )
        projection_figure.update_layout(
            template="plotly_white",
            height=340,
            xaxis_title="Kernel principal component 1",
            yaxis_title="Kernel principal component 2",
            margin={"l": 50, "r": 20, "t": 20, "b": 50},
        )
        projection_table = _table(
            ["Sample", "Component 1", "Component 2"],
            [
                [
                    item["sample_id"],
                    f"{float(item['component_1']):.5f}",
                    f"{float(item['component_2']):.5f}",
                ]
                for item in projection
            ],
        )
        return figure, table, projection_figure, projection_table

    @application.callback(
        Output("report-download", "data"),
        Input("download-report", "n_clicks"),
        State("benchmark-store", "data"),
        prevent_initial_call=True,
    )
    def download_report(_: int, data: dict[str, Any] | None) -> dict[str, Any] | None:
        if not data:
            return None
        return {
            "content": api.report_csv(str(data["report_id"])),
            "filename": f"{data['report_id']}.csv",
            "type": "text/csv",
        }

    return application


app = create_dash_app()
server = app.server


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050)
