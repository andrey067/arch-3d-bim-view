using FluentValidation;
using Microsoft.AspNetCore.Http;

namespace Arch3DAr.Backend.Application.Projects.Commands;

public class CreateProjectValidator : AbstractValidator<CreateProjectCommand>
{
    public const long DefaultMaxBytes = 100L * 1024L * 1024L;
    private const int IfcSignatureLineMaxLength = 256;

    public CreateProjectValidator()
    {
        RuleFor(x => x.Name)
            .NotEmpty()
            .MaximumLength(200)
            .WithMessage("Project name is required (1-200 characters).");

        RuleFor(x => x.Description)
            .MaximumLength(2000)
            .WithMessage("Description must be 2000 characters or less.");

        RuleFor(x => x.ClientLabel)
            .MaximumLength(200)
            .WithMessage("Client label must be 200 characters or less.");

        RuleFor(x => x.File)
            .NotNull()
            .WithMessage("An .ifc file is required.")
            .Must(BeAValidIfc)
            .WithMessage("Not a valid IFC file. The upload must be an .ifc file exported from a supported CAD tool.")
            .Must(HaveAllowedExtension)
            .WithMessage("Only .ifc files are supported in this version.")
            .Must((cmd, file) => file!.Length <= DefaultMaxBytes)
            .WithMessage($"File too large. Maximum allowed size is {DefaultMaxBytes / 1024 / 1024} MB.");
    }

    private static bool HaveAllowedExtension(IFormFile? file) =>
        file is not null &&
        Path.GetExtension(file.FileName).Equals(".ifc", StringComparison.OrdinalIgnoreCase);

    private static bool BeAValidIfc(IFormFile? file)
    {
        if (file is null) return false;
        if (file.Length < 32) return false;
        try
        {
            using var stream = file.OpenReadStream();
            using var reader = new StreamReader(stream);
            // IFC files start with a header line: "ISO-10303-21;"
            // We only need to read the first line.
            var firstLine = reader.ReadLine();
            return firstLine is not null && firstLine.TrimStart().StartsWith("ISO-10303-21", StringComparison.Ordinal);
        }
        catch
        {
            return false;
        }
    }
}
