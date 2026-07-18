source("common.R")
d <- read.csv(file.path(FIG_DATA, "fig3_jaccard_by_cardinality.csv"))
p <- ggplot(d, aes(cardinality, median_observed_jaccard)) +
  geom_ribbon(aes(ymin=obs_ci_low, ymax=obs_ci_high), alpha=0.2) +
  geom_line() + geom_point() +
  geom_line(aes(y=median_predicted_jaccard), linetype=2) +
  labs(x="Gate cardinality (K)", y="Median accepted-set Jaccard") + theme_nf()
save_fig(p, "figure3_jaccard_by_cardinality")
