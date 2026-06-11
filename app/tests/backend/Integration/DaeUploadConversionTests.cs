using System.IO.Compression;
using System.Net;
using System.Net.Http.Json;
using System.Text;
using Arch3DAr.Backend.Infrastructure;
using FluentAssertions;
using Microsoft.AspNetCore.WebUtilities;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Net.Http.Headers;
using Xunit;

namespace Arch3DAr.Backend.Tests.Integration;

public class DaeUploadConversionTests : IClassFixture<WebAppFactory>
{
    private readonly WebAppFactory _factory;

    public DaeUploadConversionTests(WebAppFactory factory) => _factory = factory;

    [Fact]
    public async Task Upload_Dae_With_Mocked_Converter_Writes_Files_And_Returns_Ready()
    {
        var client = _factory.WithWebHostBuilder(builder =>
        {
            builder.ConfigureServices(services =>
            {
                services.AddHttpClient<HttpModelConverter>()
                    .ConfigurePrimaryHttpMessageHandler(() => new MockMeshConverterHandler(_factory.DataRoot, "dae"));
            });
        }).CreateClient();

        var fixturePath = Path.Combine(AppContext.BaseDirectory, "Integration", "Fixtures", "sample.dae");
        File.Exists(fixturePath).Should().BeTrue();

        await using var stream = File.OpenRead(fixturePath);
        using var content = new MultipartFormDataContent();
        content.Add(new StreamContent(stream), "file", "sample.dae");
        content.Add(new StringContent("DAE Test Model"), "name");

        var response = await client.PostAsync("/upload", content);
        var body = await response.Content.ReadFromJsonAsync<UploadResponse>();

        response.StatusCode.Should().Be(HttpStatusCode.OK);
        body.Should().NotBeNull();
        body!.status.Should().Be("Ready");
        body.sourceFormat.Should().Be("dae");

        using var scope = _factory.Services.CreateScope();
        var storage = scope.ServiceProvider.GetRequiredService<LocalFileStorage>();
        storage.FileExists(body.projectId, LocalFileStorage.DaeFileName).Should().BeTrue();
        storage.FileExists(body.projectId, LocalFileStorage.GlbFileName).Should().BeTrue();
        storage.FileExists(body.projectId, LocalFileStorage.UsdzFileName).Should().BeTrue();
        storage.FileExists(body.projectId, LocalFileStorage.ThumbnailFileName).Should().BeTrue();
    }

    [Fact]
    public async Task Upload_Skp_Returns_415_With_Collada_Export_Hint()
    {
        var client = _factory.CreateClient();
        var fixturePath = EnsureSampleSkpFixture();

        await using var stream = File.OpenRead(fixturePath);
        using var content = new MultipartFormDataContent();
        content.Add(new StreamContent(stream), "file", "sample.skp");
        content.Add(new StringContent("SKP Test Model"), "name");

        var response = await client.PostAsync("/upload", content);
        var body = await response.Content.ReadAsStringAsync();

        response.StatusCode.Should().Be(HttpStatusCode.UnsupportedMediaType);
        body.Should().Contain("Collada");
        body.Should().Contain(".dae");
    }

    private static string EnsureSampleSkpFixture()
    {
        var fixturePath = Path.Combine(AppContext.BaseDirectory, "Integration", "Fixtures", "sample.skp");
        if (File.Exists(fixturePath))
        {
            return fixturePath;
        }

        Directory.CreateDirectory(Path.GetDirectoryName(fixturePath)!);
        using (var zip = ZipFile.Open(fixturePath, ZipArchiveMode.Create))
        {
            zip.CreateEntry("SketchUp/version.txt").Open().Dispose();
        }

        return fixturePath;
    }

    private sealed record UploadResponse(
        string token,
        Guid projectId,
        string sourceFormat,
        string status,
        string shareUrl);

    private sealed class MockMeshConverterHandler : HttpMessageHandler
    {
        private readonly string _dataRoot;
        private readonly string _expectedFormat;

        public MockMeshConverterHandler(string dataRoot, string expectedFormat)
        {
            _dataRoot = dataRoot;
            _expectedFormat = expectedFormat;
        }

        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            var stream = await request.Content!.ReadAsStreamAsync(cancellationToken);
            var contentType = request.Content.Headers.ContentType?.ToString() ?? string.Empty;
            const string boundaryMarker = "boundary=";
            var boundaryIndex = contentType.IndexOf(boundaryMarker, StringComparison.OrdinalIgnoreCase);
            if (boundaryIndex < 0)
            {
                return new HttpResponseMessage(HttpStatusCode.BadRequest);
            }

            var boundary = contentType[(boundaryIndex + boundaryMarker.Length)..].Trim().Trim('"');
            var reader = new MultipartReader(boundary, stream);
            string? projectId = null;
            string? sourceFormat = null;
            for (var section = await reader.ReadNextSectionAsync(cancellationToken);
                 section is not null;
                 section = await reader.ReadNextSectionAsync(cancellationToken))
            {
                if (!ContentDispositionHeaderValue.TryParse(section.ContentDisposition, out var disposition))
                {
                    continue;
                }

                if (disposition.Name == "projectId")
                {
                    using var sr = new StreamReader(section.Body);
                    projectId = await sr.ReadToEndAsync(cancellationToken);
                }
                else if (disposition.Name == "sourceFormat")
                {
                    using var sr = new StreamReader(section.Body);
                    sourceFormat = await sr.ReadToEndAsync(cancellationToken);
                }
            }

            if (string.IsNullOrEmpty(projectId) || sourceFormat != _expectedFormat)
            {
                return new HttpResponseMessage(HttpStatusCode.BadRequest);
            }

            var dir = Path.Combine(_dataRoot, "projects", projectId);
            Directory.CreateDirectory(dir);
            await File.WriteAllBytesAsync(Path.Combine(dir, LocalFileStorage.GlbFileName), [0x67, 0x6C, 0x54, 0x46], cancellationToken);
            await File.WriteAllBytesAsync(Path.Combine(dir, LocalFileStorage.UsdzFileName), [0x50, 0x4B, 0x03, 0x04], cancellationToken);
            await File.WriteAllBytesAsync(Path.Combine(dir, LocalFileStorage.ThumbnailFileName), [0x89, 0x50, 0x4E, 0x47], cancellationToken);

            var json = $$"""
                {"glbPath":"projects/{{projectId}}/model.glb","usdzPath":"projects/{{projectId}}/model.usdz","thumbnailPath":"projects/{{projectId}}/thumbnail.webp","durationMs":99}
                """;

            return new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new StringContent(json, Encoding.UTF8, "application/json"),
            };
        }
    }
}
