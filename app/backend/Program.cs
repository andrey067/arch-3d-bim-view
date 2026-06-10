using System.Text.Json;
using System.Text.Json.Serialization;
using Arch3DAr.Backend.Api.Endpoints;
using Arch3DAr.Backend.Application.Abstractions;
using Arch3DAr.Backend.Domain;
using Arch3DAr.Backend.Infrastructure;
using FluentValidation;
using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Minio;
using Serilog;
using Serilog.Formatting.Compact;

var builder = WebApplication.CreateBuilder(args);

// --- Serilog ---
Log.Logger = new LoggerConfiguration()
    .MinimumLevel.Information()
    .Enrich.FromLogContext()
    .Enrich.WithProperty("Application", "Arch3DAR.Backend")
    .WriteTo.Console(new CompactJsonFormatter())
    .CreateLogger();

builder.Host.UseSerilog();

// --- Configuration: read env directly so docker-compose env vars work uniformly ---
var minioSettings = new MinioSettings
{
    Endpoint = builder.Configuration["MinIO:Endpoint"] ?? "minio:9000",
    PublicEndpoint = builder.Configuration["MinIO:PublicEndpoint"] ?? "localhost:9000",
    AccessKey = builder.Configuration["MinIO:AccessKey"] ?? "minioadmin",
    SecretKey = builder.Configuration["MinIO:SecretKey"] ?? "minioadmin123",
    UseSsl = bool.TryParse(builder.Configuration["MinIO:UseSSL"], out var ssl) && ssl,
    BucketIfc = builder.Configuration["MinIO:BucketIfc"] ?? "ifc-files",
    BucketGlb = builder.Configuration["MinIO:BucketGlb"] ?? "glb-files",
    BucketThumbnails = builder.Configuration["MinIO:BucketThumbnails"] ?? "thumbnails",
    BucketQrcodes = builder.Configuration["MinIO:BucketQrcodes"] ?? "qrcodes",
    PresignTtlSeconds = int.TryParse(builder.Configuration["MinIO:PresignTtlSeconds"], out var ttl) ? ttl : 600,
};
var converterSettings = new ConverterSettings
{
    Url = builder.Configuration["Converter:Url"] ?? "http://converter:8080",
};
var publicBaseUrl = builder.Configuration["PublicBaseUrl"] ?? "http://localhost:3000";
var maxIfcMb = int.TryParse(builder.Configuration["MaxIfcMb"], out var mb) ? mb : 100;
var maxIfcBytes = (long)maxIfcMb * 1024L * 1024L;
var allowedOrigins = (builder.Configuration["Cors:AllowedOrigins"] ?? "http://localhost:3000")
    .Split(';', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);

// --- Services ---
builder.Services.AddSingleton(minioSettings);
builder.Services.AddSingleton(converterSettings);
builder.Services.AddSingleton<IMinioClient>(_ => MinioService.BuildClient(minioSettings));
builder.Services.AddScoped<MinioService>();
builder.Services.AddSingleton<QrCodeService>();
builder.Services.AddSingleton<ICurrentUser, CurrentUser>();
builder.Services.AddHttpContextAccessor();
builder.Services.AddSingleton<IModelConverter, HttpModelConverter>();
builder.Services.AddHttpClient<IModelConverter, HttpModelConverter>();

builder.Services.AddDbContext<AppDbContext>(opts =>
    opts.UseNpgsql(builder.Configuration.GetConnectionString("DefaultConnection"))
       .ConfigureWarnings(w => w.Ignore(Microsoft.EntityFrameworkCore.Diagnostics.RelationalEventId.PendingModelChangesWarning)));

builder.Services.AddMediatR(cfg => cfg.RegisterServicesFromAssembly(typeof(Program).Assembly));
builder.Services.AddValidatorsFromAssembly(typeof(Program).Assembly);

builder.Services.AddCors(o => o.AddDefaultPolicy(p =>
    p.WithOrigins(allowedOrigins)
     .AllowAnyHeader()
     .AllowAnyMethod()
     .AllowCredentials()));

builder.Services.Configure<FormOptions>(o =>
{
    o.MultipartBodyLengthLimit = maxIfcBytes + 1_048_576; // headroom
});

builder.Services.AddProblemDetails();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

builder.Services.ConfigureHttpJsonOptions(o =>
{
    o.SerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.CamelCase;
    o.SerializerOptions.Converters.Add(new JsonStringEnumConverter());
});

builder.WebHost.ConfigureKestrel(o =>
{
    o.Limits.MaxRequestBodySize = maxIfcBytes + 1_048_576;
});

var app = builder.Build();

// --- Pipeline ---
app.UseMiddleware<CorrelationIdMiddleware>();
app.UseSerilogRequestLogging();
app.UseCors();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

// Centralized exception → ProblemDetails handler (no stack-trace leak)
app.UseExceptionHandler(eb => eb.Run(async ctx =>
{
    var ex = ctx.Features.Get<IExceptionHandlerFeature>()?.Error;
    var logger = ctx.RequestServices.GetRequiredService<ILogger<Program>>();
    var correlationId = ctx.Items[CorrelationIdMiddleware.HeaderName] as string ?? "-";

    ProblemDetails problem;
    int status;
    switch (ex)
    {
        case InvalidStateTransitionException ist:
            status = StatusCodes.Status409Conflict;
            problem = new ProblemDetails
            {
                Type = "https://arch3dar.com/errors/invalid-state-transition",
                Title = "Invalid state transition",
                Status = status,
                Detail = ist.Message,
            };
            break;
        case ValidationException ve:
            status = StatusCodes.Status400BadRequest;
            problem = new ProblemDetails
            {
                Type = "https://arch3dar.com/errors/validation",
                Title = "Validation failed",
                Status = status,
                Detail = "One or more validation errors occurred.",
                Extensions = { ["errors"] = ve.Errors.GroupBy(e => e.PropertyName)
                    .ToDictionary(g => g.Key, g => g.Select(e => e.ErrorMessage).ToArray()) },
            };
            break;
        case ConversionException ce:
            status = StatusCodes.Status502BadGateway;
            problem = new ProblemDetails
            {
                Type = "https://arch3dar.com/errors/conversion-failed",
                Title = "Conversion failed",
                Status = status,
                Detail = ce.Message,
            };
            break;
        case BadHttpRequestException bre:
            status = bre.StatusCode == 413 || bre.StatusCode == 415
                ? bre.StatusCode
                : StatusCodes.Status400BadRequest;
            problem = new ProblemDetails
            {
                Type = $"https://arch3dar.com/errors/{(status == 413 ? "file-too-large" : status == 415 ? "invalid-ifc" : "bad-request")}",
                Title = status == 413 ? "File too large" : status == 415 ? "Invalid IFC" : "Bad request",
                Status = status,
                Detail = bre.Message,
            };
            break;
        default:
            status = StatusCodes.Status500InternalServerError;
            logger.LogError(ex, "Unhandled exception");
            problem = new ProblemDetails
            {
                Type = "https://arch3dar.com/errors/internal",
                Title = "Internal server error",
                Status = status,
                Detail = "An unexpected error occurred. See the correlation id in logs.",
            };
            break;
    }

    problem.Instance = ctx.Request.Path;
    problem.Extensions["correlationId"] = correlationId;
    ctx.Response.StatusCode = status;
    ctx.Response.ContentType = "application/problem+json";
    await ctx.Response.WriteAsJsonAsync(problem);
}));

// --- Database migration + bucket bootstrap ---
using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    await db.Database.MigrateAsync();
    var minio = scope.ServiceProvider.GetRequiredService<MinioService>();
    await minio.EnsureBucketsAsync();
}

// --- Endpoints ---
app.MapGet("/health", () => Results.Ok(new { status = "ok" }));

app.MapGroup("/api")
    .MapProjectsEndpoints()
    .MapPublicShareEndpoints();

app.Run();

public partial class Program { }
