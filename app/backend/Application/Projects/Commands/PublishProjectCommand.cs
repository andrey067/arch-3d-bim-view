using MediatR;
using Arch3DAr.Backend.Application.Projects.Dtos;

namespace Arch3DAr.Backend.Application.Projects.Commands;

public sealed record PublishProjectCommand(Guid ProjectId) : IRequest<PublishResultDto>;
