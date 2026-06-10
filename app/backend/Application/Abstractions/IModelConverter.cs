namespace Arch3DAr.Backend.Application.Abstractions;

public sealed record ConversionResult(
    string GlbObjectKey,
    string ThumbnailObjectKey,
    long DurationMs);

public interface IModelConverter
{
    Task<ConversionResult> ConvertAsync(Guid projectId, CancellationToken ct);
}
