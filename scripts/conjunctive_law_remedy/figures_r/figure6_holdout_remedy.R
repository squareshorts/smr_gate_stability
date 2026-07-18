source("common.R")
d <- read.csv(file.path(FIG_DATA, "fig6_holdout_remedy.csv"))
p <- ggplot(d, aes(holdout_dataset, splithalf_jaccard, fill=method)) +
  geom_col(position="dodge") + ylim(0,1) +
  labs(x="Holdout dataset", y="Split-half Jaccard", fill="Method") + theme_nf()
save_fig(p, "figure6_holdout_remedy")
