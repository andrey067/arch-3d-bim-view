using Arch3DAr.Backend.Application.Projects.Commands;
using Xunit;

namespace Arch3DAr.Backend.Tests.Unit;

public class NotFoundExceptionTests
{
    [Fact]
    public void Exception_Carries_Message()
    {
        var ex = new NotFoundException("missing");
        Assert.Equal("missing", ex.Message);
    }
}
