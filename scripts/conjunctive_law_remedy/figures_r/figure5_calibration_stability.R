source("common.R")
d <- read.csv(file.path(FIG_DATA, "fig5_calibration_stability.csv"))
p <- ggplot(d, aes(reorder(method, pooled_median_splithalf_jaccard), pooled_median_splithalf_jaccard)) +
  geom_col() + coord_flip() + ylim(0,1) +
  labs(x="Method", y="Median split-half accepted-set Jaccard") + theme_nf()
save_fig(p, "figure5_calibration_stability")
