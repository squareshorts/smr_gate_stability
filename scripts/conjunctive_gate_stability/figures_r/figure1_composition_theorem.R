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
d<-read.csv(file.path(FD,"f1_theorem.csv")); v<-setNames(d$value,d$quantity)
lab<-function(...) sprintf(...)
# Panel A: existing gate G with two replicates + accepted-set overlap (schematic circles)
circ<-function(cx,cy,r,n=100){t<-seq(0,2*pi,length.out=n);data.frame(x=cx+r*cos(t),y=cy+r*sin(t))}
A1<-circ(1.7,2,1.1);A1$set<-"G1";A2<-circ(2.6,2,1.1);A2$set<-"G2"
pA<-ggplot()+geom_polygon(data=A1,aes(x,y),fill=CB[1],alpha=0.35)+
  geom_polygon(data=A2,aes(x,y),fill=CB[2],alpha=0.35)+
  annotate("text",x=1.2,y=2,label="G1",size=3)+annotate("text",x=3.1,y=2,label="G2",size=3)+
  annotate("text",x=2.15,y=2,label="Q",size=3)+
  annotate("text",x=2.15,y=0.4,label=lab("P1=%.2f  P2=%.2f  Q=%.2f",v["P1"],v["P2"],v["Q"]),size=2.8)+
  annotate("text",x=2.15,y=0.0,label=lab("J_old = Q/(P1+P2-Q) = %.2f",v["J_old"]),size=2.9)+
  coord_equal()+xlim(0,4.3)+ylim(-0.3,3.4)+theme_nf()+
  theme(axis.title=element_blank(),axis.text=element_blank(),axis.ticks=element_blank(),panel.grid=element_blank())
B1<-circ(1.7,2,1.1);B2<-circ(2.6,2,1.1)
pB<-ggplot()+geom_polygon(data=B1,aes(x,y),fill=CB[3],alpha=0.35)+
  geom_polygon(data=B2,aes(x,y),fill=CB[5],alpha=0.35)+
  annotate("text",x=1.2,y=2,label="A1",size=3)+annotate("text",x=3.1,y=2,label="A2",size=3)+
  annotate("text",x=2.15,y=2,label="c",size=3)+
  annotate("text",x=2.15,y=0.4,label=lab("a=%.2f  b=%.2f  c=%.2f",v["a"],v["b"],v["c"]),size=2.8)+
  annotate("text",x=2.15,y=0.0,label="new gate: G and A",size=2.9)+
  coord_equal()+xlim(0,4.3)+ylim(-0.3,3.4)+theme_nf()+
  theme(axis.title=element_blank(),axis.text=element_blank(),axis.ticks=element_blank(),panel.grid=element_blank())
pC<-ggplot()+xlim(0,1)+ylim(0,1)+
  annotate("text",x=0.5,y=0.82,label="J_new = Qc/(P1a+P2b-Qc)",size=3.2)+
  annotate("text",x=0.5,y=0.60,label=lab("= %.2f  (<= J_old = %.2f)",v["J_new"],v["J_old"]),size=3)+
  annotate("text",x=0.5,y=0.38,label="J_new <= J_old  iff  c(P1+P2) <= P1a+P2b",size=3)+
  annotate("text",x=0.5,y=0.20,label=lab("(%.2f <= %.2f)",v["c(P1+P2)"],v["P1a+P2b"]),size=2.8)+
  annotate("text",x=0.5,y=0.02,label="symmetric: a=b=p, c<=p  =>  non-increasing",size=2.8)+
  theme_void()
if(has_patchwork){library(patchwork);p<-(pA|pB|pC)+plot_annotation(tag_levels="A");save_fig(p,"figure1_composition_theorem",9,3.4)}else{
  save_fig(pA,"figure1_composition_theorem_A",3,3.4);save_fig(pB,"figure1_composition_theorem_B",3,3.4);save_fig(pC,"figure1_composition_theorem_C",3,3.4)}
