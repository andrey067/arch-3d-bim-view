using Arch3DAr.Backend.Application.Abstractions;
using Arch3DAr.Backend.Application.Projects.Dtos;
using Arch3DAr.Backend.Domain;
using Arch3DAr.Backend.Infrastructure;
using MediatR;
using Microsoft.EntityFrameworkCore;

namespace Arch3DAr.Backend.Application.Projects.Commands;

public class PublishProjectHandler : IRequestHandler<PublishProjectCommand, PublishResultDto>
{
    private readonly AppDbContext _db;
    private readonly ICurrentUser _current;
    private readonly MinioService _minio;
    private readonly MinioSettings _minioSettings;
    private readonly QrCodeService _qr;
    private readonly IConfiguration _config;
    private readonly ILogger<PublishProjectHandler> _logger;

    public PublishProjectHandler(
        AppDbContext db,
        ICurrentUser current,
        MinioService minio,
        MinioSettings minioSettings,
        QrCodeService qr,
        IConfiguration config,
        ILogger<PublishProjectHandler> logger)
    {
        _db = db;
        _current = current;
        _minio = minio;
        _minioSettings = minioSettings;
        _qr = qr;
        _config = config;
        _logger = logger;
    }

    public async Task<PublishResultDto> Handle(PublishProjectCommand req, CancellationToken ct)
    {
        var project = await _db.Projects
            .FirstOrDefaultAsync(p => p.Id == req.ProjectId, ct);
        if (project is null || project.OwnerId != _current.Id)
        {
            throw new NotFoundException("Project not found.");
        }

        // Idempotent: if a ShareLink already exists, return it.
        var existing = await _db.ShareLinks
            .FirstOrDefaultAsync(s => s.ProjectId == project.Id, ct);
        if (existing is not null)
        {
            return BuildResult(project.Id, existing);
        }

        if (project.Status != ProjectStatus.ReadyToPublish)
        {
            throw new InvalidStateTransitionException(project.Status, ProjectStatus.Published);
        }

        var publicToken = Guid.NewGuid();
        var shareLink = ShareLink.Create(project.Id, publicToken, DateTimeOffset.UtcNow);
        var qrKey = $"projects/{project.Id}/qr.png";
        var publicUrl = BuildPublicUrl(publicToken);

        var png = _qr.GeneratePng(publicUrl);
        using (var ms = new MemoryStream(png))
        {
            await _minio.UploadStreamAsync(
                _minioSettings.BucketQrcodes,
                qrKey,
                ms,
                "image/png",
                ct);
        }
        shareLink.AttachQrCode(qrKey);

        project.Publish(DateTimeOffset.UtcNow);
        _db.ShareLinks.Add(shareLink);
        await _db.SaveChangesAsync(ct);

        _logger.LogInformation("Project {ProjectId} published with token {Token}", project.Id, publicToken);
        return BuildResult(project.Id, shareLink);
    }

    private PublishResultDto BuildResult(Guid projectId, ShareLink shareLink)
    {
        var publicUrl = BuildPublicUrl(shareLink.PublicToken);
        // For dev convenience, return a relative URL for QR; the public page can presign on demand.
        var qrCodeUrl = $"/api/share/{shareLink.PublicToken}/qr";
        return new PublishResultDto(projectId, shareLink.PublicToken, publicUrl, qrCodeUrl);
    }

    private string BuildPublicUrl(Guid publicToken)
    {
        var baseUrl = _config["PublicBaseUrl"] ?? "http://localhost:3000";
        return $"{baseUrl.TrimEnd('/')}/s/{publicToken:D}";
    }
}

public class NotFoundException : Exception
{
    public NotFoundException(string message) : base(message) { }
}
