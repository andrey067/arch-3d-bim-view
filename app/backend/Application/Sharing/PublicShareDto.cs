using MediatR;

namespace Arch3DAr.Backend.Application.Sharing;

public sealed record PublicShareDto(
    string Name,
    string? ClientLabel,
    string Status,
    string GlbUrl,
    string ThumbnailUrl);

public sealed record GetPublicShareQuery(Guid PublicToken) : IRequest<PublicShareDto>;
