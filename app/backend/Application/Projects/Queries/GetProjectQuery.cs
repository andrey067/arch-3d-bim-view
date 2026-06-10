using MediatR;
using Arch3DAr.Backend.Application.Projects.Dtos;

namespace Arch3DAr.Backend.Application.Projects.Queries;

public sealed record GetProjectQuery(Guid Id) : IRequest<ProjectDto>;
