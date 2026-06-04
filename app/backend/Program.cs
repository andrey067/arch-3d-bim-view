using Backend.Data;
using Backend.Models;
using Backend.Services;
using Microsoft.EntityFrameworkCore;
using Minio;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container
builder.Services.AddEndpointsApiExplorer();

// Configure EF Core with PostgreSQL
var connectionString = builder.Configuration.GetConnectionString("DefaultConnection")
    ?? throw new InvalidOperationException("Connection string 'DefaultConnection' not found.");
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(connectionString));

// Configure MinIO client
var minioEndpoint = builder.Configuration["MinIO__Endpoint"] ?? "localhost:9000";
var minioAccessKey = builder.Configuration["MinIO__AccessKey"] ?? "minioadmin";
var minioSecretKey = builder.Configuration["MinIO__SecretKey"] ?? "minioadmin";
var minioUseSSL = builder.Configuration.GetValue<bool>("MinIO__UseSSL");

var minioClient = new MinioClient()
    .WithEndpoint(minioEndpoint)
    .WithCredentials(minioAccessKey, minioSecretKey)
    .WithSSL(minioUseSSL);

builder.Services.AddSingleton(minioClient);
builder.Services.AddSingleton<MinioService>();

// Configure CORS
var frontendOrigin = builder.Environment.IsDevelopment()
    ? "http://localhost:3000"
    : "http://localhost";

builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
    {
        policy.WithOrigins(frontendOrigin)
              .AllowAnyHeader()
              .AllowAnyMethod();
    });
});

var app = builder.Build();

// Auto-migrate database on startup
using (var scope = app.Services.CreateScope())
{
    var context = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    var logger = scope.ServiceProvider.GetRequiredService<ILogger<Program>>();
    try
    {
        logger.LogInformation("Applying database migrations...");
        context.Database.Migrate();
        logger.LogInformation("Database migrations applied successfully.");
    }
    catch (Exception ex)
    {
        logger.LogError(ex, "An error occurred while applying database migrations.");
        throw;
    }
}

// Ensure MinIO buckets exist on startup
using (var scope = app.Services.CreateScope())
{
    var minioService = scope.ServiceProvider.GetRequiredService<MinioService>();
    var logger = scope.ServiceProvider.GetRequiredService<ILogger<Program>>();
    try
    {
        logger.LogInformation("Ensuring MinIO buckets exist...");
        await minioService.EnsureBucketsExistAsync();
        logger.LogInformation("MinIO buckets verified.");
    }
    catch (Exception ex)
    {
        logger.LogWarning(ex, "Could not verify MinIO buckets. Service may not be available yet.");
    }
}

app.UseCors();

// Health check endpoint
app.MapGet("/health", () => Results.Ok(new { status = "healthy", timestamp = DateTime.UtcNow }))
   .WithTags("Health");

// Upload endpoint
app.MapPost("/api/projects/upload", async (HttpContext context, AppDbContext dbContext, MinioService minioService, ILogger<Program> logger) =>
{
    var form = await context.Request.ReadFormAsync();
    var file = form.Files.GetFile("file");
    var name = form["name"].ToString();

    // Validate name
    if (string.IsNullOrWhiteSpace(name))
    {
        return Results.BadRequest(new { error = "Name is required" });
    }

    // Validate file
    if (file == null || file.Length == 0)
    {
        return Results.BadRequest(new { error = "File is required" });
    }

    // Check file extension
    var fileName = file.FileName;
    if (!fileName.EndsWith(".ifc", StringComparison.OrdinalIgnoreCase))
    {
        return Results.BadRequest(new { error = "Only IFC files are allowed" });
    }

    // Enforce 500 MB max
    const long maxFileSize = 500 * 1024 * 1024; // 500 MB
    if (file.Length > maxFileSize)
    {
        return Results.BadRequest(new { error = "File size exceeds 500 MB limit" });
    }

    // Validate IFC header (ISO-10303-21 magic bytes)
    using (var memoryStream = new MemoryStream())
    {
        await file.CopyToAsync(memoryStream);
        memoryStream.Position = 0;

        using var reader = new StreamReader(memoryStream, leaveOpen: true);
        var firstLine = await reader.ReadLineAsync();

        if (string.IsNullOrEmpty(firstLine) || !firstLine.StartsWith("ISO-10303-21;"))
        {
            return Results.BadRequest(new { error = "Invalid IFC file: missing ISO-10303-21 header" });
        }

        memoryStream.Position = 0;

        // Create project record
        var projectId = Guid.NewGuid();
        var project = new Project
        {
            Id = projectId,
            Name = name,
            Description = string.Empty,
            IfcObjectKey = $"projects/{projectId}/{fileName}",
            Status = ProjectStatus.Uploaded,
            CreatedAt = DateTime.UtcNow
        };

        dbContext.Projects.Add(project);
        await dbContext.SaveChangesAsync();

        // Upload file to MinIO
        try
        {
            memoryStream.Position = 0;
            await minioService.UploadFileAsync(
                minioService.IfcFilesBucket,
                project.IfcObjectKey,
                memoryStream,
                "application/octet-stream"
            );

            logger.LogInformation("Uploaded IFC file for project {ProjectId}: {FileName}", projectId, fileName);
            return Results.Created($"/api/projects/{projectId}", new { id = projectId, name = project.Name, status = project.Status.ToString() });
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to upload file to MinIO for project {ProjectId}", projectId);
            // Clean up the database record if upload fails
            dbContext.Projects.Remove(project);
            await dbContext.SaveChangesAsync();
            return Results.Problem("Failed to upload file to storage");
        }
    }
})
.WithTags("Projects")
.Produces(201)
.Produces(400)
.Produces(500);

// Get all projects
app.MapGet("/api/projects", async (AppDbContext dbContext, MinioService minioService) =>
{
    var projects = await dbContext.Projects
        .OrderByDescending(p => p.CreatedAt)
        .Select(p => new
        {
            p.Id,
            p.Name,
            p.Description,
            p.Status,
            p.CreatedAt,
            ThumbnailUrl = !string.IsNullOrEmpty(p.ThumbnailObjectKey)
                ? minioService.GetPresignedUrlAsync(minioService.ThumbnailsBucket, p.ThumbnailObjectKey, 3600)
                : null
        })
        .ToListAsync();

    // Resolve thumbnail URLs
    var result = new List<object>();
    foreach (var p in projects)
    {
        string? thumbnailUrl = null;
        if (p.ThumbnailUrl != null)
        {
            try
            {
                thumbnailUrl = await p.ThumbnailUrl;
            }
            catch
            {
                thumbnailUrl = null;
            }
        }

        result.Add(new
        {
            p.Id,
            p.Name,
            p.Description,
            Status = p.Status.ToString(),
            p.CreatedAt,
            ThumbnailUrl = thumbnailUrl
        });
    }

    return Results.Ok(result);
})
.WithTags("Projects")
.Produces(200);

// Get project by ID
app.MapGet("/api/projects/{id:guid}", async (Guid id, AppDbContext dbContext, MinioService minioService) =>
{
    var project = await dbContext.Projects.FindAsync(id);

    if (project == null)
    {
        return Results.NotFound(new { error = "Project not found" });
    }

    // Generate presigned URLs
    string? ifcUrl = null;
    string? glbUrl = null;
    string? thumbnailUrl = null;

    try
    {
        if (!string.IsNullOrEmpty(project.IfcObjectKey))
        {
            ifcUrl = await minioService.GetPresignedUrlAsync(minioService.IfcFilesBucket, project.IfcObjectKey, 3600);
        }
    }
    catch (Exception ex)
    {
        // Log but don't fail - URL generation might fail if file doesn't exist
    }

    try
    {
        if (!string.IsNullOrEmpty(project.GlbObjectKey))
        {
            glbUrl = await minioService.GetPresignedUrlAsync(minioService.GlbFilesBucket, project.GlbObjectKey, 3600);
        }
    }
    catch (Exception ex)
    {
        // Log but don't fail
    }

    try
    {
        if (!string.IsNullOrEmpty(project.ThumbnailObjectKey))
        {
            thumbnailUrl = await minioService.GetPresignedUrlAsync(minioService.ThumbnailsBucket, project.ThumbnailObjectKey, 3600);
        }
    }
    catch (Exception ex)
    {
        // Log but don't fail
    }

    return Results.Ok(new
    {
        project.Id,
        project.Name,
        project.Description,
        Status = project.Status.ToString(),
        project.CreatedAt,
        IfcUrl = ifcUrl,
        GlbUrl = glbUrl,
        ThumbnailUrl = thumbnailUrl
    });
})
.WithTags("Projects")
.Produces(200)
.Produces(404);

// Share endpoint
app.MapGet("/api/share/{id:guid}", async (Guid id, AppDbContext dbContext, MinioService minioService) =>
{
    var project = await dbContext.Projects.FindAsync(id);

    if (project == null)
    {
        return Results.NotFound(new { error = "Project not found" });
    }

    string? glbUrl = null;
    try
    {
        if (!string.IsNullOrEmpty(project.GlbObjectKey))
        {
            glbUrl = await minioService.GetPresignedUrlAsync(minioService.GlbFilesBucket, project.GlbObjectKey, 3600);
        }
    }
    catch (Exception ex)
    {
        // Log but don't fail
    }

    return Results.Ok(new
    {
        project.Id,
        project.Name,
        project.Description,
        Status = project.Status.ToString(),
        GlbUrl = glbUrl,
        Metadata = new
        {
            project.CreatedAt,
            IfcFileExists = !string.IsNullOrEmpty(project.IfcObjectKey),
            GlbFileExists = !string.IsNullOrEmpty(project.GlbObjectKey),
            ThumbnailExists = !string.IsNullOrEmpty(project.ThumbnailObjectKey)
        }
    });
})
.WithTags("Share")
.Produces(200)
.Produces(404);

app.Run();
