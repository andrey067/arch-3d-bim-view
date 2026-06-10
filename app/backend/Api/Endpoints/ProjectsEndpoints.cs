namespace Arch3DAr.Backend.Api.Endpoints;

using Arch3DAr.Backend.Application.Projects.Commands;
using Arch3DAr.Backend.Application.Projects.Queries;
using FluentValidation;
using MediatR;
using Microsoft.AspNetCore.Http.HttpResults;
using Microsoft.AspNetCore.Mvc;

public static class ProjectsEndpoints
{
    public static IEndpointRouteBuilder MapProjectsEndpoints(this IEndpointRouteBuilder app)
    {
        var group = app.MapGroup("/projects");

        group.MapPost("/", async (
            HttpContext http,
            IMediator mediator,
            IValidator<CreateProjectCommand> validator,
            CancellationToken ct) =>
        {
            var form = await http.Request.ReadFormAsync(ct);
            var name = form["name"].ToString();
            var description = form["description"].ToString();
            var clientLabel = form["clientLabel"].ToString();
            var file = form.Files["file"];

            var cmd = new CreateProjectCommand(name, description, clientLabel, file);
            var result = await validator.ValidateAsync(cmd, ct);
            if (!result.IsValid)
            {
                throw new ValidationException(result.Errors);
            }
            var dto = await mediator.Send(cmd, ct);
            return Results.Created($"/api/projects/{dto.Id}", dto);
        }).DisableAntiforgery();

        group.MapGet("/", async (IMediator mediator, CancellationToken ct) =>
        {
            var list = await mediator.Send(new ListProjectsQuery(), ct);
            return Results.Ok(list);
        });

        group.MapGet("/{id:guid}", async (Guid id, IMediator mediator, CancellationToken ct) =>
        {
            var dto = await mediator.Send(new GetProjectQuery(id), ct);
            return Results.Ok(dto);
        });

        group.MapPost("/{id:guid}/publish", async (Guid id, IMediator mediator, CancellationToken ct) =>
        {
            var result = await mediator.Send(new PublishProjectCommand(id), ct);
            return Results.Ok(result);
        });

        return app;
    }
}
