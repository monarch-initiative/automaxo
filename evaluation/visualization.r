# Load required libraries
library(ggplot2)
library(scales)

# Create the data frame and rename columns
data1 <- data.frame(
  Value_Types = c('Unmatched Annotations', 'Possible MAxO Matches', 
                  'Grounded MAxO Annotations', 'Distinct MAxO Annotations'),
  Counts = c(15376, 4743, 1492, 153)
)

# Reorder the Value_Types based on Counts in descending order
data1$Value_Types <- factor(data1$Value_Types, levels = data1$Value_Types[order(data1$Counts, decreasing = TRUE)])

# Define custom colors with less solid colors (pastel shades)
custom_colors <- c("Unmatched Annotations" = "#a6cee3",  # pastel blue
                   "Possible MAxO Matches" = "#fb9a99",  # pastel pink
                   "Grounded MAxO Annotations" = "#cab2d6",  # pastel purple
                   "Distinct MAxO Annotations" = "#b2df8a")  # pastel green

# Create the plot
plot <- ggplot(data1, aes(x = Counts, y = Value_Types, fill = Value_Types)) +
  geom_bar(stat = 'identity', width = 0.6) +
  scale_fill_manual(values = custom_colors) +
  theme_minimal(base_size = 15) +
  labs(
    title = "Summary of Automaxo Extraction of MAxO Annotations",
    x = "Counts",
    y = "Value Types"
  ) +
  geom_text(aes(label = scales::comma(Counts)), 
            position = position_stack(vjust = 0.5), 
            color = "black", size = 5) +
  theme(
    plot.title = element_text(hjust = 0.5, face = "bold", size = 18),
    axis.title.x = element_text(face = "bold", size = 14),
    axis.title.y = element_text(face = "bold", size = 14),
    axis.text.y = element_text(face = "bold", size = 14),
    legend.position = "none",
    panel.background = element_rect(fill = "#f7f7f7"),
    panel.grid.major.x = element_line(color = "gray", linetype = "dashed"),
    panel.grid.minor.x = element_line(color = "gray", linetype = "dashed")
  )

# Save the plot as a JPG file
ggsave("evaluation/plot_1.jpg", plot = plot, device = "jpeg", width = 12, height = 8, dpi = 300)
