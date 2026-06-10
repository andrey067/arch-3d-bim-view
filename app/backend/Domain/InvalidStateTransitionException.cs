namespace Arch3DAr.Backend.Domain;

public class InvalidStateTransitionException : Exception
{
    public ProjectStatus From { get; }
    public ProjectStatus To { get; }

    public InvalidStateTransitionException(ProjectStatus from, ProjectStatus to)
        : base($"Invalid project state transition from '{from}' to '{to}'.")
    {
        From = from;
        To = to;
    }
}
