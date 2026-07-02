@echo off
setlocal
cd /d "%~dp0"
python simulations\wp1_stuart_landau_validity.py --grid reduced
python simulations\wp2_weak_coupling_checks.py --grid reduced
python simulations\wp3_null_models.py --grid reduced
python simulations\wp4_criticality.py --grid reduced
python simulations\wp5_burst_threshold_surrogates.py --grid reduced
python simulations\wp6_parameter_regime_map.py --grid reduced
python figures\wp9_cn_figures.py
python empirical\wp7_dataset_plan_inventory.py --download
python empirical\wp8_empirical_analysis.py
python code\generate_final_reports.py
python utils\manifest.py
endlocal
