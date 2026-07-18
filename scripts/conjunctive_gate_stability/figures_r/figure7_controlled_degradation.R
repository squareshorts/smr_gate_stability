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
cur<-read.csv(file.path(FD,"f7a_severity.csv"))
long<-rbind(data.frame(family=cur$family,severity=cur$severity,response=cur$R0_response,method="R0"),
            data.frame(family=cur$family,severity=cur$severity,response=cur$R1_response,method="R1"),
            data.frame(family=cur$family,severity=cur$severity,response=cur$R2_response,method="R2"))
labmap<-c(D1_single_channel_broadband="D1 single-ch broadband",D2_common_mode_broadband="D2 common-mode broadband",
          D3_narrowband_35_45="D3 35-45 Hz",D4_narrowband_20_30="D4 20-30 Hz",D5_transient_impulse="D5 transient",
          D6_clipping="D6 clipping",D7_partial_channel_freeze="D7 partial freeze",D8_full_channel_variance_collapse="D8 full freeze")
long$family<-factor(labmap[long$family],levels=labmap)
pA<-ggplot(long,aes(severity,response,color=method,shape=method,linetype=method))+
  geom_line()+geom_point(size=0.9)+facet_wrap(~family,ncol=4)+scale_color_manual(values=CB)+ylim(0,1)+
  labs(x="Severity level",y="Response rate",color="Method",shape="Method",linetype="Method")+theme_nf()
pc<-read.csv(file.path(FD,"f7b_paired_top.csv")); pc$family<-factor(labmap[pc$family],levels=labmap)
pB<-ggplot(pc,aes(R1_minus_R0,reorder(family,R1_minus_R0)))+geom_vline(xintercept=0,linetype=2)+
  geom_pointrange(aes(xmin=ci_low,xmax=ci_high))+
  labs(x="Top-severity paired R1 - R0 response (95% CI)",y="Degradation family")+theme_nf()
ct<-read.csv(file.path(FD,"f7c_controls.csv"))
pC<-ggplot(ct,aes(method,value,fill=control))+geom_col(position="dodge")+scale_fill_manual(values=CB)+ylim(0,1)+
  labs(x="Method",y="Rate (software/structural controls)",fill=NULL)+theme_nf()+theme(legend.text=element_text(size=7))
if(has_patchwork){library(patchwork);p<-pA/(pB|pC)+plot_annotation(tag_levels="A");save_fig(p,"figure7_controlled_degradation",9,8)}else{
  save_fig(pA,"figure7_controlled_degradation_A",9,4);save_fig(pB,"figure7_controlled_degradation_B");save_fig(pC,"figure7_controlled_degradation_C")}
