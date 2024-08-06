# Load required libraries
library(ggplot2)
library(tidyr)
library(dplyr)
library(scales)

# Create the data frame
data <- data.frame(
  Value_Types = c('Distinct Grounded Annotations', 'Grounded Annotations', 'Unmatched Annotations', 'Possible Annotations Matches'),
  MAXO = c(172, 1767, 17035, 5130),
  HPO = c(649, 3688, 15114, 4885),
  MONDO = c(352, 11866, 6936, 5425)
)

# Gather the data into long format for ggplot2
data_long <- data %>%
  pivot_longer(cols = -Value_Types, names_to = "Source", values_to = "Counts")

# Define custom colors
custom_colors <- c("MAXO" = "skyblue", "HPO" = "lightgreen", "MONDO" = "salmon")

# Create the plot
plot <- ggplot(data_long, aes(x = Value_Types, y = Counts, fill = Source)) +
  geom_bar(stat = 'identity', position = position_dodge(width = 0.5), width = 0.5) +
  scale_fill_manual(values = custom_colors) +
  theme_minimal(base_size = 15) +
  labs(
    title = "Summary of Extracted Values for MAXO, HPO, and MONDO",
    x = "Value Types",
    y = "Counts"
  ) +
  geom_text(aes(label = scales::comma(Counts)), 
            position = position_dodge(width = 0.75), 
            vjust = -0.5, size = 6) +  # Increased text size for bar labels
  theme(
    plot.title = element_text(hjust = 0.5, face = "bold", size = 22),  # Increased title size
    axis.title.x = element_text(face = "bold", size = 18),  # Increased x-axis title size
    axis.title.y = element_text(face = "bold", size = 18),  # Increased y-axis title size
    axis.text.x = element_text(face = "bold", size = 16, angle = 0, hjust = 0.5),  # Increased x-axis text size
    axis.text.y = element_text(face = "bold", size = 16),  # Increased y-axis text size
    legend.title = element_blank(),
    legend.text = element_text(size = 16),  # Increased legend text size
    legend.position = "top",
    panel.background = element_rect(fill = "#f7f7f7"),
    panel.grid.major.x = element_line(color = "gray", linetype = "dashed"),
    panel.grid.minor.x = element_line(color = "gray", linetype = "dashed")
  )

# Save the plot as a JPG file
ggsave("evaluation/plot.jpg", plot = plot, device = "jpeg", width = 20, height = 12, dpi = 300)
