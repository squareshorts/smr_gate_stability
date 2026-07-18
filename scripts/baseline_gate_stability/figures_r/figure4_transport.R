source(file.path(dirname(sub("^--file=", "", commandArgs(trailingOnly = FALSE)[grep("--file=", commandArgs(trailingOnly = FALSE))])), "common.R"))
d <- read.csv(file.path(data_dir, "figure4_transport.csv"))
d$monitor <- factor(d$monitor, monitor_levels, monitor_labels)
d$dataset <- factor(d$dataset, dataset_levels)
p <- ggplot(d, aes(monitor, accepted_set_jaccard, fill = monitor)) +
  geom_violin(scale = "width", trim = TRUE, colour = "grey30", linewidth = 0.35) +
  geom_boxplot(width = 0.18, outlier.shape = NA, fill = "white", linewidth = 0.35) +
  geom_point(aes(shape = monitor), position = position_jitter(width = 0.08, height = 0), alpha = 0.4, size = 0.8) +
  geom_hline(yintercept = 0.75, linetype = 3, colour = "grey45") + facet_wrap(~dataset, ncol = 1) +
  scale_fill_manual(values = palette_cb, guide = "none") + scale_shape_manual(values = shapes_cb, guide = "none") +
  scale_x_discrete(labels = monitor_labels) + coord_cartesian(ylim = c(0, 1)) +
  labs(x = NULL, y = "First-to-final accepted-set Jaccard") + theme_study() +
  theme(axis.text.x = element_text(angle = 25, hjust = 1))
save_figure(p, 4, 8.4, 8.2)
write_validation(4, d)
