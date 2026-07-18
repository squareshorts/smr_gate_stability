suppressPackageStartupMessages({
  library(ggplot2)
  library(scales)
  library(patchwork)
})

script_arg <- commandArgs(trailingOnly = FALSE)[grep("--file=", commandArgs(trailingOnly = FALSE))][1]
script_path <- sub("^--file=", "", script_arg)
root <- normalizePath(file.path(dirname(script_path), "..", "..", ".."), winslash = "/", mustWork = TRUE)
data_dir <- file.path(root, "results", "baseline_gate_stability", "figure_data")
figure_dir <- file.path(root, "results", "baseline_gate_stability", "figures")
dir.create(figure_dir, recursive = TRUE, showWarnings = FALSE)

dataset_levels <- c("ds004447", "ds004444", "ds004446")
monitor_levels <- c("M0_NO_GATE", "M1_HIGH_BETA", "M2_BROADBAND_HIGH_FREQUENCY", "M3_AMPLITUDE_150", "M4_NFSQI_FULL_QUALITY", "M5_RIEMANNIAN_POTATO")
monitor_labels <- c("M0 No gate", "M1 High beta", "M2 Broadband/HF", "M3 Amplitude 150", "M4 NF-SQI full", "M5 Potato")
palette_cb <- c("#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00", "#56B4E9")
shapes_cb <- c(16, 17, 15, 18, 3, 8)

theme_study <- function() {
  theme_minimal(base_size = 9) +
    theme(
      text = element_text(colour = "black"),
      axis.text = element_text(size = 8),
      axis.title = element_text(size = 9),
      strip.text = element_text(size = 8, face = "bold"),
      legend.text = element_text(size = 8),
      panel.grid.minor = element_blank(),
      plot.margin = margin(5.5, 9, 5.5, 5.5)
    )
}

save_figure <- function(plot, number, width, height) {
  ggsave(file.path(figure_dir, paste0("figure", number, ".pdf")), plot, width = width, height = height, units = "in", device = cairo_pdf)
  ggsave(file.path(figure_dir, paste0("figure", number, ".png")), plot, width = width, height = height, units = "in", dpi = 600, bg = "white")
}

write_validation <- function(number, data, exact = TRUE) {
  write.csv(data.frame(figure = number, source_rows = nrow(data), exact_source_values = exact, no_plot_title = TRUE, dataset_order = paste(dataset_levels, collapse = ","), minimum_font_pt = 8), file.path(data_dir, paste0("figure", number, "_value_validation.csv")), row.names = FALSE)
}
