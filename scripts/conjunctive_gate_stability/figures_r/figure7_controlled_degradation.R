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
  geom_line(linewidth=1.0)+geom_point(size=2.0)+facet_wrap(~family,ncol=4)+scale_color_manual(values=CB)+ylim(0,1)+
  labs(x="Severity level",y="Response rate",color="Method",shape="Method",linetype="Method")+theme_nf() +
  theme(legend.position="bottom")
pc<-read.csv(file.path(FD,"f7b_paired_top.csv")); pc$family<-factor(labmap[pc$family],levels=labmap)
pB<-ggplot(pc,aes(R1_minus_R0,reorder(family,R1_minus_R0)))+
  geom_vline(xintercept=0,linetype=2, color="grey70", linewidth=0.5)+
  geom_pointrange(aes(xmin=ci_low,xmax=ci_high), size=1.0, linewidth=1.0)+
  labs(x="R1 - R0 withholding difference",y="Degradation family")+theme_nf()
ct<-read.csv(file.path(FD,"f7c_controls.csv"))
ct$control_label <- ifelse(grepl("D0", ct$control), "D0 unchanged input:\ndecision reproduced", "D9 missing/invalid input:\nwithheld fail-closed")
ct$control_label <- factor(ct$control_label, levels = c("D9 missing/invalid input:\nwithheld fail-closed", "D0 unchanged input:\ndecision reproduced"))
ct$display_label <- sprintf("PASS\n(%.2f)", ct$value)
pC<-ggplot(ct,aes(method,control_label))+
  geom_tile(fill="darkslategray4", color="white", linewidth=2)+
  geom_text(aes(label=display_label), color="white", fontface="bold", size=4)+
  labs(subtitle="Structural controls", x=NULL, y=NULL, caption="Deterministic validation endpoints; no inferential comparison.")+
  theme_nf()+
  theme(
    axis.line=element_blank(),
    axis.ticks=element_blank(),
    panel.grid=element_blank(),
    panel.border=element_blank(),
    plot.subtitle=element_text(size=11, face="bold", hjust=0.5),
    plot.caption=element_text(size=8, hjust=0.5)
  )
if(has_patchwork){
  library(patchwork)
  p<-pA / (pB | pC) + plot_annotation(tag_levels="A") + plot_layout(heights = c(1.8, 1))
  save_fig(p,"figure7_controlled_degradation",11,8.5)
}else{
  save_fig(pA,"figure7_controlled_degradation_A",11,5)
  save_fig(pB,"figure7_controlled_degradation_B",5.5,3.5)
  save_fig(pC,"figure7_controlled_degradation_C",5.5,3.5)
}
