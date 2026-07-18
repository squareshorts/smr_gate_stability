#!/usr/bin/env Rscript

root <- normalizePath(file.path(getwd()), winslash = "/", mustWork = TRUE)
out_dir <- file.path(root, "results/runtime_assurance_remediation/figures")
data_dir <- file.path(root, "results/runtime_assurance_remediation/figure_data")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(data_dir, recursive = TRUE, showWarnings = FALSE)

scheduler <- read.csv(file.path(root, "results/runtime_assurance_remediation/scheduler/scheduler_comparison.csv"))
scorecard <- read.csv(file.path(root, "results/runtime_assurance_remediation/final_verification_scorecard.csv"))

write.csv(scheduler, file.path(data_dir, "figure_scheduler_tradeoff_data.csv"), row.names = FALSE)
write.csv(scorecard, file.path(data_dir, "figure_scorecard_data.csv"), row.names = FALSE)

status_cols <- c(pass = "#0072B2", partial = "#E69F00", fail = "#D55E00")

pdf(file.path(out_dir, "figure_scheduler_tradeoff.pdf"), width = 7, height = 4.8, onefile = FALSE)
par(mar = c(8, 5, 2, 2), cex = 0.9)
plot(
  scheduler$median_displayed_reward_time_percent,
  scheduler$median_display_transitions_per_min,
  pch = 21,
  bg = ifelse(scheduler$frozen_scheduler_status == "pass", "#0072B2", "#D55E00"),
  col = "black",
  xlab = "Displayed reward time (%)",
  ylab = "Displayed transitions/min",
  ylim = c(0, max(17, scheduler$median_display_transitions_per_min, na.rm = TRUE) * 1.05)
)
abline(h = 4, lty = 2, col = "gray35")
text(
  scheduler$median_displayed_reward_time_percent,
  scheduler$median_display_transitions_per_min,
  labels = scheduler$scheduler,
  pos = 4,
  cex = 0.7,
  xpd = NA
)
dev.off()

png(file.path(out_dir, "figure_scheduler_tradeoff.png"), width = 7, height = 4.8, units = "in", res = 600)
par(mar = c(8, 5, 2, 2), cex = 0.9)
plot(
  scheduler$median_displayed_reward_time_percent,
  scheduler$median_display_transitions_per_min,
  pch = 21,
  bg = ifelse(scheduler$frozen_scheduler_status == "pass", "#0072B2", "#D55E00"),
  col = "black",
  xlab = "Displayed reward time (%)",
  ylab = "Displayed transitions/min",
  ylim = c(0, max(17, scheduler$median_display_transitions_per_min, na.rm = TRUE) * 1.05)
)
abline(h = 4, lty = 2, col = "gray35")
text(
  scheduler$median_displayed_reward_time_percent,
  scheduler$median_display_transitions_per_min,
  labels = scheduler$scheduler,
  pos = 4,
  cex = 0.7,
  xpd = NA
)
dev.off()

pdf(file.path(out_dir, "figure_scorecard.pdf"), width = 7.2, height = 4.8, onefile = FALSE)
par(mar = c(8, 9, 2, 2), cex = 0.85)
status <- factor(scorecard$status, levels = c("fail", "partial", "pass"))
barplot(
  rep(1, nrow(scorecard)),
  names.arg = scorecard$requirement,
  horiz = TRUE,
  las = 1,
  col = status_cols[as.character(scorecard$status)],
  border = "black",
  xlab = "Requirement evaluated"
)
legend("bottomright", legend = names(status_cols), fill = status_cols, bty = "n")
dev.off()

png(file.path(out_dir, "figure_scorecard.png"), width = 7.2, height = 4.8, units = "in", res = 600)
par(mar = c(8, 9, 2, 2), cex = 0.85)
barplot(
  rep(1, nrow(scorecard)),
  names.arg = scorecard$requirement,
  horiz = TRUE,
  las = 1,
  col = status_cols[as.character(scorecard$status)],
  border = "black",
  xlab = "Requirement evaluated"
)
legend("bottomright", legend = names(status_cols), fill = status_cols, bty = "n")
dev.off()

validation <- data.frame(
  figure = c("figure_scheduler_tradeoff", "figure_scorecard"),
  source_rows = c(nrow(scheduler), nrow(scorecard)),
  has_title = c(FALSE, FALSE),
  generated_from_completed_data = c(TRUE, TRUE)
)
write.csv(validation, file.path(root, "results/runtime_assurance_remediation/figure_value_validation.csv"), row.names = FALSE)
writeLines(
  c(
    "# Figure render QC",
    "",
    "- Generated in R from frozen CSV outputs.",
    "- No plot titles were added.",
    "- External baseline, degradation, and calibration-remediation figures were not rendered because those analyses are incomplete."
  ),
  file.path(root, "results/runtime_assurance_remediation/figure_render_qc.md")
)

source_map <- data.frame(
  figure = c("figure_scheduler_tradeoff", "figure_scorecard"),
  r_source = "scripts/runtime_assurance_remediation/figures_r/figure_scheduler_and_scorecard.R",
  source_data = c(
    "results/runtime_assurance_remediation/figure_data/figure_scheduler_tradeoff_data.csv",
    "results/runtime_assurance_remediation/figure_data/figure_scorecard_data.csv"
  ),
  pdf = c(
    "results/runtime_assurance_remediation/figures/figure_scheduler_tradeoff.pdf",
    "results/runtime_assurance_remediation/figures/figure_scorecard.pdf"
  ),
  png = c(
    "results/runtime_assurance_remediation/figures/figure_scheduler_tradeoff.png",
    "results/runtime_assurance_remediation/figures/figure_scorecard.png"
  )
)
write.csv(source_map, file.path(root, "results/runtime_assurance_remediation/figure_source_map.csv"), row.names = FALSE)
