#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(ggplot2)
  library(dplyr)
  library(scales)
})

args <- commandArgs(trailingOnly = FALSE)
script_arg <- sub("^--file=", "", args[grep("^--file=", args)])
script_dir <- dirname(normalizePath(script_arg))
root <- normalizePath(file.path(script_dir, "..", "..", ".."))
data_dir <- file.path(root, "results", "runtime_assurance_remediation", "figure_data")
figure_dir <- file.path(root, "results", "runtime_assurance_remediation", "figures")
dir.create(figure_dir, recursive = TRUE, showWarnings = FALSE)

theme_runtime <- theme_bw(base_size = 10) +
  theme(
    legend.position = "bottom",
    legend.title = element_blank(),
    legend.text = element_text(size = 8),
    panel.grid.minor = element_blank(),
    plot.title = element_blank()
  )

stability <- read.csv(file.path(data_dir, "calibration_stability_by_duration.csv")) %>%
  mutate(method_label = factor(method_label, levels = unique(method_label)))

p_stability <- ggplot(
  stability,
  aes(
    x = checkpoint_s,
    y = median_accepted_set_jaccard,
    group = method_label,
    colour = method_label,
    linetype = method_label,
    shape = method_label
  )
) +
  geom_hline(yintercept = 0.85, linewidth = 0.4, linetype = "dashed", colour = "grey35") +
  geom_line(linewidth = 0.55) +
  geom_point(size = 2.0, fill = "white") +
  scale_x_continuous(breaks = c(15, 30, 60, 90, 120)) +
  scale_y_continuous(limits = c(0, 1), breaks = seq(0, 1, 0.2)) +
  scale_colour_grey(start = 0.1, end = 0.75) +
  guides(colour = guide_legend(nrow = 2, byrow = TRUE)) +
  labs(x = "Available baseline checkpoint (s)", y = "Median accepted-set Jaccard") +
  theme_runtime

ggsave(file.path(figure_dir, "figure_calibration_stability.pdf"), p_stability, width = 7.2, height = 5.8, units = "in", device = cairo_pdf)
ggsave(file.path(figure_dir, "figure_calibration_stability.png"), p_stability, width = 7.2, height = 5.8, units = "in", dpi = 600, bg = "white")

comparison <- read.csv(file.path(data_dir, "calibration_method_comparison_90s.csv")) %>%
  mutate(
    method_label = factor(method_label, levels = unique(method_label)),
    label_offset = case_when(
      grepl("^C0", method_label) ~ 0.030,
      grepl("^C3", method_label) ~ -0.014,
      TRUE ~ 0.030
    )
  )

p_comparison <- ggplot(
  comparison,
  aes(
    x = median_decision_agreement,
    y = median_accepted_set_jaccard,
    shape = method_label,
    fill = method_label
  )
) +
  geom_vline(xintercept = 0.97, linewidth = 0.4, linetype = "dashed", colour = "grey35") +
  geom_hline(yintercept = 0.85, linewidth = 0.4, linetype = "dashed", colour = "grey35") +
  geom_point(size = 3.2, colour = "black") +
  geom_text(aes(y = median_accepted_set_jaccard + label_offset, label = sub(" .*", "", method_label)), size = 3, show.legend = FALSE) +
  scale_x_continuous(limits = c(0.94, 0.985), labels = label_number(accuracy = 0.01)) +
  scale_y_continuous(limits = c(0.45, 0.90), labels = label_number(accuracy = 0.1)) +
  scale_fill_grey(start = 0.2, end = 0.85) +
  guides(shape = guide_legend(nrow = 2, byrow = TRUE), fill = guide_legend(nrow = 2, byrow = TRUE)) +
  labs(x = "Median overall decision agreement", y = "Median accepted-set Jaccard") +
  theme_runtime

ggsave(file.path(figure_dir, "figure_calibration_method_comparison.pdf"), p_comparison, width = 7.2, height = 5.8, units = "in", device = cairo_pdf)
ggsave(file.path(figure_dir, "figure_calibration_method_comparison.png"), p_comparison, width = 7.2, height = 5.8, units = "in", dpi = 600, bg = "white")
