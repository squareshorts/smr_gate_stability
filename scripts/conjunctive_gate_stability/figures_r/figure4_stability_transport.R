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
s<-read.csv(file.path(FD,"f4a_stability_sessions.csv")); s$dataset<-factor(s$dataset,levels=DS_ORDER)
pr<-read.csv(file.path(FD,"f4a_stability_proportions.csv"))
prlab<-aggregate(prop_ge_0.80~method+dataset,pr,function(x)x); prlab$dataset<-factor(prlab$dataset,levels=DS_ORDER)
pA<-ggplot(s,aes(method,accepted_set_jaccard))+
  geom_hline(yintercept=0.80,linetype=2,color="grey70", linewidth=0.5)+
  geom_boxplot(outlier.size=0.5,width=0.8,fill=CB[6],alpha=0.3)+
  geom_text(data=prlab,aes(method,0.30,label=sprintf("%.0f%%",100*prop_ge_0.80)),size=3.5)+
  facet_wrap(~dataset,nrow=1)+ylim(0,1)+coord_flip()+
  labs(x=NULL,y="Split-half accepted-set Jaccard (dashed 0.80; % = sessions >=0.80)")+theme_nf() +
  theme(axis.text.y = element_text(color="black"))
tp<-read.csv(file.path(FD,"f4b_transport_points.csv")); ts<-read.csv(file.path(FD,"f4b_transport_summary.csv"))
tp$dataset<-factor(tp$dataset,levels=DS_ORDER); ts$dataset<-factor(ts$dataset,levels=DS_ORDER)
pB<-ggplot(tp,aes(method,accepted_set_jaccard))+
  geom_jitter(width=0.12,height=0,size=0.5,alpha=0.15,color=CB[7])+
  geom_pointrange(data=ts,aes(method,median,ymin=ci_low,ymax=ci_high),color=CB[1], size=1.0, linewidth=1.0)+
  facet_wrap(~dataset,nrow=1)+ylim(0,1)+coord_flip()+
  labs(x="Method",y="Cross-session transport Jaccard (participant-grouped 95% CI)")+theme_nf() +
  theme(axis.text.y = element_text(color="black"))
if(has_patchwork){
  library(patchwork)
  p<-(pA/pB)+plot_annotation(tag_levels="A")
  save_fig(p,"figure4_stability_transport",10,8)
}else{
  save_fig(pA,"figure4_stability_transport_A",10,4)
  save_fig(pB,"figure4_stability_transport_B",10,4)
}
