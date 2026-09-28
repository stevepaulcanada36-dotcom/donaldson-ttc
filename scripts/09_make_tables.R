#' 09_make_tables.R
#'
#' Final presentation tables for the Donaldson TTC paper.
#' Python handles download, cleaning, statistical analysis,
#' simulation, and tests.
#' This script uses tinytable for the final PDF tables.

suppressPackageStartupMessages({
  library(tinytable)
})

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
if (length(file_arg) > 0) {
  script_path <- sub("^--file=", "", file_arg[1])
  project_root <- normalizePath(file.path(dirname(script_path), ".."))
} else {
  project_root <- normalizePath(".")
}

tables_path <- file.path(project_root, "outputs", "tables")
dir.create(tables_path, recursive = TRUE, showWarnings = FALSE)

# Keep tables beside the text that introduces them instead of allowing LaTeX
# to move them to the top of a later page.
options(tinytable_latex_placement = "H")

format_hour <- function(x) {
  x <- as.character(x)
  hour_text <- sub(":.*$", "", x)
  hour_number <- suppressWarnings(as.integer(hour_text))
  sprintf("%02d:00", hour_number)
}

save_table <- function(data, filename, caption, label,
                       width = NULL, align = NULL, fontsize = NULL) {
  path <- file.path(tables_path, filename)

  # escape=TRUE is important for labels such as "Positive-delay rate (%)";
  # otherwise LaTeX treats % as the start of a comment and hides the value.
  tab <- tt(
    data,
    caption = caption,
    width = width,
    escape = TRUE
  )

  if (!is.null(align)) {
    tab <- style_tt(tab, j = seq_len(ncol(data)), align = align)
  }
  if (!is.null(fontsize)) {
    tab <- style_tt(tab, j = seq_len(ncol(data)), fontsize = fontsize)
  }

  # Put the LaTeX label on the table itself while leaving the caption text
  # escaped safely by tinytable.
  tab <- theme_latex(
    tab,
    placement = "H",
    outer = paste0("label={", label, "}")
  )

  save_tt(tab, path, overwrite = TRUE)
}

# Table 1: primary data profile.
profile <- read.csv(file.path(tables_path, "data_profile.csv"),
                    check.names = FALSE, stringsAsFactors = FALSE)
profile$Value <- as.character(profile$Value)

save_table(
  profile,
  "data_profile.tex",
  "Summary of the primary TTC study dataset.",
  "tbl-data-profile",
  width = c(0.68, 0.27),
  align = "lr"
)

# Table 2: selected data-quality characteristics (appendix/supporting file).
quality <- read.csv(file.path(tables_path, "data_quality_summary.csv"),
                    check.names = FALSE, stringsAsFactors = FALSE)
quality$Value <- ifelse(
  quality$Measure == "Observations",
  format(quality$Value, big.mark = ",", scientific = FALSE),
  sprintf("%.2f", as.numeric(quality$Value))
)

save_table(
  quality,
  "data_quality.tex",
  "Selected data-quality characteristics of the primary study dataset.",
  "tbl-quality",
  width = c(0.72, 0.25),
  align = "lr"
)

# Main hourly table.
hourly <- read.csv(file.path(tables_path, "hourly_summary.csv"),
                   check.names = FALSE)
hourly$Hour <- format_hour(hourly$Hour)
hourly_main <- hourly[, c(
  "Hour", "observations", "positive_delays",
  "positive_delay_percent", "median_positive_delay",
  "rate_difference_pp_vs_overall"
)]
names(hourly_main) <- c(
  "Hour", "Observations", "Positive delays",
  "Positive-delay rate (percent)", "Median positive delay (min)",
  "Difference vs overall (percentage points)"
)
hourly_main$Observations <- format(
  hourly_main$Observations,
  big.mark = ",",
  scientific = FALSE
)

hourly_main$`Positive delays` <- format(
  hourly_main$`Positive delays`,
  big.mark = ",",
  scientific = FALSE
)

hourly_main$`Positive-delay rate (percent)` <- sprintf(
  "%.2f",
  hourly_main$`Positive-delay rate (percent)`
)

hourly_main$`Median positive delay (min)` <- sprintf(
  "%.1f",
  hourly_main$`Median positive delay (min)`
)

hourly_main$`Difference vs overall (percentage points)` <- sprintf(
  "%.2f",
  hourly_main$`Difference vs overall (percentage points)`
)

save_table(
  hourly_main,
  "hourly_results.tex",
  "Hourly prevalence and conditional severity of recorded TTC subway delays.",
  "tbl-hourly-results",
  width = c(0.08, 0.13, 0.13, 0.18, 0.22, 0.20),
  align = "lrrrrr",
  fontsize = 0.90
)

# Supporting weekday table.
weekday <- read.csv(file.path(tables_path, "weekday_summary.csv"),
                    check.names = FALSE)
weekday_main <- weekday[
  ,
  c(
    "Day",
    "observations",
    "positive_delay_percent",
    "median_positive_delay"
  )
]

names(weekday_main) <- c(
  "Day",
  "Observations",
  "Positive-delay rate (percent)",
  "Median positive delay (min)"
)

weekday_main$Observations <- format(
  weekday_main$Observations,
  big.mark = ",",
  scientific = FALSE
)

weekday_main$`Positive-delay rate (percent)` <- sprintf(
  "%.2f",
  weekday_main$`Positive-delay rate (percent)`
)

weekday_main$`Median positive delay (min)` <- sprintf(
  "%.1f",
  weekday_main$`Median positive delay (min)`
)

save_table(
  weekday_main,
  "weekday.tex",
  "Positive-delay prevalence and median positive delay by weekday.",
  "tbl-weekday",
  width = c(0.18, 0.18, 0.32, 0.22),
  align = "lrrr"
)

# Historical comparison table.
comparison <- read.csv(file.path(tables_path, "hourly_2024_vs_since_2025.csv"),
                       check.names = FALSE)
comparison_main <- comparison[, c(
  "Hour", "rate_2024", "rate_since_2025",
  "rate_difference_pp_since_2025_minus_2024",
  "median_2024", "median_since_2025"
)]
names(comparison_main) <- c(
  "Hour", "2024 rate (percent)", "Since-2025 rate (percent)",
  "Rate difference (percentage points)",
  "2024 median (min)",
  "Since-2025 median (min)"
)
comparison_main$`2024 rate (percent)` <- sprintf(
  "%.2f",
  comparison_main$`2024 rate (percent)`
)

comparison_main$`Since-2025 rate (percent)` <- sprintf(
  "%.2f",
  comparison_main$`Since-2025 rate (percent)`
)

comparison_main$`Rate difference (percentage points)` <- sprintf(
  "%.2f",
  comparison_main$`Rate difference (percentage points)`
)

comparison_main$`2024 median (min)` <- sprintf(
  "%.1f",
  comparison_main$`2024 median (min)`
)

comparison_main$`Since-2025 median (min)` <- sprintf(
  "%.1f",
  comparison_main$`Since-2025 median (min)`
)

save_table(
  comparison_main,
  "historical.tex",
  paste(
    "Hour-by-hour comparison between the 2024 benchmark and ",
    "the primary study period."
  ),
  "tbl-historical",
  width = c(0.08, 0.14, 0.16, 0.19, 0.18, 0.19),
  align = "lrrrrr",
  fontsize = 0.88
)

# Appendix C: Wilson intervals and prevalence ratios.
uncertainty <- hourly[, c(
  "Hour", "positive_delay_percent",
  "rate_ci_low_percent", "rate_ci_high_percent",
  "prevalence_ratio_vs_overall"
)]
names(uncertainty) <- c(
  "Hour", "Positive-delay rate (percent)", "Wilson low (percent)",
  "Wilson high (percent)", "Prevalence ratio"
)
uncertainty$Hour <- format_hour(uncertainty$Hour)
uncertainty[, -1] <- lapply(uncertainty[, -1], function(x) sprintf("%.2f", x))

save_table(
  uncertainty,
  "hourly_uncertainty.tex",
  "Wilson intervals and prevalence ratios by hour.",
  "tbl-hourly-uncertainty",
  width = c(0.08, 0.24, 0.24, 0.24, 0.20),
  align = "lrrrr",
  fontsize = 0.90
)

# Appendix C: counts and absolute contrasts.
counts <- hourly[, c(
  "Hour", "observations", "positive_delays",
  "median_positive_delay", "rate_difference_pp_vs_overall"
)]
names(counts) <- c(
  "Hour", "Observations", "Positive delays",
  "Median positive delay (min)", "Difference vs overall (percentage points)"
)
counts$Hour <- format_hour(counts$Hour)
counts$Observations <- format(
  counts$Observations,
  big.mark = ",",
  scientific = FALSE
)

counts$`Positive delays` <- format(
  counts$`Positive delays`,
  big.mark = ",",
  scientific = FALSE
)

counts$`Median positive delay (min)` <- sprintf(
  "%.1f",
  counts$`Median positive delay (min)`
)

counts$`Difference vs overall (percentage points)` <- sprintf(
  "%.2f",
  counts$`Difference vs overall (percentage points)`
)

save_table(
  counts,
  "hourly_counts.tex",
  "Counts, conditional median, and absolute hourly contrast.",
  "tbl-hourly-counts",
  width = c(0.08, 0.16, 0.16, 0.24, 0.28),
  align = "lrrrr",
  fontsize = 0.88
)

message("Saved tinytable LaTeX tables to: ", tables_path)
