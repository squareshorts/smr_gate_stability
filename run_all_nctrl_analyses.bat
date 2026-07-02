@echo off
REM NCTRL full pipeline runner
REM Run from repo root: C:\work\smr_cn_revision

call conda activate smr-cn-revision
if %errorlevel% neq 0 (
    echo ERROR: conda activate smr-cn-revision failed
    exit /b 1
)

echo ============================================================
echo NCTRL1 + NCTRL2: Active-damping simulation + metrics
echo ============================================================
python simulations\nctrl1_active_damping_model.py
if %errorlevel% neq 0 ( echo ERROR in NCTRL1. Aborting. & exit /b 1 )

echo ============================================================
echo NCTRL3: Empirical noise-floor analysis
echo ============================================================
python empirical\nctrl3_noise_floor_analysis.py
if %errorlevel% neq 0 ( echo ERROR in NCTRL3. Aborting. & exit /b 1 )

echo ============================================================
echo NCTRL4: Burst instability + diffusion
echo ============================================================
python empirical\nctrl4_burst_instability.py
if %errorlevel% neq 0 ( echo ERROR in NCTRL4. Aborting. & exit /b 1 )

echo ============================================================
echo NCTRL5: Four-quadrant noise-control classification
echo ============================================================
python empirical\nctrl5_four_quadrant_noise.py
if %errorlevel% neq 0 ( echo ERROR in NCTRL5. Aborting. & exit /b 1 )

echo ============================================================
echo NCTRL6: Reward-quality state analysis
echo ============================================================
python empirical\nctrl6_reward_quality.py
if %errorlevel% neq 0 ( echo ERROR in NCTRL6. Aborting. & exit /b 1 )

echo ============================================================
echo NCTRL7: Framework comparison
echo ============================================================
python code\nctrl7_framework_comparison.py
if %errorlevel% neq 0 ( echo ERROR in NCTRL7. Aborting. & exit /b 1 )

echo ============================================================
echo NCTRL8: Manuscript-candidate figure assembly
echo ============================================================
python code\nctrl8_figures.py
if %errorlevel% neq 0 ( echo ERROR in NCTRL8. Aborting. & exit /b 1 )

echo ============================================================
echo NCTRL Final Reports + manifest update
echo ============================================================
python code\nctrl_final_reports.py
if %errorlevel% neq 0 ( echo ERROR in final reports. & exit /b 1 )

echo ============================================================
echo ALL NCTRL ANALYSES COMPLETE
echo ============================================================
