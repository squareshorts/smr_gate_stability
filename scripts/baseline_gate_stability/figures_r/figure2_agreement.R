source(file.path(dirname(sub("^--file=", "", commandArgs(trailingOnly = FALSE)[grep("--file=", commandArgs(trailingOnly = FALSE))])), "common.R"))
d <- read.csv(file.path(data_dir, "figure2_agreement.csv"))
d$monitor <- factor(d$monitor, monitor_levels, monitor_labels)
d$dataset <- factor(d$dataset, dataset_levels)
p <- ggplot(d, aes(overall_agreement, accepted_set_jaccard, colour = dataset, shape = dataset)) +
  geom_abline(slope = 1, intercept = 0, linetype = 2, colour = "grey45", linewidth = 0.4) +
  geom_vline(xintercept = 0.95, linetype = 3, colour = "grey55") +
  geom_hline(yintercept = 0.80, linetype = 3, colour = "grey55") +
  geom_point(alpha = 0.58, size = 1.25) +
  facet_wrap(~monitor, ncol = 3) +
  scale_colour_manual(values = palette_cb[1:3]) + scale_shape_manual(values = shapes_cb[1:3]) +
  coord_equal(xlim = c(0, 1), ylim = c(0, 1)) +
  labs(x = "Overall decision agreement", y = "Accepted-set Jaccard", colour = NULL, shape = NULL) + theme_study()
save_figure(p, 2, 8.4, 5.7)
write_validation(2, d)
