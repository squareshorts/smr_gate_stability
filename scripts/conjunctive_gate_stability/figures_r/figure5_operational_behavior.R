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
  p <- ggplot(g,aes(method,value,color=calibration,shape=calibration,linetype=calibration))+
    stat_summary(fun=median,geom="point",size=3,position=position_dodge(0.5))+
    stat_summary(fun.data=function(x)data.frame(y=median(x, na.rm=TRUE),ymin=quantile(x,.25, na.rm=TRUE),ymax=quantile(x,.75, na.rm=TRUE)),
                 geom="errorbar",width=0.4, linewidth=1.0, position=position_dodge(0.5))+
    scale_color_manual(values=CB)+
    labs(x="Method",y=ylab,color="Calibration",shape="Calibration",linetype="Calibration")+
    theme_nf()
  
  if (length(unique(g$calibration)) == 1) {
    p <- p + annotate("text", x = 2, y = max(g$value, na.rm=TRUE), label="local p75 only", size=3, color="grey40")
  }
  p
}
pA<-mk("acceptance_proportion","Acceptance proportion")
pB<-mk("accepted_windows_per_min","Accepted windows/min")
pC<-mk("longest_no_acceptance_s","Longest rejection interval (s)")
pD<-mk("transitions_per_min","Transitions/min")
if(has_patchwork){
  library(patchwork)
  p<-(pA|pB)/(pC|pD)+plot_annotation(tag_levels="A")+plot_layout(guides="collect") & theme(legend.position="bottom")
  save_fig(p,"figure5_operational_behavior",10,8)
}else{
  save_fig(pA,"figure5_operational_behavior_A")
  save_fig(pB,"figure5_operational_behavior_B")
  save_fig(pC,"figure5_operational_behavior_C")
  save_fig(pD,"figure5_operational_behavior_D")
}
