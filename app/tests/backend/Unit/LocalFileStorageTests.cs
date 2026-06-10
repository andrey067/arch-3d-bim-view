using Arch3DAr.Backend.Infrastructure;
using Xunit;

namespace Arch3DAr.Backend.Tests.Unit;

public class LocalFileStorageTests : IDisposable
{
    private readonly string _root;
    private readonly LocalFileStorage _storage;

    public LocalFileStorageTests()
    {
        _root = Path.Combine(Path.GetTempPath(), "arch3dar-storage-" + Guid.NewGuid());
        _storage = new LocalFileStorage(new LocalFileStorageSettings { DataRoot = _root });
    }

    public void Dispose()
    {
        if (Directory.Exists(_root))
        {
            Directory.Delete(_root, recursive: true);
        }
    }

    [Fact]
    public async Task WriteFile_And_FileExists_Work()
    {
        var id = Guid.NewGuid();
        await _storage.WriteFileAsync(id, LocalFileStorage.GlbFileName, [1, 2, 3], CancellationToken.None);
        Assert.True(_storage.FileExists(id, LocalFileStorage.GlbFileName));
        Assert.False(_storage.FileExists(id, LocalFileStorage.UsdzFileName));
    }

    [Fact]
    public void ResolvePath_Stays_Inside_DataRoot()
    {
        var id = Guid.NewGuid();
        var path = _storage.ResolvePath(id, LocalFileStorage.GlbFileName);
        Assert.True(_storage.IsInsideDataRoot(path));
    }
}
