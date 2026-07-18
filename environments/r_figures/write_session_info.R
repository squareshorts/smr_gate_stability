libp <- Sys.getenv("R_FIG_LIB")
if (nzchar(libp)) .libPaths(c(libp, .libPaths()))
writeLines(capture.output(sessionInfo()), commandArgs(trailingOnly = TRUE)[1])
