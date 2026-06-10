using System.Net.Http.Json;
using Arch3DAr.Backend.Application.Abstractions;

namespace Arch3DAr.Backend.Infrastructure;

public class ConverterSettings
{
    public string Url { get; set; } = "http://converter:8080";
}

public class HttpModelConverter : IModelConverter
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

    public async Task<ConversionResult> ConvertAsync(Guid projectId, CancellationToken ct)
    {
        var resp = await _http.PostAsJsonAsync($"{_settings.Url}/convert",
            new { projectId }, ct);
        if (!resp.IsSuccessStatusCode)
        {
            var body = await resp.Content.ReadAsStringAsync(ct);
            _logger.LogError("Converter returned {Status}: {Body}", resp.StatusCode, body);
            throw new ConversionException($"Converter returned {(int)resp.StatusCode}: {body}");
        }
        var result = await resp.Content.ReadFromJsonAsync<ConverterResponse>(cancellationToken: ct)
            ?? throw new ConversionException("Converter returned an empty response");
        return new ConversionResult(result.glbKey, result.thumbnailKey, result.durationMs);
    }

    private sealed record ConverterResponse(string glbKey, string thumbnailKey, long durationMs);
}

public class ConversionException : Exception
{
    public ConversionException(string message) : base(message) { }
}
