source(file.path(dirname(sub("^--file=", "", commandArgs(trailingOnly = FALSE)[grep("--file=", commandArgs(trailingOnly = FALSE))])), "common.R"))
d <- read.csv(file.path(data_dir, "figure6_downstream.csv"))
d$monitor <- factor(d$monitor, monitor_levels, monitor_labels)
d$dataset <- factor(d$dataset, dataset_levels)
d$analysis <- factor(d$analysis, c("natural", "count_matched"), c("Natural retention", "Count matched"))
p <- ggplot(d, aes(monitor, balanced_accuracy_difference_vs_m0, colour = monitor, shape = dataset)) +
  geom_hline(yintercept = 0, linetype = 2, colour = "grey35") +
  geom_point(position = position_jitter(width = 0.12), alpha = 0.45, size = 0.9) +
  stat_summary(aes(group = monitor), fun.data = mean_se, geom = "pointrange", colour = "black", linewidth = 0.45) +
  facet_wrap(~analysis, ncol = 1) + scale_colour_manual(values = palette_cb, guide = "none") +
  scale_shape_manual(values = shapes_cb[1:3], name = NULL) + scale_x_discrete(labels = monitor_labels) +
  labs(x = NULL, y = "Balanced-accuracy difference versus no gate") + theme_study() +
  theme(axis.text.x = element_text(angle = 25, hjust = 1), legend.position = "bottom")
save_figure(p, 6, 8.4, 7.3)
write_validation(6, d)
