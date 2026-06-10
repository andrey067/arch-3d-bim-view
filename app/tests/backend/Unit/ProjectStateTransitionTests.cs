using Arch3DAr.Backend.Domain;
using Xunit;

namespace Arch3DAr.Backend.Tests.Unit;

public class ProjectStateTransitionTests
{
    private static readonly Guid OwnerId = Guid.Parse("11111111-1111-1111-1111-111111111111");
    private static readonly DateTimeOffset Now = DateTimeOffset.UtcNow;

    [Fact]
    public void Rejects_Illegal_Transition_UploadReceived_To_Published()
    {
        var p = Project.Create(OwnerId, "n", null, null, "k", 1, Now);
        Assert.Throws<InvalidStateTransitionException>(() => p.TransitionTo(ProjectStatus.Published, Now));
    }

    [Fact]
    public void Walks_Happy_Path_To_Published()
    {
        var p = Project.Create(OwnerId, "n", null, null, "k", 1, Now);
        p.StartConversion(Now);
        p.CompleteConversion("g", "t", 100, Now);
        p.Publish(Now);
        Assert.Equal(ProjectStatus.Published, p.Status);
    }

    [Fact]
    public void Allows_Processing_To_Failed()
    {
        var p = Project.Create(OwnerId, "n", null, null, "k", 1, Now);
        p.StartConversion(Now);
        p.FailConversion("bad", Now);
        Assert.Equal(ProjectStatus.Failed, p.Status);
        Assert.Equal("bad", p.ErrorMessage);
    }
}
