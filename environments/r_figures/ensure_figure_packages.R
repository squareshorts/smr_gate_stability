libp <- Sys.getenv("R_FIG_LIB")
if (!nzchar(libp)) stop("R_FIG_LIB is empty")

dir.create(libp, recursive = TRUE, showWarnings = FALSE)
.libPaths(c(libp, .libPaths()))

project_root <- Sys.getenv("CGS_PROJECT_ROOT")
if (!nzchar(project_root)) stop("CGS_PROJECT_ROOT is empty")

lockfile <- file.path(project_root, "renv.lock")
activate <- file.path(project_root, "renv", "activate.R")

if (file.exists(lockfile)) {
  if (!requireNamespace("renv", quietly = TRUE)) {
    install.packages(
      "renv",
      repos = "https://cloud.r-project.org",
      lib = libp
    )
  }

  renv::restore(project = project_root, prompt = FALSE)

  if (file.exists(activate)) {
    source(activate)
  }
}

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
    "Missing R packages after installation: ",
    paste(still_missing, collapse = ", ")
  )
}

cat("Figure packages ready\n")
cat("renv lock used: ", file.exists(lockfile), "\n", sep = "")
for (pkg in packages) {
  cat(pkg, ": ", as.character(packageVersion(pkg)), "\n", sep = "")
}
cat("Library paths:\n")
cat(paste(.libPaths(), collapse = "\n"), "\n")
