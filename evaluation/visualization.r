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
  theme_minimal(base_size = 20) +  # Increase the base size
  geom_text(aes(label = scales::comma(Counts)), 
            position = position_dodge(width = 0.75), 
            vjust = -0.5, size = 8) +  # Increased text size for bar labels
  theme(
    plot.title = element_blank(),  # Removed title
    axis.title.x = element_blank(),  # Removed x-axis title
    axis.title.y = element_blank(),  # Removed y-axis title
    axis.text.x = element_text(face = "bold", size = 22, angle = 0, hjust = 0.5),  # Increased x-axis text size
    axis.text.y = element_text(face = "bold", size = 25),  # Increased y-axis text size
    legend.title = element_blank(),
    legend.text = element_text(size = 25),  # Increased legend text size
    legend.position = c(0.02, 0.98),  # Moved legend to top left corner
    legend.justification = c(0, 1),  # Adjust legend justification
    panel.background = element_rect(fill = "#f7f7f7"),
    panel.grid.major.x = element_line(color = "gray", linetype = "dashed"),
    panel.grid.minor.x = element_line(color = "gray", linetype = "dashed")
  )

# Save the plot as a JPG file
ggsave("evaluation/plot.jpg", plot = plot, device = "jpeg", width = 20, height = 12, dpi = 300)
