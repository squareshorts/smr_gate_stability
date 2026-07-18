# Sole supported R entry point for final figure rendering.
# It renders exactly the figures listed in:
#   configs/conjunctive_gate_stability/final_figures.csv
#
# Figure scripts are sourced only through this orchestrator. The orchestrator
# injects the repository root and figure-script directory through R options.

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)

if (length(file_arg) != 1L) {
  stop("Could not resolve render_all_figures.R from commandArgs()")
}

this_file <- normalizePath(
  sub("^--file=", "", file_arg),
  winslash = "/",
  mustWork = TRUE
)

script_dir <- dirname(this_file)
figure_script_dir <- normalizePath(
  file.path(script_dir, "figures_r"),
  winslash = "/",
  mustWork = TRUE
)

project_root <- Sys.getenv("CGS_PROJECT_ROOT")

if (!nzchar(project_root)) {
  project_root <- file.path(script_dir, "..", "..")
}

project_root <- normalizePath(
  project_root,
  winslash = "/",
  mustWork = TRUE
)

renv_activate <- file.path(project_root, "renv", "activate.R")
rfiglib <- Sys.getenv("R_FIG_LIB")

if (file.exists(renv_activate)) {
  source(renv_activate)
} else if (nzchar(rfiglib) && dir.exists(rfiglib)) {
  .libPaths(c(rfiglib, .libPaths()))
}

options(
  CGS_PROJECT_ROOT = project_root,
  CGS_FIGURE_SCRIPT_DIR = figure_script_dir,
  CGS_FIGURE_DIR = figure_script_dir
)

manifest_path <- file.path(
  project_root,
  "configs",
  "conjunctive_gate_stability",
  "final_figures.csv"
)

if (!file.exists(manifest_path)) {
  stop("Missing figure manifest: ", manifest_path)
}

manifest <- read.csv(manifest_path, stringsAsFactors = FALSE)

if (!"figure" %in% names(manifest) || nrow(manifest) == 0L) {
  stop("Figure manifest must contain a nonempty 'figure' column: ", manifest_path)
}

if (anyDuplicated(manifest$figure)) {
  stop("Duplicate figure identifiers in manifest: ", manifest_path)
}

if ("order" %in% names(manifest)) {
  manifest <- manifest[order(manifest$order), , drop = FALSE]
}

output_dir <- file.path(
  project_root,
  "results",
  "conjunctive_gate_final",
  "figures"
)

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

render_rows <- vector("list", nrow(manifest))

for (i in seq_len(nrow(manifest))) {
  stem <- manifest$figure[[i]]
  script_path <- file.path(figure_script_dir, paste0(stem, ".R"))
  pdf_path <- file.path(output_dir, paste0(stem, ".pdf"))
  png_path <- file.path(output_dir, paste0(stem, ".png"))

  started <- Sys.time()
  status <- "failed"
  error_message <- ""

  message("Rendering: ", stem)

  tryCatch(
    {
      if (!file.exists(script_path)) {
        stop("Manifest-listed figure script not found: ", script_path)
      }

      figure_environment <- new.env(parent = globalenv())
      source(
        script_path,
        chdir = TRUE,
        local = figure_environment
      )

      if (!file.exists(pdf_path) || file.info(pdf_path)$size <= 0) {
        stop("Missing or zero-byte PDF: ", pdf_path)
      }

      if (!file.exists(png_path) || file.info(png_path)$size <= 0) {
        stop("Missing or zero-byte PNG: ", png_path)
      }

      status <- "success"
    },
    error = function(e) {
      error_message <<- conditionMessage(e)
    }
  )

  completed <- Sys.time()

  render_rows[[i]] <- data.frame(
    order = if ("order" %in% names(manifest)) manifest$order[[i]] else i,
    figure = stem,
    script = script_path,
    started_at = format(started, "%Y-%m-%dT%H:%M:%S%z"),
    completed_at = format(completed, "%Y-%m-%dT%H:%M:%S%z"),
    elapsed_seconds = as.numeric(difftime(completed, started, units = "secs")),
    status = status,
    pdf_path = pdf_path,
    pdf_bytes = if (file.exists(pdf_path)) file.info(pdf_path)$size else 0,
    png_path = png_path,
    png_bytes = if (file.exists(png_path)) file.info(png_path)$size else 0,
    error_message = error_message,
    stringsAsFactors = FALSE
  )

  render_manifest <- do.call(rbind, render_rows[seq_len(i)])
  write.csv(
    render_manifest,
    file.path(output_dir, "render_manifest.csv"),
    row.names = FALSE
  )

  if (!identical(status, "success")) {
    stop("Figure rendering failed for ", stem, ": ", error_message)
  }
}

writeLines(
  capture.output(sessionInfo()),
  file.path(output_dir, "R_sessionInfo.txt")
)

message(
  "Completed: ",
  nrow(manifest),
  " figures rendered to ",
  normalizePath(output_dir, winslash = "/", mustWork = TRUE)
)
