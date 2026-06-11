using System.Net.Http.Json;

using Arch3DAr.Backend.Domain;

namespace Arch3DAr.Backend.Infrastructure;

public class ConverterSettings
{
    public string Url { get; set; } = "http://converter:8080";
}

public class HttpModelConverter
{
    private readonly HttpClient _http;
    private readonly ConverterSettings _settings;
    private readonly ILogger<HttpModelConverter> _logger;

    public HttpModelConverter(HttpClient http, ConverterSettings settings, ILogger<HttpModelConverter> logger)
    {
        _http = http;
        _settings = settings;
        _logger = logger;
    }

    public async Task<ConverterResult> ConvertAsync(
        byte[] sourceBytes,
        Guid projectId,
        SourceFormat sourceFormat,
        CancellationToken ct)
    {
        using var content = new MultipartFormDataContent();
        var ext = sourceFormat == SourceFormat.Skp ? "skp" : "ifc";
        var fileContent = new ByteArrayContent(sourceBytes);
        fileContent.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("application/octet-stream");
        content.Add(fileContent, "file", $"{projectId}.{ext}");
        content.Add(new StringContent(projectId.ToString()), "projectId");
        content.Add(new StringContent(ext), "sourceFormat");

        var resp = await _http.PostAsync($"{_settings.Url}/convert", content, ct);
        var body = await resp.Content.ReadAsStringAsync(ct);
        if (!resp.IsSuccessStatusCode)
        {
            _logger.LogError("Converter returned {Status}: {Body}", resp.StatusCode, body);
            throw new ConversionException($"Converter returned {(int)resp.StatusCode}: {body}");
        }

        var result = await resp.Content.ReadFromJsonAsync<ConverterResponse>(cancellationToken: ct)
            ?? throw new ConversionException("Converter returned an empty response");
        return new ConverterResult(result.glbPath, result.usdzPath, result.thumbnailPath, result.durationMs);
    }

    private sealed record ConverterResponse(string glbPath, string usdzPath, string thumbnailPath, long durationMs);
}

public record ConverterResult(string GlbPath, string UsdzPath, string ThumbnailPath, long DurationMs);

public class ConversionException : Exception
{
    public ConversionException(string message) : base(message) { }
}
