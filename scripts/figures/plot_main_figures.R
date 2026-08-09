library(ggplot2)
library(dplyr)
library(patchwork)
library(scales)

out_dir <- "results/figure_source_data/"
dir.create(out_dir, showWarnings = FALSE)

theme_pub <- function() {
  theme_minimal(base_size = 9, base_family = "sans") +
    theme(
      plot.title = element_blank(),
      plot.subtitle = element_blank(),
      panel.grid.minor = element_blank(),
      panel.grid.major = element_line(color = "grey90", linewidth = 0.3),
      panel.border = element_rect(fill = NA, color = "grey20", linewidth = 0.5),
      axis.title = element_text(face = "bold", size = 9),
      axis.text = element_text(color = "grey20", size = 8),
      legend.position = "bottom",
      legend.title = element_blank(),
      legend.text = element_text(size = 8),
      legend.key.size = unit(0.4, "cm"),
      strip.background = element_blank(),
      strip.text = element_text(face = "bold", size = 9, hjust = 0)
    )
}

save_plot <- function(filename, plot, width = 6, height = 4) {
  ggsave(paste0(out_dir, filename, ".pdf"), plot, width = width, height = height, device = "pdf")
  ggsave(paste0(out_dir, filename, ".svg"), plot, width = width, height = height, device = "svg")
  ggsave(paste0(out_dir, filename, ".png"), plot, width = width, height = height, dpi = 600, device = "png")
}

# ---------------------------------------------------------
# Figure 1 - Composition Law
# ---------------------------------------------------------
df_rect_before <- data.frame(
  xmin = c(0.13, 0.315, 0.685),
  xmax = c(0.315, 0.685, 0.87),
  ymin = c(0.68, 0.68, 0.68),
  ymax = c(0.77, 0.77, 0.77),
  label = c("U[1]", "M", "U[2]")
)

df_rect_after <- data.frame(
  xmin = c(0.13, 0.315, 0.43833, 0.56167, 0.685),
  xmax = c(0.315, 0.43833, 0.56167, 0.685, 0.87),
  ymin = c(0.31, 0.31, 0.31, 0.31, 0.31),
  ymax = c(0.40, 0.40, 0.40, 0.40, 0.40),
  label = c("x[1]", "e[1]", "c", "e[2]", "x[2]")
)

p1a <- ggplot() +
  # Header 1
  annotate("text", x = 0.5, y = 0.84, label = "Before criterion addition", size = 4) +
  
  # Top schematic
  geom_rect(data = df_rect_before, aes(xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax), fill="white", color="black", linewidth=0.5) +
  geom_text(data = df_rect_before, aes(x=(xmin+xmax)/2, y=(ymin+ymax)/2, label=label), parse=TRUE, size=4) +
  
  # Transition block
  geom_segment(aes(x=0.5, y=0.60, xend=0.5, yend=0.54), arrow = arrow(length=unit(0.2, "cm")), linewidth=0.5) +
  
  # Header 2
  annotate("text", x = 0.5, y = 0.48, label = "After criterion addition", size = 4) +
  
  # Bottom schematic
  geom_rect(data = df_rect_after, aes(xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax), fill="white", color="black", linewidth=0.5) +
  geom_text(data = df_rect_after, aes(x=(xmin+xmax)/2, y=(ymin+ymax)/2, label=label), parse=TRUE, size=4) +
  
  # Mapping Cues (light gray guide lines)
  geom_segment(aes(x=0.315, y=0.68, xend=0.315, yend=0.40), color="grey80", linewidth=0.3) +
  geom_segment(aes(x=0.685, y=0.68, xend=0.685, yend=0.40), color="grey80", linewidth=0.3) +
  
  xlim(0, 1) + ylim(0, 1) +
  theme_void() +
  theme(plot.margin = margin(10, 10, 10, 10))

df_fig1_data <- read.csv("results/figure_source_data/fig1_composition_edges.csv")
p1b <- ggplot(df_fig1_data, aes(x = observed_delta_j, y = reconstructed_delta_j, color = dataset, shape = dataset)) +
  geom_abline(intercept = 0, slope = 1, linetype = "dashed", color = "grey70") +
  geom_point(alpha = 0.2, size = 1.5) +
  annotate("text", x = -0.7, y = 0.15, label = "Max |error| = 0.0\nSign agreement = 100%", size = 3, hjust = 0) +
  scale_color_manual(values = c("Internal" = "grey30", "External" = "#d95f02")) +
  labs(x = expression("Observed "*Delta*J), y = expression("Reconstructed "*Delta*J)) +
  theme_pub() + theme(legend.position = "none", plot.margin = margin(t=15, r=10, b=5, l=15))

df_fig1c_raw <- read.csv("results/figure_source_data/fig1_sign_summary.csv")
df_fig1c <- data.frame(
  Dataset = df_fig1c_raw$dataset,
  Outcome = factor(df_fig1c_raw$sign, levels=rev(c("Increase", "Unchanged", "Decrease"))),
  Proportion = df_fig1c_raw$proportion
)
p1c <- ggplot(df_fig1c, aes(x = Proportion, y = Dataset, fill = Outcome)) +
  geom_bar(stat = "identity", position = "fill", width = 0.6) +
  scale_fill_manual(values = c("Increase" = "#2c7bb6", "Decrease" = "#d7191c", "Unchanged" = "#fdae61")) +
  scale_x_continuous(labels = scales::percent) +
  labs(x = "Proportion of Lattice Edges", y = "") +
  theme_pub()

fig1 <- (p1a | p1b | p1c) + plot_layout(widths = c(1.25, 1, 1)) + plot_annotation(tag_levels = 'A')
save_plot("fig1_composition_law", fig1, width = 10, height = 3.5)

# ---------------------------------------------------------
# Figure 2 - Cardinality Instability
# ---------------------------------------------------------
df_fig2 <- read.csv("results/figure_source_data/fig2_cardinality.csv")
fig2 <- ggplot(df_fig2, aes(x = Cardinality, y = Jaccard, color = Dataset, shape = Dataset)) +
  geom_line(aes(group = Dataset), position = position_dodge(0.1)) +
  geom_point(position = position_dodge(0.1), size = 2.5) +
  geom_errorbar(aes(ymin = Lower, ymax = Upper), width = 0.1, position = position_dodge(0.1)) +
  scale_color_manual(values = c("Internal" = "grey30", "External" = "#d95f02")) +
  ylim(0.4, 1.0) +
  labs(x = "Conjunctive Cardinality", y = "Split-Half Jaccard Index") +
  theme_pub()
save_plot("fig2_cardinality", fig2, width = 5, height = 4)

# ---------------------------------------------------------
# Figure 3 - Method Stability and Transport
# ---------------------------------------------------------
df_fig3 <- read.csv("results/figure_source_data/fig3_method_stability_transport.csv")
df_fig3$Method <- factor(df_fig3$Method, levels = c("Conjunction", "RMS", "Mean", "H1"))

p3a <- ggplot(subset(df_fig3, Context == "Split-Half" & Dataset == "Internal"), aes(x = Method, y = Jaccard, color = Method)) +
  geom_point(size = 3) + geom_errorbar(aes(ymin = Lower, ymax = Upper), width = 0.2) + ylim(0.25, 1.0) + theme_pub() + theme(axis.title.x = element_blank())
p3b <- ggplot(subset(df_fig3, Context == "Split-Half" & Dataset == "External"), aes(x = Method, y = Jaccard, color = Method)) +
  geom_point(size = 3) + geom_errorbar(aes(ymin = Lower, ymax = Upper), width = 0.2) + ylim(0.25, 1.0) + theme_pub() + theme(axis.title.x = element_blank(), axis.text.y = element_blank(), axis.title.y = element_blank())
p3c <- ggplot(subset(df_fig3, Context == "Transport" & Dataset == "Internal"), aes(x = Method, y = Jaccard, color = Method)) +
  geom_point(size = 3) + geom_errorbar(aes(ymin = Lower, ymax = Upper), width = 0.2) + ylim(0.25, 1.0) + theme_pub() + theme(axis.title.x = element_blank())
p3d <- ggplot(subset(df_fig3, Context == "Transport" & Dataset == "External"), aes(x = Method, y = Jaccard, color = Method)) +
  geom_point(size = 3) + geom_errorbar(aes(ymin = Lower, ymax = Upper), width = 0.2) + ylim(0.25, 1.0) + theme_pub() + theme(axis.title.x = element_blank(), axis.text.y = element_blank(), axis.title.y = element_blank())

fig3 <- (p3a | p3b) / (p3c | p3d) + plot_layout(guides = 'collect') + plot_annotation(tag_levels = 'A') & scale_color_manual(values = c("H1"="#e7298a", "Mean"="#1b9e77", "RMS"="#7570b3", "Conjunction"="#d95f02"))
save_plot("fig3_method_stability_transport", fig3, width = 7, height = 5)

# ---------------------------------------------------------
# Figure 4 - Paired Differences
# ---------------------------------------------------------
df_fig4 <- read.csv("results/figure_source_data/fig4_paired_differences.csv")
df_fig4$Comparison <- factor(df_fig4$Comparison, levels = rev(c("Mean - Conj", "RMS - Conj", "H1 - Conj", "H1 - Mean")))

p4a <- ggplot(subset(df_fig4, Context == "Split-Half"), aes(x = Median_Diff, y = Comparison)) +
  geom_vline(xintercept = 0, linetype = "dashed", color = "grey70") +
  geom_errorbar(aes(xmin = CI_2.5, xmax = CI_97.5), width = 0.2, color = "black") +
  geom_point(size = 3, shape = 21, fill = "white", color = "black") +
  labs(x = "Paired Participant-Level Difference", y = "") +
  theme_pub()

p4b <- ggplot(subset(df_fig4, Context == "Transport"), aes(x = Median_Diff, y = Comparison)) +
  geom_vline(xintercept = 0, linetype = "dashed", color = "grey70") +
  geom_errorbar(aes(xmin = CI_2.5, xmax = CI_97.5), width = 0.2, color = "black") +
  geom_point(size = 3, shape = 21, fill = "white", color = "black") +
  labs(x = "Paired Participant-Level Difference", y = "") +
  theme_pub() + theme(axis.text.y = element_blank(), axis.title.y = element_blank())

fig4 <- (p4a | p4b) + plot_annotation(tag_levels = 'A')
save_plot("fig4_paired_differences", fig4, width = 7, height = 3)

# ---------------------------------------------------------
# Figure 5 - Calibration Duration
# ---------------------------------------------------------
df_fig5a <- read.csv("results/figure_source_data/fig5_calibration_duration_a.csv")
df_fig5a$Method <- factor(df_fig5a$Method, levels = rev(c("Conjunction", "RMS", "Mean", "H1")))
p5a <- ggplot(df_fig5a, aes(x = Jaccard, y = Method, color = Duration)) +
  geom_point(position = position_dodge(0.5), size = 2.5) +
  geom_errorbar(aes(xmin = Lower, xmax = Upper), width = 0.2, position = position_dodge(0.5)) +
  scale_color_manual(values = c("15 s" = "grey50", "30 s" = "black")) +
  labs(x = "Split-Half Jaccard") +
  theme_pub() + theme(axis.title.y = element_blank())

df_fig5b <- read.csv("results/figure_source_data/fig5_calibration_duration_b.csv")
df_fig5b$Method <- factor(df_fig5b$Method, levels = rev(c("Conjunction", "RMS", "Mean", "H1")))
p5b <- ggplot(df_fig5b, aes(x = Delta, y = Method)) +
  geom_vline(xintercept = 0, linetype = "dashed", color = "grey50") +
  geom_point(size = 2.5) +
  geom_errorbar(aes(xmin = Lower, xmax = Upper), width = 0.2) +
  labs(x = "Change in Jaccard (30s - 15s)") +
  theme_pub() + theme(axis.text.y = element_blank(), axis.title.y = element_blank())

# Panel C: merge Mean & H1
df_fig5c <- read.csv("results/figure_source_data/fig5_calibration_duration_c.csv")
df_fig5c$Method <- factor(df_fig5c$Method, levels = c("Conjunction", "RMS", "Mean & H1"))
p5c <- ggplot(df_fig5c, aes(x = Duration, y = Acceptance, color = Method)) +
  geom_line(linewidth = 1) +
  geom_point(size = 2) +
  scale_color_manual(values = c("Mean & H1"="#1b9e77", "RMS"="#7570b3", "Conjunction"="#d95f02")) +
  ylim(0, 1) +
  labs(x = "Calibration Duration (s)", y = "Acceptance Rate") +
  theme_pub()

fig5 <- (p5a | p5b) / p5c + plot_annotation(tag_levels = 'A')
save_plot("fig5_calibration_duration", fig5, width = 7, height = 6)
