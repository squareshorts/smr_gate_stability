source(file.path(dirname(sub("^--file=", "", commandArgs(trailingOnly = FALSE)[grep("--file=", commandArgs(trailingOnly = FALSE))])), "common.R"))
d <- read.csv(file.path(data_dir, "figure7_scorecard.csv"), check.names = FALSE)
metrics <- c("median_split_half_accepted_set_jaccard", "cross_session_accepted_set_jaccard", "median_longest_feedback_free_interval_s", "transitions_per_min", "p95_latency_ms")
labels <- c("Split-half Jaccard", "Transport Jaccard", "Longest gap (s)", "Transitions/min", "p95 latency (ms)")
long <- do.call(rbind, lapply(seq_along(metrics), function(i) data.frame(monitor = d$monitor, metric = labels[i], value = d[[metrics[i]]], stringsAsFactors = FALSE)))
long$monitor <- factor(long$monitor, monitor_levels, monitor_labels)
long$metric <- factor(long$metric, labels)
long$scaled <- ave(long$value, long$metric, FUN = function(x) if (diff(range(x)) == 0) rep(0.5, length(x)) else (x - min(x)) / diff(range(x)))
long$display <- ifelse(long$metric %in% c("Split-half Jaccard", "Transport Jaccard"), sprintf("%.3f", long$value), sprintf("%.2f", long$value))
p <- ggplot(long, aes(metric, monitor, fill = scaled)) +
  geom_tile(colour = "white", linewidth = 0.7) + geom_text(aes(label = display), size = 2.7) +
  scale_fill_gradientn(colours = c("#F7FBFF", "#6BAED6", "#08306B"), limits = c(0, 1), guide = "none") +
  labs(x = NULL, y = NULL) + theme_study() +
  theme(panel.grid = element_blank(), axis.text.x = element_text(angle = 25, hjust = 1))
save_figure(p, 7, 8.4, 4.6)
write_validation(7, d)
