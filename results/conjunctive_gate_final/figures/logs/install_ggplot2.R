libp <- Sys.getenv("R_FIG_LIB")

dir.create(
  libp,
  recursive = TRUE,
  showWarnings = FALSE
)

.libPaths(c(libp, .libPaths()))

if (!requireNamespace("ggplot2", quietly = TRUE)) {
  install.packages(
    "ggplot2",
    repos = "https://cloud.r-project.org",
    lib = libp
  )
}

if (!requireNamespace("ggplot2", quietly = TRUE)) {
  stop("ggplot2 installation failed")
}

cat("ggplot2 ready\n")
cat("Version: ", as.character(packageVersion("ggplot2")), "\n", sep = "")
cat("Library: ", find.package("ggplot2"), "\n", sep = "")
