# Common theme for conjunctive-law-remedy figures. No titles anywhere.
suppressWarnings(suppressMessages({
  library(ggplot2)
}))

FIG_DATA <- file.path(dirname(dirname(dirname(sys.frame(1)$ofile))), "results",
                      "conjunctive_law_remedy", "figure_data")
FIG_OUT  <- file.path(dirname(dirname(dirname(sys.frame(1)$ofile))), "results",
                      "conjunctive_law_remedy", "figures")

theme_nf <- function() {
  theme_bw(base_size = 10) +
    theme(plot.title = element_blank(),
          legend.title = element_text(size = 9),
          panel.grid.minor = element_blank())
}

save_fig <- function(plot, stem) {
  dir.create(FIG_OUT, showWarnings = FALSE, recursive = TRUE)
  ggsave(file.path(FIG_OUT, paste0(stem, ".pdf")), plot, width = 6, height = 4, device = cairo_pdf)
  ggsave(file.path(FIG_OUT, paste0(stem, ".png")), plot, width = 6, height = 4, dpi = 600)
}
