using System.Text;
using Arch3DAr.Backend.Domain;
using Arch3DAr.Backend.Infrastructure;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.EntityFrameworkCore;
using Minio;
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
    PresignTtlSeconds = int.TryParse(builder.Configuration["MinIO:PresignTtlSeconds"], out var ttl) ? ttl : 3600,
};

var converterSettings = new ConverterSettings
{
    Url = builder.Configuration["Converter:Url"] ?? "http://converter:8080",
};

var publicBaseUrl = (builder.Configuration["PublicBaseUrl"] ?? "http://localhost:3100").TrimEnd('/');
var maxIfcMb = int.TryParse(builder.Configuration["MaxIfcMb"], out var mb) ? mb : 100;
var maxIfcBytes = (long)maxIfcMb * 1024L * 1024L;
var allowedOrigins = (builder.Configuration["Cors:AllowedOrigins"] ?? "http://localhost:3100")
    .Split(';', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);

builder.Services.AddSingleton(minioSettings);
builder.Services.AddSingleton(converterSettings);
builder.Services.AddSingleton<IMinioClient>(_ => MinioService.BuildClient(minioSettings));
builder.Services.AddScoped<MinioService>();
builder.Services.AddSingleton<QrCodeService>();
builder.Services.AddHttpContextAccessor();
builder.Services.AddHttpClient<HttpModelConverter>();

builder.Services.AddDbContext<AppDbContext>(opts =>
    opts.UseNpgsql(builder.Configuration.GetConnectionString("DefaultConnection"))
       .ConfigureWarnings(w => w.Ignore(Microsoft.EntityFrameworkCore.Diagnostics.RelationalEventId.PendingModelChangesWarning)));

builder.Services.AddCors(o => o.AddDefaultPolicy(p =>
    p.WithOrigins(allowedOrigins)
     .AllowAnyHeader()
     .AllowAnyMethod()
     .AllowCredentials()));

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
    await db.Database.EnsureCreatedAsync();
    var minio = scope.ServiceProvider.GetRequiredService<MinioService>();
    await minio.EnsureBucketsAsync();
}

string NewToken()
{
    Span<byte> bytes = stackalloc byte[16];
    System.Security.Cryptography.RandomNumberGenerator.Fill(bytes);
    return Convert.ToHexString(bytes).ToLowerInvariant();
}

// GET /health
app.MapGet("/health", () => Results.Ok(new { status = "ok" }));

// POST /upload  (multipart, single .ifc; field name "file", optional "name")
app.MapPost("/upload", async (
    HttpContext http,
    AppDbContext db,
    MinioService minio,
    MinioSettings minioSettings,
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

    // Read first line and check IFC signature
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
    var ifcKey = $"projects/{projectId}/source.ifc";

    byte[] ifcBytes;
    await using (var s = file.OpenReadStream())
    using (var ms = new MemoryStream())
    {
        await s.CopyToAsync(ms, ct);
        ifcBytes = ms.ToArray();
    }
    await minio.UploadBytesAsync(minioSettings.BucketIfc, ifcKey, ifcBytes, "application/octet-stream", ct);

    var now = DateTimeOffset.UtcNow;
    var project = Project.Create(publicToken, name, ifcKey, ifcBytes.Length, now);
    db.Projects.Add(project);
    await db.SaveChangesAsync(ct);

    try
    {
        var result = await converter.ConvertAsync(ifcBytes, projectId, ct);
        project.MarkReady(result.GlbKey, result.UsdzKey, result.ThumbnailKey, result.DurationMs, DateTimeOffset.UtcNow);
        await db.SaveChangesAsync(ct);
    }
    catch (ConversionException ex)
    {
        logger.LogWarning(ex, "Conversion failed for project {ProjectId}", projectId);
        project.MarkFailed(ex.Message, DateTimeOffset.UtcNow);
        await db.SaveChangesAsync(ct);
    }

    var shareUrl = $"{publicBaseUrl}/s/{publicToken}";
    var qrSvg = qr.GenerateSvg(shareUrl);

    return Results.Ok(new
    {
        token = publicToken,
        name = project.Name,
        status = project.Status.ToString(),
        shareUrl,
        qrSvg,
    });
}).DisableAntiforgery();

// GET /share/{token}
app.MapGet("/share/{token}", async (
    string token,
    AppDbContext db,
    MinioService minio,
    MinioSettings minioSettings,
    CancellationToken ct) =>
{
    var project = await db.Projects.AsNoTracking()
        .FirstOrDefaultAsync(p => p.PublicToken == token, ct);
    if (project is null || project.Status != ProjectStatus.Ready
        || string.IsNullOrEmpty(project.GlbObjectKey)
        || string.IsNullOrEmpty(project.ThumbnailObjectKey))
    {
        return Results.NotFound();
    }

    var glbUrl = await minio.GetPresignedUrlAsync(minioSettings.BucketGlb, project.GlbObjectKey, ct);
    var thumbUrl = await minio.GetPresignedUrlAsync(minioSettings.BucketThumbnails, project.ThumbnailObjectKey, ct);

    string? usdzUrl = null;
    if (!string.IsNullOrEmpty(project.UsdzObjectKey))
    {
        usdzUrl = await minio.GetPresignedUrlAsync(minioSettings.BucketGlb, project.UsdzObjectKey, ct);
    }

    return Results.Ok(new
    {
        name = project.Name,
        glbUrl,
        usdzUrl,
        thumbnailUrl = thumbUrl,
    });
});

// GET /share/{token}/qr
app.MapGet("/share/{token}/qr", async (
    string token,
    AppDbContext db,
    QrCodeService qr,
    CancellationToken ct) =>
{
    var project = await db.Projects.AsNoTracking()
        .FirstOrDefaultAsync(p => p.PublicToken == token, ct);
    if (project is null) return Results.NotFound();
    var shareUrl = $"{publicBaseUrl}/s/{token}";
    var svg = qr.GenerateSvg(shareUrl);
    return Results.Content(svg, "image/svg+xml");
});

app.Run();

public partial class Program { }
