figure_script_dir <- getOption("CGS_FIGURE_SCRIPT_DIR")
if (is.null(figure_script_dir) || !nzchar(figure_script_dir)) {
  stop("Figure scripts must be executed through render_all_figures.R")
}
common_path <- file.path(figure_script_dir, "common.R")
if (!file.exists(common_path)) {
  stop("Missing common.R: ", common_path)
}
source(common_path, local = TRUE)
library(ggplot2)
d<-read.csv(file.path(FD,"fS1_scorecard.csv"))
d$status<-factor(d$status,levels=c("verified","strong","pass","limited","fail"))
d$evidence<-factor(d$evidence,levels=rev(d$evidence))
pal<-c(verified=CB[3],strong=CB[1],pass=CB[6],limited=CB[5],fail=CB[2])
p<-ggplot(d,aes(x=1,y=evidence,fill=status))+geom_tile(color="white")+geom_text(aes(label=status),size=3)+
  scale_fill_manual(values=pal)+labs(x=NULL,y=NULL,
    caption="Study-defined verification scorecard; criteria frozen in frozen_remedy_success_criteria.md and frozen_degradation_success_criteria.md")+
  theme_nf()+theme(axis.text.x=element_blank(),axis.ticks.x=element_blank(),legend.position="none",
                   plot.caption=element_text(size=7,hjust=0))
save_fig(p,"figureS1_evidence_scorecard",7,3.4)
