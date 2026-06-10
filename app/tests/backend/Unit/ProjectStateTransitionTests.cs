using Arch3DAr.Backend.Domain;
using Xunit;

namespace Arch3DAr.Backend.Tests.Unit;

public class ProjectStateTransitionTests
{
    private static readonly DateTimeOffset Now = DateTimeOffset.UtcNow;

    [Fact]
    public void Create_Starts_Uploading()
    {
        var id = Guid.NewGuid();
        var p = Project.Create(id, "abc123", "Sofa", 1024, Now);
        Assert.Equal(ProjectStatus.Uploading, p.Status);
        Assert.Equal($"projects/{id}", p.DataDirectory);
    }

    [Fact]
    public void MarkConverting_Updates_Status()
    {
        var p = Project.Create(Guid.NewGuid(), "abc123", "Sofa", 1024, Now);
        p.MarkConverting(Now);
        Assert.Equal(ProjectStatus.Converting, p.Status);
    }

    [Fact]
    public void MarkReady_Sets_Duration_And_Ready()
    {
        var p = Project.Create(Guid.NewGuid(), "abc123", "Sofa", 1024, Now);
        p.MarkConverting(Now);
        p.MarkReady(4500, Now);
        Assert.Equal(ProjectStatus.Ready, p.Status);
        Assert.Equal(4500, p.ConversionDurationMs);
        Assert.Null(p.ErrorMessage);
    }

    [Fact]
    public void MarkFailed_Sets_Error()
    {
        var p = Project.Create(Guid.NewGuid(), "abc123", "Sofa", 1024, Now);
        p.MarkFailed("USDZ generation failed", Now);
        Assert.Equal(ProjectStatus.Failed, p.Status);
        Assert.Equal("USDZ generation failed", p.ErrorMessage);
    }
}
