using Arch3DAr.Backend.Application.Abstractions;
using Arch3DAr.Backend.Application.Projects.Commands;
using Arch3DAr.Backend.Application.Projects.Dtos;
using Arch3DAr.Backend.Infrastructure;
using MediatR;
using Microsoft.EntityFrameworkCore;

namespace Arch3DAr.Backend.Application.Projects.Queries;

public class GetProjectHandler : IRequestHandler<GetProjectQuery, ProjectDto>
{
    private readonly AppDbContext _db;
    private readonly ICurrentUser _current;
    private readonly MinioService _minio;
    private readonly MinioSettings _minioSettings;

    public GetProjectHandler(
        AppDbContext db,
        ICurrentUser current,
        MinioService minio,
        MinioSettings minioSettings)
    {
        _db = db;
        _current = current;
        _minio = minio;
        _minioSettings = minioSettings;
    }

    public async Task<ProjectDto> Handle(GetProjectQuery req, CancellationToken ct)
    {
        var project = await _db.Projects
            .AsNoTracking()
            .FirstOrDefaultAsync(p => p.Id == req.Id, ct);
        if (project is null || project.OwnerId != _current.Id)
        {
            throw new NotFoundException("Project not found.");
        }

        var thumbnailUrl = project.ThumbnailObjectKey is null
            ? null
            : await _minio.GetPresignedUrlAsync(_minioSettings.BucketThumbnails, project.ThumbnailObjectKey, ct);

        return new ProjectDto(
            project.Id,
            project.Name,
            project.Description,
            project.ClientLabel,
            project.Status.ToString(),
            thumbnailUrl,
            project.IfcSizeBytes,
            project.ErrorMessage,
            project.CreatedAt,
            project.UpdatedAt,
            project.PublishedAt);
    }
}
