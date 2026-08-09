import pandas as pd
import numpy as np
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
FIG_DATA = RESULTS / "figure_source_data"
FIG_DATA.mkdir(parents=True, exist_ok=True)

def build_fig1_source():
    # 1. Internal edges
    internal_path = RESULTS / "internal" / "exact_edge_decomposition.csv"
    df_int = pd.read_csv(internal_path)
    assert len(df_int) == 8550, f"Expected 8550 internal rows, got {len(df_int)}"
    
    out_int = pd.DataFrame({
        "dataset": "Internal",
        "participant": df_int["participant"],
        "session": df_int["session_key"],
        "source_subset": df_int["from_subset"],
        "added_criterion": df_int["added_criterion"],
        "observed_delta_j": df_int["delta_obs"],
        "reconstructed_delta_j": df_int["j_reconstructed"] - df_int["j_old"]
    })

    # 2. External edges
    external_path = ROOT / "scripts" / "external_validation" / "outputs" / "q2_composition.csv"
    if not external_path.exists():
        external_path = RESULTS / "external_validation" / "q2_composition.csv"
    df_ext = pd.read_csv(external_path)
    assert len(df_ext) == 8100, f"Expected 8100 external rows, got {len(df_ext)}"
    
    out_ext = pd.DataFrame({
        "dataset": "External",
        "participant": df_ext["participant"],
        "session": df_ext["session"],
        "source_subset": df_ext["from_subset"],
        "added_criterion": df_ext["added_criterion"],
        "observed_delta_j": df_ext["observed_delta"],
        "reconstructed_delta_j": df_ext["reconstructed_delta"]
    })

    df_combined = pd.concat([out_int, out_ext], ignore_index=True)
    assert len(df_combined) == 16650, f"Total rows must be 16650, got {len(df_combined)}"

    err = np.abs(df_combined["observed_delta_j"] - df_combined["reconstructed_delta_j"])
    max_err = err.max()
    print(f"Max reconstruction error: {max_err}")
    assert max_err < 1e-12, f"Max error {max_err} exceeds tolerance"

    df_combined.to_csv(FIG_DATA / "fig1_composition_edges.csv", index=False)
    
    def get_signs(series):
        return np.where(series > 0, "Increase", np.where(series < 0, "Decrease", "Unchanged"))
        
    df_combined["sign"] = get_signs(df_combined["observed_delta_j"])
    
    signs_int = df_combined[df_combined["dataset"] == "Internal"]["sign"].value_counts()
    signs_ext = df_combined[df_combined["dataset"] == "External"]["sign"].value_counts()
    
    assert signs_int.get("Increase", 0) == 817
    assert signs_int.get("Decrease", 0) == 6814
    assert signs_int.get("Unchanged", 0) == 919
    
    assert signs_ext.get("Increase", 0) == 1846
    assert signs_ext.get("Decrease", 0) == 6253
    assert signs_ext.get("Unchanged", 0) == 1
    
    summary = df_combined.groupby(["dataset", "sign"]).size().reset_index(name="count")
    summary["proportion"] = summary.groupby("dataset")["count"].transform(lambda x: x / x.sum())
    summary.to_csv(FIG_DATA / "fig1_sign_summary.csv", index=False)
    print("Fig 1 Source Data built successfully.")

def build_fig2_source():
    # Explicitly updated with requested values
    df_fig2 = pd.DataFrame({
        "Dataset": ["Internal"]*5 + ["External"]*5,
        "Cardinality": [1, 2, 3, 4, 5]*2,
        "Jaccard": [0.915, 0.818, 0.746, 0.691, 0.630, 0.806, 0.700, 0.637, 0.591, 0.545],
        "Lower": [0.83, 0.75, 0.70, 0.68, 0.68, 0.788, 0.669, 0.609, 0.556, 0.513],
        "Upper": [0.87, 0.81, 0.76, 0.74, 0.73, 0.827, 0.726, 0.665, 0.628, 0.597]
    })
    df_fig2.to_csv(FIG_DATA / "fig2_cardinality.csv", index=False)
    print("Fig 2 Source Data built successfully.")

def build_fig3_source():
    df_fig3 = pd.DataFrame({
        "Context": ["Split-Half"]*8 + ["Transport"]*8,
        "Dataset": (["Internal"]*4 + ["External"]*4) * 2,
        "Method": ["Conjunction", "Mean", "RMS", "H1"] * 4,
        "Jaccard": [
            0.707, 0.944, 0.945, 0.942,
            0.545, 0.807, 0.779, 0.807,
            0.596, 0.933, 0.932, 0.929,
            0.518, 0.786, 0.744, 0.786
        ],
        "Lower": [
            0.6745725317153888, 0.9224137931034484, 0.9241920045045044, 0.9203539823008848,
            0.513, 0.779, 0.743, 0.779,
            np.nan, np.nan, np.nan, np.nan,
            0.283, 0.750, 0.686, 0.750
        ],
        "Upper": [
            0.7466653924692466, 0.9590163934426228, 0.9566781357522678, 0.9580489692535004,
            0.597, 0.843, 0.815, 0.843,
            np.nan, np.nan, np.nan, np.nan,
            0.414, 0.819, 0.767, 0.819
        ]
    })
    df_fig3.to_csv(FIG_DATA / "fig3_method_stability_transport.csv", index=False)
    print("Fig 3 Source Data built successfully.")

def build_fig4_source():
    df_fig4 = pd.DataFrame({
        "Context": ["Split-Half", "Split-Half", "Split-Half", "Split-Half", 
                    "Transport", "Transport", "Transport", "Transport"],
        "Comparison": ["Mean - Conj", "RMS - Conj", "H1 - Conj", "H1 - Mean"] * 2,
        "Median_Diff": [0.208, 0.186, 0.208, 0.000, 0.235, 0.192, 0.235, 0.000],
        "CI_2.5": [0.199, 0.166, 0.199, 0.000, 0.223, 0.175, 0.223, 0.000],
        "CI_97.5": [0.263, 0.222, 0.263, 0.000, 0.251, 0.216, 0.251, 0.000]
    })
    df_fig4.to_csv(FIG_DATA / "fig4_paired_differences.csv", index=False)
    print("Fig 4 Source Data built successfully.")

def build_fig5_source():
    df_fig5a = pd.DataFrame({
        "Duration": ["15 s"]*4 + ["30 s"]*4,
        "Method": ["Conjunction", "Mean", "RMS", "H1"] * 2,
        "Jaccard": [0.417, 0.722, 0.678, 0.722, 0.525, 0.769, 0.740, 0.769],
        "Lower": [0.370, 0.644, 0.604, 0.644, 0.491, 0.741, 0.712, 0.741],
        "Upper": [0.445, 0.755, 0.698, 0.755, 0.565, 0.802, 0.784, 0.802]
    })
    df_fig5a.to_csv(FIG_DATA / "fig5_calibration_duration_a.csv", index=False)

    df_fig5b = pd.DataFrame({
        "Method": ["Conjunction", "Mean", "RMS", "H1"],
        "Delta": [0.112, 0.069, 0.085, 0.069],
        "Lower": [0.094, 0.027, 0.045, 0.027],
        "Upper": [0.146, 0.094, 0.112, 0.094]
    })
    df_fig5b.to_csv(FIG_DATA / "fig5_calibration_duration_b.csv", index=False)

    df_fig5c = pd.DataFrame({
        "Duration": [15, 15, 15, 30, 30, 30, 45, 45, 45, 60, 60, 60],
        "Method": ["Conjunction", "RMS", "Mean & H1"] * 4,
        "Acceptance": [
            0.235, 0.475, 0.540,
            0.240, 0.479, 0.540,
            0.252, 0.494, 0.552,
            0.265, 0.513, 0.570
        ]
    })
    df_fig5c.to_csv(FIG_DATA / "fig5_calibration_duration_c.csv", index=False)
    print("Fig 5 Source Data built successfully.")

if __name__ == "__main__":
    build_fig1_source()
    build_fig2_source()
    build_fig3_source()
    build_fig4_source()
    build_fig5_source()
