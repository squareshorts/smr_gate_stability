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
a<-read.csv(file.path(FD,"f2a_pooled.csv")); b<-read.csv(file.path(FD,"f2b_by_dataset.csv"))
ann<-read.csv(file.path(FD,"f2_annotations.csv")); b$dataset<-factor(b$dataset,levels=DS_ORDER)
pA<-ggplot(a,aes(median_predicted_jaccard,median_observed_jaccard,color=factor(cardinality),shape=factor(cardinality)))+
  geom_abline(slope=1,intercept=0,linetype=2)+geom_point(size=2.5)+scale_color_manual(values=CB)+
  annotate("text",x=0.62,y=0.98,hjust=0,size=4,label=sprintf("Spearman = %.3f",ann$value[ann$stat=="spearman"]))+
  annotate("text",x=0.62,y=0.93,hjust=0,size=4,label=sprintf("median abs error = %.3f",ann$value[ann$stat=="median_abs_error"]))+
  labs(x="Predicted accepted-set Jaccard",y="Observed accepted-set Jaccard",color="K",shape="K")+
  coord_fixed(xlim=c(0.5, 1.05), ylim=c(0.5, 1.05)) +
  theme_nf() + theme(legend.position = c(0.85, 0.25), legend.background = element_rect(fill="transparent"))
pB<-ggplot(b,aes(median_predicted_jaccard,median_observed_jaccard,color=dataset,shape=dataset))+
  geom_abline(slope=1,intercept=0,linetype=2)+geom_point(size=2,alpha=0.7)+scale_color_manual(values=CB)+
  labs(x="Predicted accepted-set Jaccard",y="Observed accepted-set Jaccard",color="Dataset",shape="Dataset")+
  coord_fixed(xlim=c(0.5, 1.05), ylim=c(0.5, 1.05)) +
  theme_nf() + theme(legend.position = c(0.85, 0.25), legend.background = element_rect(fill="transparent"))
if(has_patchwork){
  library(patchwork)
  p<-(pA|pB)+plot_annotation(tag_levels="A")
  save_fig(p,"figure2_composition_validation",10,5)
}else{
  save_fig(pA,"figure2_composition_validation_A")
  save_fig(pB,"figure2_composition_validation_B")
}
