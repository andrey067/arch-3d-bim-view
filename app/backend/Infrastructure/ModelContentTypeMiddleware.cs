namespace Arch3DAr.Backend.Infrastructure;

public sealed class ModelContentTypeMiddleware
{
    private static readonly Dictionary<string, string> MimeByExtension = new(StringComparer.OrdinalIgnoreCase)
    {
        [".glb"] = "model/gltf-binary",
        [".usdz"] = "model/vnd.usdz+zip",
        [".png"] = "image/png",
        [".webp"] = "image/webp",
    };

    private readonly RequestDelegate _next;

    public ModelContentTypeMiddleware(RequestDelegate next) => _next = next;

    public async Task InvokeAsync(HttpContext context)
    {
        var path = context.Request.Path.Value ?? string.Empty;
        var ext = Path.GetExtension(path);
        if (MimeByExtension.TryGetValue(ext, out var mime))
        {
            context.Response.OnStarting(() =>
            {
                context.Response.ContentType = mime;
                if (ext.Equals(".glb", StringComparison.OrdinalIgnoreCase))
                {
                    context.Response.Headers.AcceptRanges = "bytes";
                }
                return Task.CompletedTask;
            });
        }

        await _next(context);
    }
}
