namespace Arch3DAr.Backend.Api.Endpoints;

using Arch3DAr.Backend.Application.Sharing;
using Arch3DAr.Backend.Infrastructure;
using MediatR;
using Microsoft.EntityFrameworkCore;

public static class PublicShareEndpoints
{
    public static IEndpointRouteBuilder MapPublicShareEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapGet("/share/{token:guid}", async (
            Guid token,
            IMediator mediator,
            CancellationToken ct) =>
        {
            var dto = await mediator.Send(new GetPublicShareQuery(token), ct);
            return Results.Ok(dto);
        });

        app.MapGet("/share/{token:guid}/qr", async (
            Guid token,
            Infrastructure.AppDbContext db,
            MinioService minio,
            MinioSettings settings,
            CancellationToken ct) =>
        {
            var link = await db.ShareLinks.AsNoTracking()
                .FirstOrDefaultAsync(s => s.PublicToken == token, ct);
            if (link is null || string.IsNullOrEmpty(link.QrCodeObjectKey))
            {
                return Results.NotFound();
            }
            var bytes = await minio.DownloadAsync(settings.BucketQrcodes, link.QrCodeObjectKey, ct);
            return Results.File(bytes, "image/png");
        }).AllowAnonymous();

        return app;
    }
}
