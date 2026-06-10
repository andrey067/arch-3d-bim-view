namespace Arch3DAr.Backend.Application.Abstractions;

public interface ICurrentUser
{
    Guid Id { get; }
    bool IsAuthenticated { get; }
}

public class CurrentUser : ICurrentUser
{
    public bool IsAuthenticated => true;

    public Guid Id { get; } = Guid.Parse("11111111-1111-1111-1111-111111111111");
}
