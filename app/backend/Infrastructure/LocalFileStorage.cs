namespace Arch3DAr.Backend.Infrastructure;

public sealed class LocalFileStorageSettings
{
    public string DataRoot { get; set; } = "/data";
}

public sealed class LocalFileStorage
{
    public const string IfcFileName = "original.ifc";
    public const string GlbFileName = "model.glb";
    public const string UsdzFileName = "model.usdz";
    public const string ThumbnailFileName = "thumbnail.png";

    private readonly string _dataRoot;

    public LocalFileStorage(LocalFileStorageSettings settings)
    {
        _dataRoot = Path.GetFullPath(settings.DataRoot);
        Directory.CreateDirectory(_dataRoot);
    }

    public string ProjectRelativeDirectory(Guid projectId) => $"projects/{projectId}";

    public string EnsureProjectDir(Guid projectId)
    {
        var dir = ResolveProjectDir(projectId);
        Directory.CreateDirectory(dir);
        return dir;
    }

    public string ResolveProjectDir(Guid projectId) =>
        Path.Combine(_dataRoot, "projects", projectId.ToString());

    public string ResolvePath(Guid projectId, string fileName)
    {
        var path = Path.Combine(ResolveProjectDir(projectId), fileName);
        return Path.GetFullPath(path);
    }

    public async Task WriteFileAsync(Guid projectId, string fileName, byte[] bytes, CancellationToken ct)
    {
        EnsureProjectDir(projectId);
        var path = ResolvePath(projectId, fileName);
        await File.WriteAllBytesAsync(path, bytes, ct);
    }

    public bool FileExists(Guid projectId, string fileName)
    {
        var path = ResolvePath(projectId, fileName);
        return File.Exists(path) && new FileInfo(path).Length > 0;
    }

    public bool IsInsideDataRoot(string fullPath)
    {
        var normalized = Path.GetFullPath(fullPath);
        return normalized.StartsWith(_dataRoot + Path.DirectorySeparatorChar, StringComparison.Ordinal)
               || normalized.Equals(_dataRoot, StringComparison.Ordinal);
    }
}
