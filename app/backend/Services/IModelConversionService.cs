using Arch3DAr.Backend.Domain;
using Arch3DAr.Backend.Infrastructure;

namespace Arch3DAr.Backend.Services;

public interface IModelConversionService
{
    Task<ConverterResult> ConvertAsync(
        byte[] sourceBytes,
        Guid projectId,
        SourceFormat sourceFormat,
        CancellationToken ct);
}

public sealed class HttpModelConverterAdapter(HttpModelConverter inner) : IModelConversionService
{
    public Task<ConverterResult> ConvertAsync(
        byte[] sourceBytes,
        Guid projectId,
        SourceFormat sourceFormat,
        CancellationToken ct) =>
        inner.ConvertAsync(sourceBytes, projectId, sourceFormat, ct);
}
