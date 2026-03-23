from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.lines import Line2D


def _load_corr_from_network_excel(corr_excel: Path, sheet_name: str = "robust_corr"):
    """
    Load a square correlation matrix from the exported network QC Excel.
    Falls back to 'pearson_r' if 'robust_corr' is absent.
    """
    corr_excel = Path(corr_excel)

    xl = pd.ExcelFile(corr_excel)
    if sheet_name not in xl.sheet_names:
        if "pearson_r" in xl.sheet_names:
            sheet_name = "pearson_r"
        else:
            raise KeyError(
                f"Neither '{sheet_name}' nor 'pearson_r' found in {corr_excel}"
            )

    df = pd.read_excel(corr_excel, sheet_name=sheet_name, index_col=0)
    R = df.to_numpy(dtype=float)

    R = np.nan_to_num(R, nan=0.0, posinf=0.0, neginf=0.0)
    if R.shape[0] == R.shape[1]:
        np.fill_diagonal(R, 1.0)

    return R, df.index.tolist()


def save_corr_matrix_plot(
    corr_excel: Path,
    out_svg: Path,
    *,
    state_name: str | None = None,
    sheet_name: str = "robust_corr",
    dpi: int = 300,
):
    """
    Save correlation matrix plot from network QC Excel.
    """
    R, _labels = _load_corr_from_network_excel(corr_excel, sheet_name=sheet_name)

    fig, ax = plt.subplots(figsize=(5, 2.5), dpi=dpi, layout="constrained")
    im = ax.imshow(R, vmin=-1, vmax=1, cmap="bwr", origin="lower")

    title = state_name if state_name is not None else Path(corr_excel).stem
    ax.set_title(title)
    ax.set_xlabel("Cell index")
    ax.set_ylabel("Cell index")

    cbar = plt.colorbar(im, ax=ax)
    cbar.set_ticks(np.linspace(-1, 1, 11))

    out_svg = Path(out_svg)
    out_svg.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_svg, bbox_inches="tight")
    plt.close(fig)

    return out_svg


def draw_signed_network_single_ax(
    W_signed,
    *,
    pos_color="red",
    neg_color="blue",
    node_size=14,
    node_color="#BDBDBD",
    alpha=0.8,
    base_width=0.4,
    max_width=3.0,
    title=None,
):
    """
    Draw a single signed network from a thresholded / robust signed matrix.
    """
    n_cells = W_signed.shape[0]

    G = nx.Graph()
    G.add_nodes_from(range(n_cells))

    positive_edges = []
    negative_edges = []
    pos_weights = []
    neg_weights = []

    for i in range(n_cells):
        for j in range(i + 1, n_cells):
            corr_val = float(W_signed[i, j])
            if corr_val != 0:
                G.add_edge(i, j, weight=abs(corr_val))
                if corr_val > 0:
                    positive_edges.append((i, j))
                    pos_weights.append(abs(corr_val))
                else:
                    negative_edges.append((i, j))
                    neg_weights.append(abs(corr_val))

    fig, ax = plt.subplots(figsize=(6, 6), layout="constrained")

    if G.number_of_edges() == 0:
        nx.draw_networkx_nodes(
            G,
            {i: (0, 0) for i in range(n_cells)},
            ax=ax,
            node_size=node_size,
            linewidths=0,
            node_color=node_color,
        )
        ax.set_title(title if title else "No edges to display")
        ax.axis("off")
        return fig, ax

    pos_layout = nx.kamada_kawai_layout(G)

    def scale_widths(w_list):
        if len(w_list) == 0:
            return []
        w_max = max(w_list)
        if w_max == 0:
            return [base_width] * len(w_list)
        return [
            base_width + (max_width - base_width) * (w / w_max)
            for w in w_list
        ]

    pos_widths = scale_widths(pos_weights)
    neg_widths = scale_widths(neg_weights)

    nx.draw_networkx_nodes(
        G,
        pos_layout,
        ax=ax,
        node_size=node_size,
        linewidths=0,
        node_color=node_color,
    )

    if len(positive_edges) > 0:
        nx.draw_networkx_edges(
            G,
            pos_layout,
            ax=ax,
            edgelist=positive_edges,
            width=pos_widths,
            edge_color=pos_color,
            alpha=alpha,
        )

    if len(negative_edges) > 0:
        nx.draw_networkx_edges(
            G,
            pos_layout,
            ax=ax,
            edgelist=negative_edges,
            width=neg_widths,
            edge_color=neg_color,
            alpha=alpha,
        )

    handles = []
    if len(positive_edges) > 0:
        handles.append(Line2D([0], [0], color=pos_color, lw=2, label="Positive"))
    if len(negative_edges) > 0:
        handles.append(Line2D([0], [0], color=neg_color, lw=2, label="Negative"))
    if handles:
        ax.legend(handles=handles, loc="upper right", frameon=False)

    if title is not None:
        ax.set_title(title, fontsize=11)
    ax.axis("off")

    return fig, ax


def save_signed_network_plot(
    corr_excel: Path,
    out_svg: Path,
    *,
    state_name: str | None = None,
    sheet_name: str = "robust_corr",
):
    """
    Save signed network plot from robust / thresholded correlation matrix Excel sheet.
    """
    W_signed, _labels = _load_corr_from_network_excel(corr_excel, sheet_name=sheet_name)

    title = state_name if state_name is not None else Path(corr_excel).stem
    fig, ax = draw_signed_network_single_ax(W_signed, title=title)

    out_svg = Path(out_svg)
    out_svg.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_svg, bbox_inches="tight")
    plt.close(fig)

    return out_svg


def batch_export_network_plots(
    proc_root: Path,
    *,
    corr_glob: str = "*network_qc*.xlsx",
    matrix_sheet: str = "robust_corr",
):
    """
    For each TSeries, save:
      _QC_suite2p/correlation_networks/*corr_matrix*.svg
      _QC_suite2p/correlation_networks/*signed_network*.svg
    """
    proc_root = Path(proc_root)
    counts = {"ok": 0, "fail": 0, "total": 0}

    for ts in sorted(proc_root.glob("TSeries*")):
        qc_dir = ts / "_QC_suite2p"
        if not qc_dir.exists():
            continue

        corr_files = sorted(qc_dir.glob(corr_glob))
        if not corr_files:
            continue

        counts["total"] += 1
        corr_excel = corr_files[0]

        plot_dir = qc_dir / "correlation_networks"
        ts_name = ts.name

        try:
            save_corr_matrix_plot(
                corr_excel,
                plot_dir / f"{ts_name}__corr_matrix.svg",
                state_name=ts_name,
                sheet_name=matrix_sheet,
            )
            save_signed_network_plot(
                corr_excel,
                plot_dir / f"{ts_name}__signed_network.svg",
                state_name=ts_name,
                sheet_name=matrix_sheet,
            )
            counts["ok"] += 1
        except Exception as e:
            (plot_dir / "FAILED_network_plots.txt").parent.mkdir(parents=True, exist_ok=True)
            (plot_dir / "FAILED_network_plots.txt").write_text(f"{type(e).__name__}: {e}")
            counts["fail"] += 1

    return counts