.libPaths("R_libs")
library(tidyverse)
library(ggplot2)
library(patchwork)
library(readr)
library(stringr)
library(scales)

# Fallback to cairo_pdf if ragg is missing
pdf_device <- if (requireNamespace("ragg", quietly = TRUE)) "cairo_pdf" else grDevices::cairo_pdf

# 1. Load Data
ci_data <- read_csv("results/submission_readiness/bootstrap_ci_all_variants.csv")

# Filter for snr_primary
df_primary <- ci_data %>% filter(Variant == "snr_primary")

# 2. Prepare Figure 6 Panel A Data (Gate Blocking)
panel_a_data <- df_primary %>%
  filter(Metric %in% c("Blk_HB_Pct", "Blk_BBNF_Pct", "Blk_Full_Pct")) %>%
  mutate(
    Gate = case_when(
      Metric == "Blk_HB_Pct" ~ "High beta",
      Metric == "Blk_BBNF_Pct" ~ "Broadband/noise-floor",
      Metric == "Blk_Full_Pct" ~ "Full NF-SQI"
    ),
    Gate = factor(Gate, levels = c("High beta", "Broadband/noise-floor", "Full NF-SQI")),
    Dataset = factor(Dataset, levels = c("ds004447", "ds004444", "ds004446"))
  )

# Print verification values
cat("Verification - Panel A (Dataset ds004447):\n")
print(panel_a_data %>% filter(Dataset == "ds004447") %>% select(Gate, Mean))
cat("Verification - Panel A (Dataset ds004444):\n")
print(panel_a_data %>% filter(Dataset == "ds004444") %>% select(Gate, Mean))
cat("Verification - Panel A (Dataset ds004446):\n")
print(panel_a_data %>% filter(Dataset == "ds004446") %>% select(Gate, Mean))


# Prepare Figure 6 Panel B Data (AUC)
panel_b_data <- df_primary %>%
  filter(Metric %in% c("High_Beta_Only_AUC", "Broadband_Noise_Floor_Only_AUC", "Broadband_Noise_Floor_+_High_Beta_AUC", "Full_NF-SQI_AUC")) %>%
  mutate(
    Model = case_when(
      Metric == "High_Beta_Only_AUC" ~ "High beta",
      Metric == "Broadband_Noise_Floor_Only_AUC" ~ "Broadband/noise-floor",
      Metric == "Broadband_Noise_Floor_+_High_Beta_AUC" ~ "BB/noise + high beta",
      Metric == "Full_NF-SQI_AUC" ~ "Full NF-SQI"
    ),
    Model = factor(Model, levels = c("High beta", "Broadband/noise-floor", "BB/noise + high beta", "Full NF-SQI")),
    Dataset = factor(Dataset, levels = c("ds004447", "ds004444", "ds004446"))
  )

cat("\nVerification - Panel B (AUC ds004447):\n")
print(panel_b_data %>% filter(Dataset == "ds004447") %>% select(Model, Mean))
cat("Verification - Panel B (AUC ds004444):\n")
print(panel_b_data %>% filter(Dataset == "ds004444") %>% select(Model, Mean))
cat("Verification - Panel B (AUC ds004446):\n")
print(panel_b_data %>% filter(Dataset == "ds004446") %>% select(Model, Mean))


# 3. Colors
color_palette <- c("High beta" = "#E69F00", 
                   "Broadband/noise-floor" = "#56B4E9", 
                   "BB/noise + high beta" = "#009E73", 
                   "Full NF-SQI" = "#D55E00")

# 4. Generate Figure 6 Panel A
p_a <- ggplot(panel_a_data, aes(x = Dataset, y = Mean, fill = Gate)) +
  geom_bar(stat = "identity", position = position_dodge(width = 0.8), width = 0.7) +
  geom_errorbar(aes(ymin = CI_Lower, ymax = CI_Upper), position = position_dodge(width = 0.8), width = 0.25) +
  scale_fill_manual(values = color_palette) +
  scale_y_continuous(limits = c(0, 105), expand = c(0,0)) +
  labs(y = "Blocked windows (%)", x = "Dataset", fill = "Gate criteria") +
  theme_classic(base_size = 12) +
  theme(legend.position = "bottom",
        axis.text = element_text(color = "black")) +
  guides(fill = guide_legend(nrow = 2, byrow = TRUE))

# Generate Figure 6 Panel B
p_b <- ggplot(panel_b_data, aes(x = Dataset, y = Mean, fill = Model)) +
  geom_bar(stat = "identity", position = position_dodge(width = 0.8), width = 0.7) +
  geom_errorbar(aes(ymin = CI_Lower, ymax = CI_Upper), position = position_dodge(width = 0.8), width = 0.25) +
  scale_fill_manual(values = color_palette) +
  coord_cartesian(ylim = c(0.45, 0.90)) +
  labs(y = "LOSO AUC", x = "Dataset", fill = "Model") +
  theme_classic(base_size = 12) +
  theme(legend.position = "bottom",
        axis.text = element_text(color = "black")) +
  guides(fill = guide_legend(nrow = 2, byrow = TRUE))

# Figure 6 Assembly
fig6 <- p_a + p_b + plot_annotation(tag_levels = 'A')

# 5. Save Figure 6
ggsave("figures/submission_readiness/fig6_cross_dataset_clean.pdf", fig6, width = 10, height = 5, device = cairo_pdf)
ggsave("figures/submission_readiness/fig6_cross_dataset_clean.png", fig6, width = 10, height = 5, dpi = 300)
ggsave("figures/submission_readiness/fig6_cross_dataset_clean.tiff", fig6, width = 10, height = 5, dpi = 300)

# 6. Model Comparison Clean Figure (Replacement for nf_sqi_model_comparison.pdf)
# Horizontal point range plot
p_model_comp <- ggplot(panel_b_data, aes(x = Mean, y = Model, color = Model)) +
  geom_pointrange(aes(xmin = CI_Lower, xmax = CI_Upper), size = 1) +
  facet_wrap(~Dataset, ncol = 1) +
  scale_color_manual(values = color_palette) +
  coord_cartesian(xlim = c(0.45, 0.90)) +
  labs(x = "LOSO AUC", y = NULL) +
  theme_bw(base_size = 12) +
  theme(legend.position = "none",
        axis.text = element_text(color = "black"),
        strip.background = element_rect(fill = "white"))

ggsave("figures/submission_readiness/fig_model_comparison_clean.pdf", p_model_comp, width = 6, height = 6, device = cairo_pdf)
ggsave("figures/submission_readiness/fig_model_comparison_clean.png", p_model_comp, width = 6, height = 6, dpi = 300)

# 7. Gate Blocking Clean Figure (Replacement for nf_sqi_contamination_overlap_bar.pdf)
# Component-wise plot + full cross-dataset blocks
gate_blocking_data <- df_primary %>%
  filter(Metric %in% c("HB_Only_Pct", "BB_Only_Pct", "Ch_Inc_Only_Pct", "Multi_Contam_Pct", "Blk_Full_Pct", "Blk_HB_Pct", "Blk_BBNF_Pct")) %>%
  mutate(
    Metric_Clean = case_when(
      Metric == "HB_Only_Pct" ~ "High beta (only)",
      Metric == "BB_Only_Pct" ~ "Broadband/noise-floor (only)",
      Metric == "Ch_Inc_Only_Pct" ~ "Channel inconsistency (only)",
      Metric == "Multi_Contam_Pct" ~ "Multiple contaminations",
      Metric == "Blk_HB_Pct" ~ "High beta (marginal)",
      Metric == "Blk_BBNF_Pct" ~ "Broadband/noise-floor (marginal)",
      Metric == "Blk_Full_Pct" ~ "Full NF-SQI"
    ),
    Dataset = factor(Dataset, levels = c("ds004447", "ds004444", "ds004446"))
  ) %>%
  mutate(Metric_Clean = reorder(Metric_Clean, Mean))

p_gate_blocking <- ggplot(gate_blocking_data, aes(x = Mean, y = Metric_Clean)) +
  geom_pointrange(aes(xmin = CI_Lower, xmax = CI_Upper), color = "black", size = 0.8) +
  facet_wrap(~Dataset, ncol = 1) +
  scale_x_continuous(limits = c(0, 105)) +
  labs(x = "Blocked windows (%)", y = NULL) +
  theme_bw(base_size = 12) +
  theme(axis.text = element_text(color = "black"),
        strip.background = element_rect(fill = "white"))

ggsave("figures/submission_readiness/fig_gate_blocking_clean.pdf", p_gate_blocking, width = 6, height = 8, device = cairo_pdf)
ggsave("figures/submission_readiness/fig_gate_blocking_clean.png", p_gate_blocking, width = 6, height = 8, dpi = 300)
