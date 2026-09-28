#' 08_make_figures.R
#'
#' Presentation layer for the Donaldson TTC paper.
#' Python remains responsible for download, cleaning, statistical analysis,
#' simulation, and tests. This script uses the saved Python analysis dataset
#' and summaries to create the paper's figures with ggplot2.

suppressPackageStartupMessages({
  library(arrow)
  library(ggplot2)
})

# Robust project-root discovery when the script is run with Rscript.
args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
if (length(file_arg) > 0) {
  script_path <- sub("^--file=", "", file_arg[1])
  project_root <- normalizePath(file.path(dirname(script_path), ".."))
} else {
  project_root <- normalizePath(".")
}

analysis_path <- file.path(project_root, "data", "analysis_data", "ttc_delay_analysis.parquet")
tables_path <- file.path(project_root, "outputs", "tables")
figures_path <- file.path(project_root, "outputs", "figures")
dir.create(figures_path, recursive = TRUE, showWarnings = FALSE)

hourly <- read.csv(file.path(tables_path, "hourly_summary.csv"), check.names = FALSE)
monthly <- read.csv(file.path(tables_path, "monthly_summary.csv"), check.names = FALSE)
comparison <- read.csv(file.path(tables_path, "hourly_2024_vs_since_2025.csv"), check.names = FALSE)
data <- read_parquet(analysis_path)

# Consistent restrained presentation style.
ink <- "#333333"
mid_gray <- "#777777"
light_gray <- "#D9D9D9"
point_gray <- "#8A8A8A"

base_theme <- theme_minimal(base_size = 11) +
  theme(
    text = element_text(colour = ink),
    axis.title = element_text(colour = ink),
    axis.text = element_text(colour = ink),
    panel.grid.minor = element_blank(),
    panel.grid.major.x = element_blank(),
    panel.grid.major.y = element_line(colour = light_gray, linewidth = 0.35),
    legend.position = "top",
    legend.title = element_blank(),
    plot.margin = margin(8, 10, 8, 8)
  )

save_plot <- function(plot, filename, width = 9, height = 5) {
  ggsave(
    filename = file.path(figures_path, filename),
    plot = plot,
    width = width,
    height = height,
    units = "in",
    dpi = 300,
    bg = "white"
  )
}

# Figure 1: all observations represented by delay ranges.
breaks <- c(-0.5, 0.5, 5.5, 15.5, 30.5, 60.5, 120.5, 300.5, 600.5, 900.5, Inf)
labels <- c("0", "1–5", "6–15", "16–30", "31–60", "61–120",
            "121–300", "301–600", "601–900", "901+")

bins <- cut(data$`Min Delay`, breaks = breaks, labels = labels, include.lowest = TRUE, right = TRUE)
distribution <- as.data.frame(table(bins), stringsAsFactors = FALSE)
names(distribution) <- c("Delay", "Observations")
distribution$Delay <- factor(distribution$Delay, levels = labels)

p1 <- ggplot(distribution, aes(x = Delay, y = Observations)) +
  geom_col(fill = mid_gray, width = 0.8) +
  labs(x = "Recorded delay (minutes)", y = "Number of recorded observations") +
  scale_y_continuous(labels = scales::comma) +
  base_theme
save_plot(p1, "delay_distribution.png", 7, 4.5)

# Figure 2: hourly prevalence with Wilson intervals from the Python analysis.
hourly$HourLabel <- sprintf("%02d:00", hourly$Hour)

p2 <- ggplot(hourly, aes(x = Hour, y = positive_delay_percent)) +
  geom_ribbon(aes(ymin = rate_ci_low_percent, ymax = rate_ci_high_percent),
              fill = light_gray, alpha = 0.8) +
  geom_line(colour = ink, linewidth = 0.7) +
  geom_point(colour = ink, size = 1.7) +
  scale_x_continuous(breaks = 0:23, labels = sprintf("%02d", 0:23)) +
  labs(x = "Hour of day", y = "Recorded observations with positive delay (%)") +
  base_theme
save_plot(p2, "positive_delay_rate_by_hour.png", 7, 4.5)

# Figure 3: conditional median positive delay.
p3 <- ggplot(hourly, aes(x = Hour, y = median_positive_delay)) +
  geom_line(colour = ink, linewidth = 0.7) +
  geom_point(colour = ink, size = 1.7) +
  scale_x_continuous(breaks = 0:23, labels = sprintf("%02d", 0:23)) +
  labs(x = "Hour of day", y = "Median recorded delay among positive records (minutes)") +
  base_theme
save_plot(p3, "median_positive_delay_by_hour.png", 7, 4.5)

# Figure 4: every positive-delay observation, with the hourly median overlaid.
positive <- data[data$`Positive Delay` == TRUE, c("Hour", "Min Delay")]
set.seed(2026)
positive$jitter <- positive$Hour + runif(nrow(positive), -0.18, 0.18)

p4 <- ggplot(positive, aes(x = jitter, y = `Min Delay`)) +
  geom_point(colour = point_gray, alpha = 0.14, size = 0.65) +
  geom_line(data = hourly, aes(x = Hour, y = median_positive_delay),
            colour = ink, linewidth = 0.7) +
  geom_point(data = hourly, aes(x = Hour, y = median_positive_delay),
             colour = ink, size = 1.2) +
  scale_x_continuous(breaks = 0:23, labels = sprintf("%02d", 0:23)) +
  scale_y_continuous(trans = scales::pseudo_log_trans(base = 10)) +
  labs(x = "Hour of day", y = "Recorded positive delay (minutes; symmetric log-like scale)") +
  base_theme
save_plot(p4, "positive_delay_observations_by_hour.png", 7, 4.5)

# Figure 5: monthly supporting pattern.
monthly$Month <- as.Date(paste0(monthly$Month, "-01"))

p5 <- ggplot(monthly, aes(x = Month, y = positive_delay_percent)) +
  geom_line(colour = ink, linewidth = 0.7) +
  geom_point(colour = ink, size = 1.6) +
  scale_x_date(date_breaks = "2 months", date_labels = "%b %Y") +
  labs(x = "Month", y = "Recorded observations with positive delay (%)") +
  base_theme +
  theme(axis.text.x = element_text(angle = 60, hjust = 1))
save_plot(p5, "positive_delay_rate_by_month.png", 7, 4.5)

# Figure 6: 2024 historical benchmark.
p6 <- ggplot(comparison, aes(x = Hour)) +
  geom_line(aes(y = rate_2024, colour = "2024"), linewidth = 0.7) +
  geom_point(aes(y = rate_2024, colour = "2024"), size = 1.6) +
  geom_line(aes(y = rate_since_2025, colour = "Since 2025"), linewidth = 0.8) +
  geom_point(aes(y = rate_since_2025, colour = "Since 2025"), size = 1.6) +
  scale_colour_manual(values = c("2024" = mid_gray, "Since 2025" = ink)) +
  scale_x_continuous(breaks = 0:23, labels = sprintf("%02d", 0:23)) +
  labs(x = "Hour of day", y = "Recorded observations with positive delay (%)") +
  base_theme
save_plot(p6, "hourly_2024_vs_since_2025.png", 7, 4.5)

message("Saved ggplot2 figures to: ", figures_path)
