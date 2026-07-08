import json
import subprocess
import sys
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

def test_validation_script_help():
    result = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'validate_nfsqi_pseudo_online_reproduction.py'), '--help'], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'Validate pseudo-online reproduction' in result.stdout

def test_missing_data_skipped(tmp_path):
    out_json = tmp_path / 'out.json'
    out_md = tmp_path / 'out.md'
    
    cmd = [
        sys.executable, str(ROOT / 'scripts' / 'validate_nfsqi_pseudo_online_reproduction.py'),
        '--config', str(ROOT / 'configs' / 'nfsqi_smr_central.yaml'),
        '--mode', 'feature-level',
        '--datasets', 'ds004447',
        '--out-json', str(out_json),
        '--out-md', str(out_md),
        '--data-root', str(tmp_path),
        '--batch-results-root', str(tmp_path),
        '--allow-missing-data'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    
    assert out_json.exists()
    data = json.loads(out_json.read_text())
    assert 'ds004447' in data['datasets']
    assert data['datasets']['ds004447']['status'] == 'SKIPPED'
    assert 'Expected batch targets missing' in data['datasets']['ds004447']['reason']

def test_missing_data_fails_without_flag(tmp_path):
    out_json = tmp_path / 'out.json'
    out_md = tmp_path / 'out.md'
    
    cmd = [
        sys.executable, str(ROOT / 'scripts' / 'validate_nfsqi_pseudo_online_reproduction.py'),
        '--config', str(ROOT / 'configs' / 'nfsqi_smr_central.yaml'),
        '--mode', 'feature-level',
        '--datasets', 'ds004447',
        '--out-json', str(out_json),
        '--out-md', str(out_md),
        '--data-root', str(tmp_path),
        '--batch-results-root', str(tmp_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode != 0

def test_synthetic_exact_match(tmp_path, monkeypatch):
    from scripts import validate_nfsqi_pseudo_online_reproduction
    
    def mock_load_expected(batch_dir, ds):
        return {
            'task_windows': 100,
            'gate_a_accepted': 50,
            'clean_gate_a': 30,
            'quality_flagged_gate_a': 20,
            'gate_b_accepted': 40,
            'gate_c_accepted': 30,
            'high_beta_blocks': 10,
            'full_nfsqi_blocks': 20
        }
        
    def mock_process_dataset(ds, config, features_csv):
        return {
            'task_windows': 100,
            'gate_a_accepted': 50,
            'clean_gate_a': 30,
            'quality_flagged_gate_a': 20,
            'gate_b_accepted': 40,
            'gate_c_accepted': 30,
            'high_beta_blocks': 10,
            'full_nfsqi_blocks': 20
        }
        
    monkeypatch.setattr(validate_nfsqi_pseudo_online_reproduction, 'load_expected_batch_targets', mock_load_expected)
    monkeypatch.setattr(validate_nfsqi_pseudo_online_reproduction, 'process_feature_level', mock_process_dataset)
    monkeypatch.setattr(validate_nfsqi_pseudo_online_reproduction, 'find_feature_csv', lambda ds: Path('dummy.csv'))
    
    out_json = tmp_path / 'out.json'
    out_md = tmp_path / 'out.md'
    
    sys.argv = [
        'validate_nfsqi_pseudo_online_reproduction.py',
        '--config', str(ROOT / 'configs' / 'nfsqi_smr_central.yaml'),
        '--mode', 'feature-level',
        '--datasets', 'ds004447',
        '--out-json', str(out_json),
        '--out-md', str(out_md),
        '--data-root', str(tmp_path),
        '--batch-results-root', str(tmp_path)
    ]
    
    validate_nfsqi_pseudo_online_reproduction.main()
    
    data = json.loads(out_json.read_text())
    assert data['datasets']['ds004447']['status'] == 'PASS'
    identities = data['datasets']['ds004447']['identities']
    assert identities["gate_a_accepted == clean + quality_flagged"]
    assert identities["gate_c_accepted == clean_gate_a"]
    assert identities["full_nfsqi_blocks == gate_a - gate_c"]
    assert identities["high_beta_blocks == gate_a - gate_b"]

def test_synthetic_mismatch(tmp_path, monkeypatch):
    from scripts import validate_nfsqi_pseudo_online_reproduction
    
    def mock_load_expected(batch_dir, ds):
        return {
            'task_windows': 100,
            'gate_a_accepted': 50,
            'clean_gate_a': 30,
            'quality_flagged_gate_a': 20,
            'gate_b_accepted': 40,
            'gate_c_accepted': 30,
            'high_beta_blocks': 10,
            'full_nfsqi_blocks': 20
        }
        
    def mock_process_dataset_mismatch(ds, config, data_root):
        return {
            'task_windows': 100,
            'gate_a_accepted': 49, # mismatch here
            'clean_gate_a': 30,
            'quality_flagged_gate_a': 19,
            'gate_b_accepted': 40,
            'gate_c_accepted': 30,
            'high_beta_blocks': 9,
            'full_nfsqi_blocks': 19
        }
        
    monkeypatch.setattr(validate_nfsqi_pseudo_online_reproduction, 'load_expected_batch_targets', mock_load_expected)
    monkeypatch.setattr(validate_nfsqi_pseudo_online_reproduction, 'process_feature_level', mock_process_dataset_mismatch)
    monkeypatch.setattr(validate_nfsqi_pseudo_online_reproduction, 'find_feature_csv', lambda ds: Path('dummy.csv'))
    
    out_json = tmp_path / 'out.json'
    out_md = tmp_path / 'out.md'
    
    sys.argv = [
        'validate_nfsqi_pseudo_online_reproduction.py',
        '--config', str(ROOT / 'configs' / 'nfsqi_smr_central.yaml'),
        '--mode', 'feature-level',
        '--datasets', 'ds004447',
        '--out-json', str(out_json),
        '--out-md', str(out_md),
        '--data-root', str(tmp_path),
        '--batch-results-root', str(tmp_path)
    ]
    
    try:
        validate_nfsqi_pseudo_online_reproduction.main()
        assert False, "Should have exited with 1"
    except SystemExit as e:
        assert e.code == 1
        
    data = json.loads(out_json.read_text())
    assert data['datasets']['ds004447']['status'] == 'FAIL'
    assert data['datasets']['ds004447']['deltas']['gate_a_accepted'] == 1
