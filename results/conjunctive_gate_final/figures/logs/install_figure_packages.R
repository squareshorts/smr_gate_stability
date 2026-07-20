libp <- Sys.getenv("R_FIG_LIB")
dir.create(libp, recursive = TRUE, showWarnings = FALSE)
.libPaths(c(libp, .libPaths()))

packages <- c("ggplot2", "patchwork")

missing <- packages[
  !vapply(packages, requireNamespace, logical(1), quietly = TRUE)
]

if (length(missing) > 0L) {
  install.packages(
    missing,
    repos = "https://cloud.r-project.org",
    lib = libp
  )
}

still_missing <- packages[
  !vapply(packages, requireNamespace, logical(1), quietly = TRUE)
]

if (length(still_missing) > 0L) {
  stop(
    "Missing packages after installation: ",
    paste(still_missing, collapse = ", ")
  )
}

cat("Figure packages ready\n")
cat("ggplot2: ", as.character(packageVersion("ggplot2")), "\n", sep = "")
cat("patchwork: ", as.character(packageVersion("patchwork")), "\n", sep = "")
