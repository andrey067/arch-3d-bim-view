using Arch3DAr.Backend.Domain;
using Arch3DAr.Backend.Infrastructure;
using FluentAssertions;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace Arch3DAr.Backend.Tests.Integration;

public class FileServingTests : IClassFixture<WebAppFactory>
{
    private readonly WebAppFactory _factory;

    public FileServingTests(WebAppFactory factory) => _factory = factory;

    [Fact]
    public async Task Get_Glb_Returns_200_With_Correct_ContentType_And_No_Redirect()
    {
        var projectId = Guid.NewGuid();
        using var scope = _factory.Services.CreateScope();
        var storage = scope.ServiceProvider.GetRequiredService<LocalFileStorage>();
        var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();

        await storage.WriteFileAsync(projectId, LocalFileStorage.GlbFileName, [0x67, 0x6C, 0x54, 0x46], CancellationToken.None);

        var project = Project.Create(projectId, "a".PadRight(32, 'b'), "Test", 4, DateTimeOffset.UtcNow);
        project.MarkReady(10, DateTimeOffset.UtcNow);
        db.Projects.Add(project);
        await db.SaveChangesAsync();

        var client = _factory.CreateClient(new() { AllowAutoRedirect = false });
        var response = await client.GetAsync($"/files/{projectId}/model.glb");

        response.StatusCode.Should().Be(System.Net.HttpStatusCode.OK);
        response.Headers.Location.Should().BeNull();
        response.Content.Headers.ContentType?.MediaType.Should().Be("model/gltf-binary");
    }

    [Fact]
    public async Task Get_Usdz_Returns_200_With_Correct_ContentType()
    {
        var projectId = Guid.NewGuid();
        using var scope = _factory.Services.CreateScope();
        var storage = scope.ServiceProvider.GetRequiredService<LocalFileStorage>();

        await storage.WriteFileAsync(projectId, LocalFileStorage.UsdzFileName, [0x50, 0x4B, 0x03, 0x04], CancellationToken.None);

        var client = _factory.CreateClient();
        var response = await client.GetAsync($"/files/{projectId}/model.usdz");

        response.StatusCode.Should().Be(System.Net.HttpStatusCode.OK);
        response.Content.Headers.ContentType?.MediaType.Should().Be("model/vnd.usdz+zip");
    }

    [Fact]
    public async Task Share_Returns_SameOrigin_File_Urls()
    {
        var projectId = Guid.NewGuid();
        var token = new string('c', 32);
        using var scope = _factory.Services.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        var storage = scope.ServiceProvider.GetRequiredService<LocalFileStorage>();

        await storage.WriteFileAsync(projectId, LocalFileStorage.GlbFileName, [1], CancellationToken.None);
        await storage.WriteFileAsync(projectId, LocalFileStorage.UsdzFileName, [1], CancellationToken.None);
        await storage.WriteFileAsync(projectId, LocalFileStorage.ThumbnailFileName, [1], CancellationToken.None);

        var project = Project.Create(projectId, token, "Chair", 1, DateTimeOffset.UtcNow);
        project.MarkReady(1, DateTimeOffset.UtcNow);
        db.Projects.Add(project);
        await db.SaveChangesAsync();

        var client = _factory.CreateClient();
        var response = await client.GetAsync($"/share/{token}");
        var json = await response.Content.ReadAsStringAsync();

        json.Should().Contain($"https://test.local/files/{projectId}/model.glb");
        json.Should().Contain($"https://test.local/files/{projectId}/model.usdz");
        json.Should().NotContain(":9000");
        json.Should().Contain("/files/");
    }
}
