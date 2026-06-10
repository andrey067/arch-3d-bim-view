using MediatR;
using Microsoft.AspNetCore.Http;

namespace Arch3DAr.Backend.Application.Projects.Commands;

public sealed record CreateProjectCommand(
    string Name,
    string? Description,
    string? ClientLabel,
    IFormFile? File) : IRequest<Application.Projects.Dtos.ProjectDto>;
