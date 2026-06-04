namespace Backend.Models;

public class Project
{
    public Guid Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public string IfcObjectKey { get; set; } = string.Empty;
    public string GlbObjectKey { get; set; } = string.Empty;
    public string ThumbnailObjectKey { get; set; } = string.Empty;
    public ProjectStatus Status { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}
