namespace Arch3DAr.Backend.Application.Projects.Dtos;

public sealed record ProjectDto(
    Guid Id,
    string Name,
    string? Description,
    string? ClientLabel,
    string Status,
    string? ThumbnailUrl,
    long? IfcSizeBytes,
    string? ErrorMessage,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    DateTimeOffset? PublishedAt);

public sealed record ProjectSummaryDto(
    Guid Id,
    string Name,
    string? ClientLabel,
    string Status,
    string? ThumbnailUrl,
    DateTimeOffset CreatedAt);

public sealed record ProjectListResponse(
    IReadOnlyList<ProjectSummaryDto> Items,
    string? NextCursor);

public sealed record PublishResultDto(
    Guid ProjectId,
    Guid PublicToken,
    string PublicUrl,
    string QrCodeUrl);
