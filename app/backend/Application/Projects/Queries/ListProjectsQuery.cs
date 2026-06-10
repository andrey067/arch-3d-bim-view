using MediatR;
using Arch3DAr.Backend.Application.Projects.Dtos;

namespace Arch3DAr.Backend.Application.Projects.Queries;

public sealed record ListProjectsQuery(
    string? StatusFilter = null,
    int Limit = 50,
    string? Cursor = null) : IRequest<ProjectListResponse>;
