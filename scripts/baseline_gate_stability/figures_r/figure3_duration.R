source(file.path(dirname(sub("^--file=", "", commandArgs(trailingOnly = FALSE)[grep("--file=", commandArgs(trailingOnly = FALSE))])), "common.R"))
d <- read.csv(file.path(data_dir, "figure3_duration.csv"))
d$monitor <- factor(d$monitor, monitor_levels, monitor_labels)
d$dataset <- factor(d$dataset, dataset_levels)
p <- ggplot(d, aes(duration_s, accepted_set_jaccard, colour = monitor, shape = monitor)) +
  geom_point(position = position_jitter(width = 1.1, height = 0), alpha = 0.20, size = 0.65) +
  stat_summary(aes(group = monitor), fun = median, geom = "line", linewidth = 0.8) +
  stat_summary(aes(group = monitor), fun = median, geom = "point", size = 1.8) +
  facet_wrap(~dataset, ncol = 1) +
  scale_colour_manual(values = palette_cb) + scale_shape_manual(values = shapes_cb) +
  scale_x_continuous(breaks = c(15, 30, 60, 90, 120)) + coord_cartesian(ylim = c(0, 1)) +
  labs(x = "Rest calibration duration (s)", y = "Accepted-set Jaccard versus full baseline", colour = NULL, shape = NULL) +
  theme_study() + theme(legend.position = "bottom")
save_figure(p, 3, 8.4, 8.0)
write_validation(3, d)
