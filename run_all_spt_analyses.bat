@echo off
setlocal
cd /d "%~dp0"
call conda activate smr-cn-revision
python simulations\spt1_fast_slow_model.py
python simulations\spt2_spt_validity.py
python simulations\spt3_barrier_interpretation.py
python empirical\spt4_empirical_timescales.py
python empirical\spt5_four_quadrant.py
python empirical\spt6_barrier_prediction.py
python code\spt7_framework_comparison.py
python code\spt8_figures.py
python code\spt_final_reports.py
endlocal
