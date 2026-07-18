source(file.path(dirname(sub("^--file=", "", commandArgs(trailingOnly = FALSE)[grep("--file=", commandArgs(trailingOnly = FALSE))])), "common.R"))
d <- read.csv(file.path(data_dir, "figure1_conceptual.csv"), check.names = FALSE)
d$label <- gsub("\\\\n", "\n", d$label)
arrows <- data.frame(x = d$x[-nrow(d)] + 0.32, xend = d$x[-1] - 0.32, y = 1, yend = 1)
p <- ggplot(d, aes(x = x, y = 1)) +
  geom_segment(data = arrows, aes(x = x, xend = xend, y = y, yend = yend), inherit.aes = FALSE, arrow = arrow(length = unit(0.12, "in")), linewidth = 0.5, colour = "grey35") +
  geom_point(aes(fill = factor(order)), shape = 21, size = 19, colour = "black", stroke = 0.6) +
  geom_text(aes(label = label), size = 2.8, lineheight = 0.92) +
  scale_fill_manual(values = palette_cb[1:5], guide = "none") +
  coord_cartesian(xlim = c(0.55, 5.45), ylim = c(0.7, 1.3), clip = "off") +
  theme_void(base_size = 9) + theme(plot.margin = margin(12, 12, 12, 12))
save_figure(p, 1, 9, 2.3)
write_validation(1, d)
