using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;

namespace Arch3DAr.Backend.Tests.Integration;

public class WebAppFactory : WebApplicationFactory<Program>
{
    public string DataRoot { get; } = Path.Combine(Path.GetTempPath(), "arch3dar-api-" + Guid.NewGuid());

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Testing");
        builder.UseSetting("DATA_ROOT", DataRoot);
        builder.UseSetting("PublicBaseUrl", "https://test.local");
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing && Directory.Exists(DataRoot))
        {
            Directory.Delete(DataRoot, recursive: true);
        }

        base.Dispose(disposing);
    }
}
