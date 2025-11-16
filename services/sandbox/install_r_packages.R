#!/usr/bin/env Rscript
# R packages installation script
# This script installs all necessary R packages for data analysis

# Set CRAN mirror
options(repos = list(CRAN = "https://cloud.r-project.org"))

# Function to install packages with error handling
install_package <- function(pkg_name) {
  tryCatch({
    if (!require(pkg_name, character.only = TRUE)) {
      install.packages(pkg_name, quiet = TRUE)
      cat(sprintf("✓ Installed %s\n", pkg_name))
    } else {
      cat(sprintf("✓ %s already installed\n", pkg_name))
    }
  }, error = function(e) {
    cat(sprintf("✗ Failed to install %s: %s\n", pkg_name, e$message))
  })
}

# List of packages to install
packages <- c(
  # Environment and dependency management
  "renv",

  # Core tidyverse meta-package
  # Note: tidyverse includes dplyr, ggplot2, tibble, tidyr, readr, purrr, stringr, forcats, lubridate
  "tidyverse",

  # Additional data manipulation (not in tidyverse)
  "glue",
  "here",
  "zoo",

  # Database access
  "DBI",
  "RPostgres",

  # Visualization (not in tidyverse)
  "reshape",
  "reshape2",
  "gridExtra",
  "plotly",
  "ggrepel",
  "ggeasy",
  "ggtext",

  # Language and functional programming
  "rlang",

  # Spatial data
  "sp",
  "sf",
  "units",
  "leaflet",

  # Web applications
  "shiny",
  "shinyWidgets",
  "shinydashboard"
)

# Install all packages
cat("Installing R packages...\n")
cat("========================\n\n")

for (pkg in packages) {
  install_package(pkg)
}

cat("\n========================\n")
cat("R packages installation complete!\n")
