source("common.R")
d <- read.csv(file.path(FIG_DATA, "fig4_lattice_effect.csv"))
p <- ggplot(d, aes(reorder(added_criterion, median_delta), median_delta)) +
  geom_col() + coord_flip() +
  labs(x="Added criterion", y="Median delta Jaccard on addition") + theme_nf()
save_fig(p, "figure4_lattice_effect")
