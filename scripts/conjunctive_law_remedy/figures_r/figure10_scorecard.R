source("common.R")
d <- read.csv(file.path(FIG_DATA, "fig10_scorecard.csv"))
p <- ggplot(d, aes(reorder(method, n_pass), n_pass)) +
  geom_col() + coord_flip() + ylim(0,12) +
  labs(x="Method", y="Frozen criteria passed (of 12)") + theme_nf()
save_fig(p, "figure10_scorecard")
