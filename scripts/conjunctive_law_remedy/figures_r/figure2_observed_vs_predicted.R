source("common.R")
d <- read.csv(file.path(FIG_DATA, "fig2_observed_vs_predicted.csv"))
p <- ggplot(d, aes(median_predicted_jaccard, median_observed_jaccard, color=factor(cardinality))) +
  geom_abline(slope=1, intercept=0, linetype=2) + geom_point(size=2) +
  labs(x="Predicted accepted-set Jaccard", y="Observed accepted-set Jaccard", color="Cardinality") +
  theme_nf()
save_fig(p, "figure2_observed_vs_predicted")
