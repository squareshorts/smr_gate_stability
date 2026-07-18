source("common.R")
# Schematic of composition structure; no title.
library(ggplot2)
df <- data.frame(x=c(1,1,3,3,5), y=c(3,1,3,1,2),
  lab=c("G1 (calib 1)","G2 (calib 2)","A1 (new crit)","A2 (new crit)","J_new = Qc/(P1a+P2b-Qc)"))
p <- ggplot(df, aes(x,y)) + geom_label(aes(label=lab), size=3) +
  annotate("segment", x=1.4, xend=4.4, y=3, yend=2.1) +
  annotate("segment", x=1.4, xend=4.4, y=1, yend=1.9) +
  xlim(0,6) + ylim(0,4) + theme_nf() + theme(axis.title=element_blank())
save_fig(p, "figure1_theorem_schematic")
