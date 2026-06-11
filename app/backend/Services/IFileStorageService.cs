using Arch3DAr.Backend.Infrastructure;

namespace Arch3DAr.Backend.Services;

public interface IFileStorageService
{
    string ProjectRelativeDirectory(Guid projectId);

    string EnsureProjectDir(Guid projectId);

    string ResolvePath(Guid projectId, string fileName);

    Task WriteFileAsync(Guid projectId, string fileName, byte[] bytes, CancellationToken ct);

    bool FileExists(Guid projectId, string fileName);

    bool IsInsideDataRoot(string fullPath);
}

public sealed class LocalFileStorageAdapter(LocalFileStorage inner) : IFileStorageService
{
    public string ProjectRelativeDirectory(Guid projectId) => inner.ProjectRelativeDirectory(projectId);

    public string EnsureProjectDir(Guid projectId) => inner.EnsureProjectDir(projectId);

    public string ResolvePath(Guid projectId, string fileName) => inner.ResolvePath(projectId, fileName);

    public Task WriteFileAsync(Guid projectId, string fileName, byte[] bytes, CancellationToken ct) =>
        inner.WriteFileAsync(projectId, fileName, bytes, ct);

    public bool FileExists(Guid projectId, string fileName) => inner.FileExists(projectId, fileName);

    public bool IsInsideDataRoot(string fullPath) => inner.IsInsideDataRoot(fullPath);
}
