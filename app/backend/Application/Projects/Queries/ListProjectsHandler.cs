using Arch3DAr.Backend.Application.Abstractions;
using Arch3DAr.Backend.Application.Projects.Dtos;
using Arch3DAr.Backend.Infrastructure;
using MediatR;
using Microsoft.EntityFrameworkCore;

namespace Arch3DAr.Backend.Application.Projects.Queries;

public class ListProjectsHandler : IRequestHandler<ListProjectsQuery, ProjectListResponse>
{
    private readonly AppDbContext _db;
    private readonly ICurrentUser _current;
    private readonly MinioService _minio;
    private readonly MinioSettings _minioSettings;

    public ListProjectsHandler(
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

    public async Task<ProjectListResponse> Handle(ListProjectsQuery req, CancellationToken ct)
    {
        var limit = Math.Clamp(req.Limit, 1, 200);

        var q = _db.Projects
            .AsNoTracking()
            .Where(p => p.OwnerId == _current.Id);

        if (!string.IsNullOrEmpty(req.StatusFilter) &&
            Enum.TryParse<Domain.ProjectStatus>(req.StatusFilter, ignoreCase: true, out var status))
        {
            q = q.Where(p => p.Status == status);
        }

        if (TryDecodeCursor(req.Cursor, out var cursorTs, out var cursorId))
        {
            q = q.Where(p =>
                p.CreatedAt < cursorTs ||
                (p.CreatedAt == cursorTs && p.Id.CompareTo(cursorId) < 0));
        }

        var rows = await q
            .OrderByDescending(p => p.CreatedAt)
            .ThenByDescending(p => p.Id)
            .Take(limit + 1)
            .ToListAsync(ct);

        var hasMore = rows.Count > limit;
        var page = hasMore ? rows.Take(limit).ToList() : rows;

        var items = new List<ProjectSummaryDto>(page.Count);
        foreach (var p in page)
        {
            var thumbnailUrl = p.ThumbnailObjectKey is null
                ? null
                : await _minio.GetPresignedUrlAsync(_minioSettings.BucketThumbnails, p.ThumbnailObjectKey, ct);
            items.Add(new ProjectSummaryDto(
                p.Id, p.Name, p.ClientLabel, p.Status.ToString(), thumbnailUrl, p.CreatedAt));
        }

        var nextCursor = hasMore
            ? EncodeCursor(page[^1].CreatedAt, page[^1].Id)
            : null;

        return new ProjectListResponse(items, nextCursor);
    }

    private static string EncodeCursor(DateTimeOffset ts, Guid id) =>
        Convert.ToBase64String(System.Text.Encoding.UTF8.GetBytes($"{ts:O}|{id:D}"));

    private static bool TryDecodeCursor(string? cursor, out DateTimeOffset ts, out Guid id)
    {
        ts = default;
        id = default;
        if (string.IsNullOrEmpty(cursor)) return false;
        try
        {
            var parts = System.Text.Encoding.UTF8.GetString(Convert.FromBase64String(cursor))
                .Split('|', 2);
            if (parts.Length != 2) return false;
            return DateTimeOffset.TryParse(parts[0], out ts) && Guid.TryParse(parts[1], out id);
        }
        catch
        {
            return false;
        }
    }
}
