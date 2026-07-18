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
a<-read.csv(file.path(FD,"f3a_cardinality.csv"))
long<-rbind(data.frame(cardinality=a$cardinality,value=a$median_observed_jaccard,series="Observed Jaccard"),
            data.frame(cardinality=a$cardinality,value=a$median_predicted_jaccard,series="Predicted Jaccard"),
            data.frame(cardinality=a$cardinality,value=a$median_overall_agreement,series="Overall agreement"))
pA<-ggplot()+geom_ribbon(data=a,aes(cardinality,ymin=obs_ci_low,ymax=obs_ci_high),fill="grey70",alpha=0.5)+
  geom_line(data=long,aes(cardinality,value,color=series,linetype=series))+
  geom_point(data=long,aes(cardinality,value,color=series,shape=series))+
  scale_color_manual(values=CB)+ylim(0,1)+
  labs(x="Gate cardinality K",y="Value (grey band = participant-grouped 95% CI, observed)",
       color=NULL,linetype=NULL,shape=NULL)+theme_nf()
pts<-read.csv(file.path(FD,"f3b_lattice_points.csv")); s<-read.csv(file.path(FD,"f3b_lattice_summary.csv"))
ord<-s$Q[order(s$median_delta)]; pts$Q<-factor(pts$Q,levels=ord); s$Q<-factor(s$Q,levels=ord)
pB<-ggplot(pts,aes(Q,delta_observed))+geom_hline(yintercept=0,linetype=2)+
  geom_jitter(width=0.12,height=0,size=0.5,alpha=0.3,color=CB[7])+
  geom_pointrange(data=s,aes(Q,median_delta,ymin=ci_low,ymax=ci_high),color=CB[1])+coord_flip()+
  labs(x="Added criterion",y="Change in accepted-set Jaccard on addition")+theme_nf()
if(has_patchwork){library(patchwork);p<-(pA|pB)+plot_annotation(tag_levels="A");save_fig(p,"figure3_cardinality_lattice",9,4)}else{
  save_fig(pA,"figure3_cardinality_lattice_A");save_fig(pB,"figure3_cardinality_lattice_B")}
