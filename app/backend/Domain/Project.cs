namespace Arch3DAr.Backend.Domain;

public class Project
{
    public Guid Id { get; private set; } = Guid.NewGuid();

    public string PublicToken { get; private set; } = string.Empty;

    public string Name { get; private set; } = string.Empty;

    public ProjectStatus Status { get; private set; } = ProjectStatus.Uploading;

    public string? ErrorMessage { get; private set; }

    public string IfcObjectKey { get; private set; } = string.Empty;

    public string? GlbObjectKey { get; private set; }

    public string? UsdzObjectKey { get; private set; }

    public string? ThumbnailObjectKey { get; private set; }

    public long IfcSizeBytes { get; private set; }

    public long? ConversionDurationMs { get; private set; }

    public DateTimeOffset CreatedAt { get; private set; } = DateTimeOffset.UtcNow;

    public DateTimeOffset UpdatedAt { get; private set; } = DateTimeOffset.UtcNow;

    private Project() { }

    public static Project Create(
        string publicToken,
        string name,
        string ifcObjectKey,
        long ifcSizeBytes,
        DateTimeOffset now)
    {
        return new Project
        {
            PublicToken = publicToken,
            Name = name.Trim(),
            IfcObjectKey = ifcObjectKey,
            IfcSizeBytes = ifcSizeBytes,
            Status = ProjectStatus.Converting,
            CreatedAt = now,
            UpdatedAt = now,
        };
    }

    public void MarkConverting(DateTimeOffset now)
    {
        Status = ProjectStatus.Converting;
        UpdatedAt = now;
    }

    public void MarkReady(string glbKey, string? usdzKey, string thumbnailKey, long durationMs, DateTimeOffset now)
    {
        GlbObjectKey = glbKey;
        UsdzObjectKey = usdzKey;
        ThumbnailObjectKey = thumbnailKey;
        ConversionDurationMs = durationMs;
        Status = ProjectStatus.Ready;
        UpdatedAt = now;
    }

    public void MarkFailed(string reason, DateTimeOffset now)
    {
        ErrorMessage = reason.Length > 500 ? reason[..500] : reason;
        Status = ProjectStatus.Failed;
        UpdatedAt = now;
    }
}
