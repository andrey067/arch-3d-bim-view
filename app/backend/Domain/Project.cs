namespace Arch3DAr.Backend.Domain;

public class Project
{
    public Guid Id { get; private set; } = Guid.NewGuid();

    public string PublicToken { get; private set; } = string.Empty;

    public string Name { get; private set; } = string.Empty;

    public ProjectStatus Status { get; private set; } = ProjectStatus.Uploading;

    public string? ErrorMessage { get; private set; }

    public string DataDirectory { get; private set; } = string.Empty;

    public long IfcSizeBytes { get; private set; }

    public long? ConversionDurationMs { get; private set; }

    public DateTimeOffset CreatedAt { get; private set; } = DateTimeOffset.UtcNow;

    public DateTimeOffset UpdatedAt { get; private set; } = DateTimeOffset.UtcNow;

    private Project() { }

    public static Project Create(
        Guid id,
        string publicToken,
        string name,
        long ifcSizeBytes,
        DateTimeOffset now)
    {
        return new Project
        {
            Id = id,
            PublicToken = publicToken,
            Name = name.Trim(),
            DataDirectory = $"projects/{id}",
            IfcSizeBytes = ifcSizeBytes,
            Status = ProjectStatus.Uploading,
            CreatedAt = now,
            UpdatedAt = now,
        };
    }

    public void MarkConverting(DateTimeOffset now)
    {
        Status = ProjectStatus.Converting;
        UpdatedAt = now;
    }

    public void MarkReady(long durationMs, DateTimeOffset now)
    {
        ConversionDurationMs = durationMs;
        Status = ProjectStatus.Ready;
        ErrorMessage = null;
        UpdatedAt = now;
    }

    public void MarkFailed(string reason, DateTimeOffset now)
    {
        ErrorMessage = reason.Length > 500 ? reason[..500] : reason;
        Status = ProjectStatus.Failed;
        UpdatedAt = now;
    }
}
