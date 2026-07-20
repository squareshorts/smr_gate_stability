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
A1<-circ(1.7,2,1.3);A1$set<-"G1";A2<-circ(2.6,2,1.3);A2$set<-"G2"
pA<-ggplot()+geom_polygon(data=A1,aes(x,y),fill=CB[1],alpha=0.35)+
  geom_polygon(data=A2,aes(x,y),fill=CB[2],alpha=0.35)+
  annotate("text",x=1.0,y=2,label="P[1]",parse=TRUE,size=5)+
  annotate("text",x=3.3,y=2,label="P[2]",parse=TRUE,size=5)+
  annotate("text",x=2.15,y=2,label="Q",parse=TRUE,size=5)+
  annotate("text",x=2.15,y=0.4,label=lab("P[1]==%.2f~~P[2]==%.2f~~Q==%.2f",v["P1"],v["P2"],v["Q"]),parse=TRUE,size=3.5)+
  annotate("text",x=2.15,y=0.0,label=lab("J==%.2f",v["J_old"]),parse=TRUE,size=3.5)+
  coord_equal()+xlim(0,4.3)+ylim(-0.3,3.4)+theme_nf()+
  theme(axis.title=element_blank(),axis.text=element_blank(),axis.ticks=element_blank(),panel.grid=element_blank(), plot.margin=margin(0,0,0,0), panel.border=element_blank())
B1<-circ(1.7,2,1.3);B2<-circ(2.6,2,1.3)
pB<-ggplot()+geom_polygon(data=B1,aes(x,y),fill=CB[3],alpha=0.35)+
  geom_polygon(data=B2,aes(x,y),fill=CB[5],alpha=0.35)+
  annotate("text",x=1.0,y=2,label="a",parse=TRUE,size=5)+
  annotate("text",x=3.3,y=2,label="b",parse=TRUE,size=5)+
  annotate("text",x=2.15,y=2,label="c",parse=TRUE,size=5)+
  annotate("text",x=2.15,y=0.4,label=lab("a==%.2f~~b==%.2f~~c==%.2f",v["a"],v["b"],v["c"]),parse=TRUE,size=3.5)+
  annotate("text",x=2.15,y=0.0,label="Conjunctive~gate~G*\"'\"",parse=TRUE,size=3.5)+
  coord_equal()+xlim(0,4.3)+ylim(-0.3,3.4)+theme_nf()+
  theme(axis.title=element_blank(),axis.text=element_blank(),axis.ticks=element_blank(),panel.grid=element_blank(), plot.margin=margin(0,0,0,0), panel.border=element_blank())
pC<-ggplot()+xlim(0,5.6)+ylim(-0.3,3.4)+coord_equal()+
  annotate("text",x=2.8,y=2.5,label="J*\"'\" == frac(Q %.% c, P[1]*a + P[2]*b - Q %.% c)",parse=TRUE,size=5)+
  annotate("text",x=2.8,y=1.5,label=lab("J*\"'\" == \"%.2f  (<= J = %.2f)\"",v["J_new"],v["J_old"]),parse=TRUE,size=5)+
  annotate("text",x=2.8,y=0.7,label="J*\"'\" <= J ~ \"iff\" ~ c*(P[1]+P[2]) <= P[1]*a + P[2]*b",parse=TRUE,size=4.5)+
  annotate("text",x=2.8,y=0.0,label="\"Symmetric: a=b=p, c<=p  =>  \" ~ J*\"'\" <= J",parse=TRUE,size=4)+
  theme_void() + theme(plot.margin=margin(0,0,0,0))
if(has_patchwork){
  library(patchwork)
  p<-(pA|pB|pC)+plot_annotation(tag_levels="A")+plot_layout(widths = c(2.2, 2.2, 5.6))
  save_fig(p,"figure1_composition_theorem",9,3.4)
}else{
  save_fig(pA,"figure1_composition_theorem_A",3,3.4)
  save_fig(pB,"figure1_composition_theorem_B",3,3.4)
  save_fig(pC,"figure1_composition_theorem_C",3,3.4)
}
