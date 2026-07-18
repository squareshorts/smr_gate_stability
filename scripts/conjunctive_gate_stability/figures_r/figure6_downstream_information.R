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
pA<-ggplot(a,aes(natural_minus_nogate,method))+geom_vline(xintercept=0,linetype=2)+
  geom_pointrange(aes(xmin=natural_ci_low,xmax=natural_ci_high))+
  labs(x="Natural-retention balanced accuracy vs no gate",y="Method")+theme_nf()
pB<-ggplot(b,aes(countmatched_minus_R0,method))+geom_vline(xintercept=0,linetype=2)+
  geom_pointrange(aes(xmin=countmatched_ci_low,xmax=countmatched_ci_high))+
  labs(x="Count-matched balanced accuracy vs R0",y="Method")+theme_nf()
if(has_patchwork){library(patchwork);p<-(pA|pB)+plot_annotation(tag_levels="A");save_fig(p,"figure6_downstream_information",9,3.2)}else{
  save_fig(pA,"figure6_downstream_information_A",4.5,3.2);save_fig(pB,"figure6_downstream_information_B",4.5,3.2)}
