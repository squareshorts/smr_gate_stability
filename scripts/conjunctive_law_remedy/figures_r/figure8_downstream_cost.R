source("common.R")
d <- read.csv(file.path(FIG_DATA, "fig8_downstream_cost.csv"))
p <- ggplot(d, aes(method, natural_minus_nogate)) +
  geom_hline(yintercept=0, linetype=2) +
  geom_pointrange(aes(ymin=natural_ci_low, ymax=natural_ci_high)) + coord_flip() +
  labs(x="Method", y="Natural-retention balanced accuracy vs no gate") + theme_nf()
save_fig(p, "figure8_downstream_cost")
