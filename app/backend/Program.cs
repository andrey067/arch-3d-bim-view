using System.Text;
using Arch3DAr.Backend.Domain;
using Arch3DAr.Backend.Infrastructure;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.EntityFrameworkCore;
using Serilog;
using Serilog.Formatting.Compact;

var builder = WebApplication.CreateBuilder(args);

Log.Logger = new LoggerConfiguration()
    .MinimumLevel.Information()
    .Enrich.FromLogContext()
    .Enrich.WithProperty("Application", "Arch3DAR.Backend")
    .WriteTo.Console(new CompactJsonFormatter())
    .CreateLogger();
builder.Host.UseSerilog();

var storageSettings = new LocalFileStorageSettings
{
    DataRoot = builder.Configuration["DATA_ROOT"] ?? "/data",
};

var converterSettings = new ConverterSettings
{
    Url = builder.Configuration["Converter:Url"] ?? "http://converter:8080",
};

var publicBaseUrl = (builder.Configuration["PublicBaseUrl"] ?? "https://localhost").TrimEnd('/');
var maxIfcMb = int.TryParse(builder.Configuration["MaxIfcMb"], out var mb) ? mb : 100;
var maxIfcBytes = (long)maxIfcMb * 1024L * 1024L;
var allowedOrigins = (builder.Configuration["Cors:AllowedOrigins"] ?? "https://localhost")
    .Split(';', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);

builder.Services.AddSingleton(storageSettings);
builder.Services.AddSingleton(converterSettings);
builder.Services.AddSingleton<LocalFileStorage>();
builder.Services.AddSingleton<QrCodeService>();
builder.Services.AddHttpContextAccessor();
builder.Services.AddHttpClient<HttpModelConverter>();

if (builder.Environment.IsEnvironment("Testing"))
{
    builder.Services.AddDbContext<AppDbContext>(opts =>
        opts.UseInMemoryDatabase("arch3dar-tests"));
}
else
{
    builder.Services.AddDbContext<AppDbContext>(opts =>
        opts.UseNpgsql(builder.Configuration.GetConnectionString("DefaultConnection"))
           .ConfigureWarnings(w => w.Ignore(Microsoft.EntityFrameworkCore.Diagnostics.RelationalEventId.PendingModelChangesWarning)));
}

builder.Services.AddCors(o => o.AddDefaultPolicy(p =>
    p.WithOrigins(allowedOrigins)
     .AllowAnyHeader()
     .AllowAnyMethod()));

builder.Services.Configure<FormOptions>(o =>
{
    o.MultipartBodyLengthLimit = maxIfcBytes + 1_048_576;
});

builder.Services.ConfigureHttpJsonOptions(o =>
{
    o.SerializerOptions.PropertyNamingPolicy = System.Text.Json.JsonNamingPolicy.CamelCase;
    o.SerializerOptions.Converters.Add(new System.Text.Json.Serialization.JsonStringEnumConverter());
});

builder.WebHost.ConfigureKestrel(o =>
{
    o.Limits.MaxRequestBodySize = maxIfcBytes + 1_048_576;
});

var app = builder.Build();

app.UseMiddleware<CorrelationIdMiddleware>();
app.UseMiddleware<ModelContentTypeMiddleware>();
app.UseSerilogRequestLogging();
app.UseCors();

app.UseExceptionHandler(eb => eb.Run(async ctx =>
{
    var ex = ctx.Features.Get<Microsoft.AspNetCore.Diagnostics.IExceptionHandlerFeature>()?.Error;
    var logger = ctx.RequestServices.GetRequiredService<ILogger<Program>>();
    var correlationId = ctx.Items[CorrelationIdMiddleware.HeaderName] as string ?? "-";

    var status = ex is ConversionException ? StatusCodes.Status502BadGateway
               : ex is BadHttpRequestException bre ? bre.StatusCode
               : StatusCodes.Status500InternalServerError;
    var title = status == 413 ? "File too large"
              : status == 415 ? "Invalid IFC"
              : status == 502 ? "Conversion failed"
              : "Internal server error";

    if (status >= 500) logger.LogError(ex, "Unhandled exception");
    else logger.LogInformation("Request rejected: {Status} {Title} ({Message})", status, title, ex?.Message);

    ctx.Response.StatusCode = status;
    ctx.Response.ContentType = "application/problem+json";
    await ctx.Response.WriteAsJsonAsync(new
    {
        type = $"https://arch3dar.com/errors/{title.ToLowerInvariant().Replace(' ', '-')}",
        title,
        status,
        detail = ex?.Message ?? "Unexpected error",
        correlationId,
    });
}));

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    await DatabaseMigrator.ApplyAsync(db);
}

string NewToken()
{
    Span<byte> bytes = stackalloc byte[16];
    System.Security.Cryptography.RandomNumberGenerator.Fill(bytes);
    return Convert.ToHexString(bytes).ToLowerInvariant();
}

string FileUrl(Guid projectId, string fileName) =>
    $"{publicBaseUrl}/files/{projectId}/{fileName}";

IResult ServeProjectFile(Guid projectId, string fileName, LocalFileStorage storage)
{
    var path = storage.ResolvePath(projectId, fileName);
    if (!storage.IsInsideDataRoot(path) || !File.Exists(path))
    {
        return Results.NotFound();
    }

    var contentType = fileName switch
    {
        LocalFileStorage.GlbFileName => "model/gltf-binary",
        LocalFileStorage.UsdzFileName => "model/vnd.usdz+zip",
        LocalFileStorage.ThumbnailFileName => "image/png",
        _ => "application/octet-stream",
    };

    return Results.File(path, contentType, enableRangeProcessing: fileName == LocalFileStorage.GlbFileName);
}

// GET /health
app.MapGet("/health", () => Results.Ok(new { status = "ok" }));

// POST /upload
app.MapPost("/upload", async (
    HttpContext http,
    AppDbContext db,
    LocalFileStorage storage,
    HttpModelConverter converter,
    QrCodeService qr,
    ILogger<Program> logger,
    CancellationToken ct) =>
{
    if (!http.Request.HasFormContentType)
    {
        return Results.Problem(statusCode: 415, title: "Invalid IFC", detail: "Expected multipart/form-data.");
    }

    var form = await http.Request.ReadFormAsync(ct);
    var file = form.Files.GetFile("file");
    if (file is null || file.Length == 0)
    {
        return Results.Problem(statusCode: 400, title: "Bad request", detail: "Field 'file' is required.");
    }
    if (file.Length > maxIfcBytes)
    {
        return Results.Problem(statusCode: 413, title: "File too large",
            detail: $"Maximum allowed size is {maxIfcMb} MB.");
    }
    if (!".ifc".Equals(Path.GetExtension(file.FileName), StringComparison.OrdinalIgnoreCase))
    {
        return Results.Problem(statusCode: 415, title: "Invalid IFC", detail: "Only .ifc files are accepted.");
    }

    byte[] head;
    await using (var s = file.OpenReadStream())
    {
        var buf = new byte[64];
        var read = await s.ReadAsync(buf.AsMemory(0, 64), ct);
        head = buf[..read];
    }
    var headText = Encoding.ASCII.GetString(head).TrimStart();
    if (!headText.StartsWith("ISO-10303-21", StringComparison.Ordinal))
    {
        return Results.Problem(statusCode: 415, title: "Invalid IFC", detail: "File does not look like an IFC document.");
    }

    var name = (form["name"].ToString() ?? Path.GetFileNameWithoutExtension(file.FileName)).Trim();
    if (string.IsNullOrWhiteSpace(name)) name = "Untitled";

    var projectId = Guid.NewGuid();
    var publicToken = NewToken();
    var now = DateTimeOffset.UtcNow;

    byte[] ifcBytes;
    await using (var s = file.OpenReadStream())
    using (var ms = new MemoryStream())
    {
        await s.CopyToAsync(ms, ct);
        ifcBytes = ms.ToArray();
    }

    storage.EnsureProjectDir(projectId);
    await storage.WriteFileAsync(projectId, LocalFileStorage.IfcFileName, ifcBytes, ct);

    var project = Project.Create(projectId, publicToken, name, ifcBytes.Length, now);
    db.Projects.Add(project);
    await db.SaveChangesAsync(ct);

    project.MarkConverting(DateTimeOffset.UtcNow);
    await db.SaveChangesAsync(ct);

    try
    {
        var result = await converter.ConvertAsync(ifcBytes, projectId, ct);
        if (!storage.FileExists(projectId, LocalFileStorage.GlbFileName)
            || !storage.FileExists(projectId, LocalFileStorage.UsdzFileName)
            || !storage.FileExists(projectId, LocalFileStorage.ThumbnailFileName))
        {
            throw new ConversionException("Converter did not produce all required output files.");
        }

        project.MarkReady(result.DurationMs, DateTimeOffset.UtcNow);
        await db.SaveChangesAsync(ct);
    }
    catch (ConversionException ex)
    {
        logger.LogWarning(ex, "Conversion failed for project {ProjectId}", projectId);
        project.MarkFailed(ex.Message, DateTimeOffset.UtcNow);
        await db.SaveChangesAsync(ct);
        return Results.Problem(statusCode: 502, title: "Conversion failed", detail: ex.Message);
    }

    var shareUrl = $"{publicBaseUrl}/s/{publicToken}";
    var qrSvg = qr.GenerateSvg(shareUrl);

    return Results.Ok(new
    {
        token = publicToken,
        projectId,
        name = project.Name,
        status = project.Status.ToString(),
        shareUrl,
        qrSvg,
    });
}).DisableAntiforgery();

// GET /files/{projectId}/{fileName}
app.MapMethods("/files/{projectId:guid}/{fileName}", new[] { "GET", "HEAD" }, (HttpContext ctx, Guid projectId, string fileName, LocalFileStorage storage) =>
{
    if (fileName is not (LocalFileStorage.GlbFileName or LocalFileStorage.UsdzFileName or LocalFileStorage.ThumbnailFileName))
    {
        return Results.NotFound();
    }

    if (HttpMethods.IsHead(ctx.Request.Method))
    {
        var headPath = storage.ResolvePath(projectId, fileName);
        if (!storage.IsInsideDataRoot(headPath) || !File.Exists(headPath))
        {
            return Results.NotFound();
        }
        var headInfo = new FileInfo(headPath);
        var headType = fileName switch
        {
            LocalFileStorage.GlbFileName => "model/gltf-binary",
            LocalFileStorage.UsdzFileName => "model/vnd.usdz+zip",
            LocalFileStorage.ThumbnailFileName => "image/png",
            _ => "application/octet-stream",
        };
        ctx.Response.Headers.ContentLength = headInfo.Length;
        ctx.Response.Headers.ContentType = headType;
        if (string.Equals(fileName, LocalFileStorage.GlbFileName, StringComparison.OrdinalIgnoreCase))
        {
            ctx.Response.Headers.AcceptRanges = "bytes";
        }
        return Results.Empty;
    }

    return ServeProjectFile(projectId, fileName, storage);
});

// GET /share/{token}
app.MapGet("/share/{token}", async (string token, AppDbContext db, CancellationToken ct) =>
{
    var project = await db.Projects.AsNoTracking()
        .FirstOrDefaultAsync(p => p.PublicToken == token, ct);

    if (project is null)
    {
        return Results.NotFound();
    }

    if (project.Status == ProjectStatus.Converting || project.Status == ProjectStatus.Uploading)
    {
        return Results.Ok(new
        {
            name = project.Name,
            status = project.Status.ToString(),
            glbUrl = (string?)null,
            usdzUrl = (string?)null,
            thumbnailUrl = (string?)null,
        });
    }

    if (project.Status != ProjectStatus.Ready)
    {
        return Results.NotFound();
    }

    return Results.Ok(new
    {
        name = project.Name,
        status = project.Status.ToString(),
        glbUrl = FileUrl(project.Id, LocalFileStorage.GlbFileName),
        usdzUrl = FileUrl(project.Id, LocalFileStorage.UsdzFileName),
        thumbnailUrl = FileUrl(project.Id, LocalFileStorage.ThumbnailFileName),
    });
});

// GET /share/{token}/qr  (alias: /qrcode/{token})
app.MapGet("/share/{token}/qr", async (string token, AppDbContext db, QrCodeService qr, CancellationToken ct) =>
{
    var project = await db.Projects.AsNoTracking()
        .FirstOrDefaultAsync(p => p.PublicToken == token, ct);
    if (project is null || project.Status != ProjectStatus.Ready) return Results.NotFound();
    var shareUrl = $"{publicBaseUrl}/s/{token}";
    var svg = qr.GenerateSvg(shareUrl);
    return Results.Content(svg, "image/svg+xml");
});

app.MapGet("/qrcode/{token}", async (string token, AppDbContext db, QrCodeService qr, CancellationToken ct) =>
{
    var project = await db.Projects.AsNoTracking()
        .FirstOrDefaultAsync(p => p.PublicToken == token, ct);
    if (project is null || project.Status != ProjectStatus.Ready) return Results.NotFound();
    var shareUrl = $"{publicBaseUrl}/s/{token}";
    var svg = qr.GenerateSvg(shareUrl);
    return Results.Content(svg, "image/svg+xml");
});

app.Run();

public partial class Program { }
