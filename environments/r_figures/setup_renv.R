if (!requireNamespace("renv", quietly = TRUE)) {
  install.packages(
    "renv",
    repos = "https://cloud.r-project.org"
  )
}

renv::init(bare = TRUE)
renv::install(c("ggplot2", "patchwork"))
renv::snapshot(prompt = FALSE)
