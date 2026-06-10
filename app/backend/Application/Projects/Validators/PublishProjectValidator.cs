using FluentValidation;

namespace Arch3DAr.Backend.Application.Projects.Commands;

public class PublishProjectValidator : AbstractValidator<PublishProjectCommand>
{
    public PublishProjectValidator()
    {
        RuleFor(x => x.ProjectId)
            .NotEmpty()
            .WithMessage("Project id is required.");
    }
}
