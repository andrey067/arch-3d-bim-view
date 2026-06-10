namespace Arch3DAr.Backend.Domain;

public class Project
{
    public Guid Id { get; private set; } = Guid.NewGuid();
    public Guid OwnerId { get; private set; }
    public string Name { get; private set; } = string.Empty;
    public string? Description { get; private set; }
    public string? ClientLabel { get; private set; }
    public ProjectStatus Status { get; private set; } = ProjectStatus.UploadReceived;
    public string? ErrorMessage { get; private set; }
    public string? IfcObjectKey { get; private set; }
    public string? GlbObjectKey { get; private set; }
    public string? ThumbnailObjectKey { get; private set; }
    public long? IfcSizeBytes { get; private set; }
    public DateTimeOffset? ConversionStartedAt { get; private set; }
    public long? ConversionDurationMs { get; private set; }
    public DateTimeOffset CreatedAt { get; private set; } = DateTimeOffset.UtcNow;
    public DateTimeOffset UpdatedAt { get; private set; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? PublishedAt { get; private set; }

    private Project() { }

    public static Project Create(
        Guid ownerId,
        string name,
        string? description,
        string? clientLabel,
        string ifcObjectKey,
        long ifcSizeBytes,
        DateTimeOffset now)
    {
        var p = new Project
        {
            OwnerId = ownerId,
            Name = name,
            Description = description,
            ClientLabel = clientLabel,
            IfcObjectKey = ifcObjectKey,
            IfcSizeBytes = ifcSizeBytes,
            Status = ProjectStatus.UploadReceived,
            CreatedAt = now,
            UpdatedAt = now,
        };
        return p;
    }

    public void UpdateMetadata(string name, string? description, string? clientLabel, DateTimeOffset now)
    {
        Name = name;
        Description = description;
        ClientLabel = clientLabel;
        UpdatedAt = now;
    }

    public void StartConversion(DateTimeOffset now)
    {
        TransitionTo(ProjectStatus.Processing, now);
        ConversionStartedAt = now;
        ErrorMessage = null;
    }

    public void CompleteConversion(string glbKey, string thumbnailKey, long durationMs, DateTimeOffset now)
    {
        GlbObjectKey = glbKey;
        ThumbnailObjectKey = thumbnailKey;
        ConversionDurationMs = durationMs;
        TransitionTo(ProjectStatus.ReadyToPublish, now);
    }

    public void FailConversion(string reason, DateTimeOffset now)
    {
        ErrorMessage = reason;
        TransitionTo(ProjectStatus.Failed, now);
    }

    public void Publish(DateTimeOffset now)
    {
        TransitionTo(ProjectStatus.Published, now);
        PublishedAt = now;
    }

    public void TransitionTo(ProjectStatus next, DateTimeOffset now)
    {
        if (!IsValidTransition(Status, next))
        {
            throw new InvalidStateTransitionException(Status, next);
        }
        Status = next;
        UpdatedAt = now;
    }

    public static bool IsValidTransition(ProjectStatus from, ProjectStatus to) =>
        (from, to) switch
        {
            (ProjectStatus.UploadReceived, ProjectStatus.Processing) => true,
            (ProjectStatus.Processing, ProjectStatus.ReadyToPublish) => true,
            (ProjectStatus.Processing, ProjectStatus.Failed) => true,
            (ProjectStatus.ReadyToPublish, ProjectStatus.Published) => true,
            (ProjectStatus.Failed, ProjectStatus.Processing) => true,
            _ => false,
        };
}
