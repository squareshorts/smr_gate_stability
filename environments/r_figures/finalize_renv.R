renv::settings$snapshot.type("explicit")

renv::snapshot(
  type = "explicit",
  packages = c(
    "renv",
    "ggplot2",
    "patchwork"
  ),
  prompt = FALSE,
  force = TRUE
)

renv::status()
