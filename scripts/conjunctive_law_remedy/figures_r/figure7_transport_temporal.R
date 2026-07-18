source("common.R")
d <- read.csv(file.path(FIG_DATA, "fig7_transport_temporal.csv"))
p <- ggplot(d, aes(reorder(method, -median_transitions_per_min), median_transitions_per_min)) +
  geom_col() + coord_flip() +
  labs(x="Method", y="Median transitions/min (matched availability)") + theme_nf()
save_fig(p, "figure7_transport_temporal")
