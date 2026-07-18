source(file.path(dirname(sub("^--file=", "", commandArgs(trailingOnly = FALSE)[grep("--file=", commandArgs(trailingOnly = FALSE))])), "common.R"))
d <- read.csv(file.path(data_dir, "figure5_availability.csv"))
d$monitor <- factor(d$monitor, monitor_levels, monitor_labels)
d$dataset <- factor(d$dataset, dataset_levels)
panel <- function(variable, ylab, label) {
  ggplot(d, aes(monitor, .data[[variable]], colour = monitor, shape = dataset)) +
    geom_point(position = position_jitter(width = 0.12), alpha = 0.35, size = 0.8) +
    stat_summary(aes(group = monitor), fun = median, geom = "point", shape = 95, size = 7, colour = "black") +
    scale_colour_manual(values = palette_cb, guide = "none") + scale_shape_manual(values = shapes_cb[1:3], guide = "none") +
    scale_x_discrete(labels = monitor_labels) + labs(x = NULL, y = ylab, tag = label) + theme_study() +
    theme(axis.text.x = element_text(angle = 32, hjust = 1), plot.tag = element_text(face = "bold"))
}
p <- panel("longest_feedback_free_s", "Longest feedback-free interval (s)", "A") /
  panel("state_transitions_per_min", "State transitions/min", "B") /
  panel("accepted_windows_per_min", "Accepted windows/min", "C") + plot_layout(guides = "collect")
save_figure(p, 5, 8.4, 10.2)
write_validation(5, d)
