using Arch3DAr.Backend.Application.Projects.Commands;
using Arch3DAr.Backend.Domain;
using Arch3DAr.Backend.Infrastructure;
using MediatR;
using Microsoft.EntityFrameworkCore;

namespace Arch3DAr.Backend.Application.Sharing;

public class GetPublicShareHandler : IRequestHandler<GetPublicShareQuery, PublicShareDto>
{
    private readonly AppDbContext _db;
    private readonly MinioService _minio;
    private readonly MinioSettings _minioSettings;
    private readonly ILogger<GetPublicShareHandler> _logger;

    public GetPublicShareHandler(
        AppDbContext db,
        MinioService minio,
        MinioSettings minioSettings,
        ILogger<GetPublicShareHandler> logger)
    {
        _db = db;
        _minio = minio;
        _minioSettings = minioSettings;
        _logger = logger;
    }

    public async Task<PublicShareDto> Handle(GetPublicShareQuery req, CancellationToken ct)
    {
        var shareLink = await _db.ShareLinks
            .AsNoTracking()
            .FirstOrDefaultAsync(s => s.PublicToken == req.PublicToken, ct);
        if (shareLink is null)
        {
            throw new NotFoundException("Share link not found.");
        }

        var project = await _db.Projects
            .AsNoTracking()
            .FirstOrDefaultAsync(p => p.Id == shareLink.ProjectId, ct);
        if (project is null || project.Status != ProjectStatus.Published)
        {
            throw new NotFoundException("Share link not found.");
        }

        if (string.IsNullOrEmpty(project.GlbObjectKey) || string.IsNullOrEmpty(project.ThumbnailObjectKey))
        {
            _logger.LogWarning("Project {ProjectId} is published but missing GLB/thumbnail", project.Id);
            throw new NotFoundException("Share link not found.");
        }

        var glbUrl = await _minio.GetPresignedUrlAsync(
            _minioSettings.BucketGlb, project.GlbObjectKey, ct);
        var thumbUrl = await _minio.GetPresignedUrlAsync(
            _minioSettings.BucketThumbnails, project.ThumbnailObjectKey, ct);

        // FR-025: only the minimum data is exposed. No id, no ownerId, no errorMessage, no timestamps.
        return new PublicShareDto(
            Name: project.Name,
            ClientLabel: project.ClientLabel,
            Status: project.Status.ToString(),
            GlbUrl: glbUrl,
            ThumbnailUrl: thumbUrl);
    }
}
