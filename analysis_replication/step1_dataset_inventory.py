import os
import sys
from pathlib import Path
import pandas as pd
import json

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from empirical.nf_sqi_common import (
    OPENNEURO_DATASETS, select_first_last_subset, download_one_file,
    scan_local_inventory, utc_now
)

def main():
    os.makedirs('outputs/replication_tables', exist_ok=True)
    os.makedirs('outputs/replication_logs', exist_ok=True)
    log_path = ROOT / "outputs" / "replication_logs" / "dataset_download.log"

    datasets = ['ds004444', 'ds004446', 'ds004447', 'ds004448']

    for dataset_id in datasets:
        print(f"Checking {dataset_id}...")
        raw_root = ROOT / "data" / "raw" / "openneuro" / dataset_id

        # Check if we have EDFs
        edfs = list(raw_root.rglob("*.edf"))
        if len(edfs) < 2:
            print(f"Dataset {dataset_id} seems missing or incomplete locally. Initiating lightweight download (first/last session).")
            selected_files_df, selected_files = select_first_last_subset(dataset_id)
            for idx, item in enumerate(selected_files, start=1):
                # print(f"Downloading {idx}/{len(selected_files)}: {item['filename']}")
                download_one_file(item, raw_root / item["filename"], log_path)
        else:
            print(f"Dataset {dataset_id} already has local EDFs ({len(edfs)}). Skipping download.")

    # Now scan local inventory
    inventory = scan_local_inventory("replication_check")

    # Save outputs
    inventory.to_csv("outputs/replication_tables/dataset_inventory.csv", index=False)

    # Save md
    with open("outputs/replication_logs/dataset_inventory.md", "w", encoding="utf-8") as f:
        f.write("# Dataset Replication Inventory\n\n")
        f.write(f"Generated: {utc_now()}\n\n")
        for _, row in inventory.iterrows():
            if row['dataset_id'] not in datasets:
                continue
            f.write(f"## {row['dataset_id']}\n")
            f.write(f"- Subjects: {row['local_subject_count']}\n")
            f.write(f"- Sessions: {row['local_session_count']}\n")
            f.write(f"- EDF files: {row['local_eeg_file_count']}\n")
            f.write(f"- Sampling rates: {row['sampling_rates']}\n")
            f.write(f"- Event markers: {row['event_markers']}\n")
            ch_list = str(row['channels']).split(';')
            f.write(f"- Total channels: {len(ch_list)}\n")
            f.write(f"- Sensorimotor: {row['sensorimotor_channels_found']}\n")
            suitability = row.get('suitability_for_nfsqi', row.get('suitability_for_beta_state_persistence', 'NA'))
            f.write(f"- Suitability: {suitability}\n\n")

if __name__ == '__main__':
    main()
