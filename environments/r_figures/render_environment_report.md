# R render environment report

Host: R is installed on the user's Windows machine.
Sandbox: the isolated Linux analysis sandbox has no R and cannot reach the host R (no /mnt/c, no
root, offline mirror). One bounded recovery attempt (apt/micromamba) failed. Python was NOT
substituted. R sources + frozen source data + value-validation are complete; rendering deferred to host.

To render + capture environment on the host:
  cd scripts/conjunctive_gate_stability/figures_r
  Rscript -e 'writeLines(capture.output(sessionInfo()), "../../../environments/r_figures/R_sessionInfo.txt")'
  Rscript ../render_all_figures.R
Required packages: ggplot2 (+ cairo for cairo_pdf). Install into an isolated library if missing:
  Rscript -e '.libPaths("environments/r_figures/.Rlib"); install.packages("ggplot2", repos="https://cloud.r-project.org")'
