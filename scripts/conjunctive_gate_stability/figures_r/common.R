# Common theme/paths. Windows- and Linux-safe path resolution via commandArgs(--file=).
# Honour a repo-local R library if the render entry point provided one.
.rfiglib <- Sys.getenv("R_FIG_LIB")
if (nzchar(.rfiglib) && dir.exists(.rfiglib)) .libPaths(c(.rfiglib, .libPaths()))
suppressWarnings(suppressMessages(library(ggplot2)))
CB <- c("#0072B2","#D55E00","#009E73","#CC79A7","#E69F00","#56B4E9","#000000")
DS_ORDER <- c("ds004447","ds004444","ds004446")

# Paths are injected by the sole entry point render_all_figures.R via options().
FIGRUN_DIR <- getOption("CGS_FIGURE_SCRIPT_DIR")
REPO <- getOption("CGS_PROJECT_ROOT")
if (is.null(FIGRUN_DIR) || !nzchar(FIGRUN_DIR) || is.null(REPO) || !nzchar(REPO)) {
  stop("common.R must be loaded through render_all_figures.R (CGS_PROJECT_ROOT / CGS_FIGURE_SCRIPT_DIR unset)")
}
FIGRUN_DIR <- normalizePath(FIGRUN_DIR, winslash = "/")
REPO <- normalizePath(REPO, winslash = "/")
FD  <- file.path(REPO, "results", "conjunctive_gate_final", "figure_data")
OUT <- file.path(REPO, "results", "conjunctive_gate_final", "figures")

theme_nf <- function() theme_bw(base_size=10) + theme(plot.title=element_blank(), panel.grid.minor=element_blank())
save_fig <- function(p, stem, w=6, h=4){ dir.create(OUT, showWarnings=FALSE, recursive=TRUE)
  ggsave(file.path(OUT, paste0(stem,".pdf")), p, width=w, height=h, device=cairo_pdf)
  ggsave(file.path(OUT, paste0(stem,".png")), p, width=w, height=h, dpi=600) }
has_patchwork <- requireNamespace("patchwork", quietly=TRUE)
