using Arch3DAr.Backend.Application.Abstractions;
using Arch3DAr.Backend.Application.Projects.Dtos;
using Arch3DAr.Backend.Domain;
using Arch3DAr.Backend.Infrastructure;
using FluentValidation;
using MediatR;
using Microsoft.EntityFrameworkCore;

namespace Arch3DAr.Backend.Application.Projects.Commands;

public class CreateProjectHandler : IRequestHandler<CreateProjectCommand, ProjectDto>
{
    private readonly AppDbContext _db;
    private readonly ICurrentUser _current;
    private readonly MinioService _minio;
    private readonly MinioSettings _minioSettings;
    private readonly ILogger<CreateProjectHandler> _logger;

    public CreateProjectHandler(
        AppDbContext db,
        ICurrentUser current,
        MinioService minio,
        MinioSettings minioSettings,
        ILogger<CreateProjectHandler> logger)
    {
        _db = db;
        _current = current;
        _minio = minio;
        _minioSettings = minioSettings;
        _logger = logger;
    }

    public async Task<ProjectDto> Handle(CreateProjectCommand req, CancellationToken ct)
    {
        if (!_current.IsAuthenticated)
        {
            throw new UnauthorizedAccessException("Authentication required.");
        }
        if (req.File is null)
        {
            throw new ValidationException(new[] { new FluentValidation.Results.ValidationFailure("file", "An .ifc file is required.") });
        }

        var projectId = Guid.NewGuid();
        var objectKey = $"projects/{projectId}/source.ifc";

        // Stream upload directly to MinIO (no in-memory buffering of large files).
        await using (var stream = req.File.OpenReadStream())
        {
            await _minio.UploadStreamAsync(
                _minioSettings.BucketIfc,
                objectKey,
                stream,
                "application/octet-stream",
                ct);
        }

        var now = DateTimeOffset.UtcNow;
        var project = Project.Create(
            ownerId: _current.Id,
            name: req.Name.Trim(),
            description: string.IsNullOrWhiteSpace(req.Description) ? null : req.Description.Trim(),
            clientLabel: string.IsNullOrWhiteSpace(req.ClientLabel) ? null : req.ClientLabel.Trim(),
            ifcObjectKey: objectKey,
            ifcSizeBytes: req.File.Length,
            now: now);

        _db.Projects.Add(project);
        await _db.SaveChangesAsync(ct);

        _logger.LogInformation("Project {ProjectId} created by {OwnerId} ({Bytes} bytes)",
            project.Id, project.OwnerId, project.IfcSizeBytes);

        return new ProjectDto(
            project.Id,
            project.Name,
            project.Description,
            project.ClientLabel,
            project.Status.ToString(),
            ThumbnailUrl: null,
            project.IfcSizeBytes,
            project.ErrorMessage,
            project.CreatedAt,
            project.UpdatedAt,
            project.PublishedAt);
    }
}
