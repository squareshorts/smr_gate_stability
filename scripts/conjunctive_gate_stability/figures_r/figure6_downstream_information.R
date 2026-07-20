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
a<-read.csv(file.path(FD,"f6a_natural.csv")); b<-read.csv(file.path(FD,"f6b_countmatched.csv"))
pA<-ggplot(a,aes(natural_minus_nogate,method))+geom_vline(xintercept=0,linetype=2, color="grey70", linewidth=0.5)+
  geom_pointrange(aes(xmin=natural_ci_low,xmax=natural_ci_high), size=1.0, linewidth=1.0)+
  labs(x="Balanced-accuracy difference vs no gate",y=NULL)+theme_nf() +
  theme(axis.text.y = element_text(color="black"))
pB<-ggplot(b,aes(countmatched_minus_R0,method))+geom_vline(xintercept=0,linetype=2, color="grey70", linewidth=0.5)+
  geom_pointrange(aes(xmin=countmatched_ci_low,xmax=countmatched_ci_high), size=1.0, linewidth=1.0)+
  labs(x="Count-matched difference vs R0",y=NULL)+theme_nf() +
  theme(axis.text.y = element_text(color="black"))
if(has_patchwork){
  library(patchwork)
  p<-(pA|pB)+plot_annotation(tag_levels="A")
  save_fig(p,"figure6_downstream_information",11,4.5)
}else{
  save_fig(pA,"figure6_downstream_information_A",5.5,4.5)
  save_fig(pB,"figure6_downstream_information_B",5.5,4.5)
}
