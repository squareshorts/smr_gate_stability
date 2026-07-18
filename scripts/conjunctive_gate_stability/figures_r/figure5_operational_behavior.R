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
d<-read.csv(file.path(FD,"f5_operational_points.csv"))
mk<-function(metric,ylab){
  g<-d[d$metric==metric,]
  ggplot(g,aes(method,value,color=calibration,shape=calibration))+
    stat_summary(fun=median,geom="point",size=2,position=position_dodge(0.5))+
    stat_summary(fun.data=function(x)data.frame(y=median(x),ymin=quantile(x,.25),ymax=quantile(x,.75)),
                 geom="errorbar",width=0.25,position=position_dodge(0.5))+
    scale_color_manual(values=CB)+labs(x="Method",y=ylab,color="Calibration",shape="Calibration")+theme_nf()}
pA<-mk("acceptance_proportion","Acceptance proportion")
pB<-mk("accepted_windows_per_min","Accepted windows/min")
pC<-mk("longest_no_acceptance_s","Longest no-acceptance interval (s)")
pD<-mk("transitions_per_min","Transitions/min")
if(has_patchwork){library(patchwork);p<-(pA|pB)/(pC|pD)+plot_annotation(tag_levels="A")+plot_layout(guides="collect");save_fig(p,"figure5_operational_behavior",9,7)}else{
  save_fig(pA,"figure5_operational_behavior_A");save_fig(pB,"figure5_operational_behavior_B");save_fig(pC,"figure5_operational_behavior_C");save_fig(pD,"figure5_operational_behavior_D")}
