using Minio;
using Minio.DataModel.Args;

namespace Arch3DAr.Backend.Infrastructure;

public class MinioSettings
{
    public string Endpoint { get; set; } = string.Empty;
    public string PublicEndpoint { get; set; } = string.Empty;
    public string AccessKey { get; set; } = string.Empty;
    public string SecretKey { get; set; } = string.Empty;
    public bool UseSsl { get; set; }
    public string BucketIfc { get; set; } = "ifc-files";
    public string BucketGlb { get; set; } = "glb-files";
    public string BucketThumbnails { get; set; } = "thumbnails";
    public string BucketQrcodes { get; set; } = "qrcodes";
    public int PresignTtlSeconds { get; set; } = 600;
}

public class MinioService
{
    private readonly IMinioClient _client;
    private readonly MinioSettings _settings;
    private readonly ILogger<MinioService> _logger;

    public MinioService(IMinioClient client, MinioSettings settings, ILogger<MinioService> logger)
    {
        _client = client;
        _settings = settings;
        _logger = logger;
    }

    public static IMinioClient BuildClient(MinioSettings s) =>
        new MinioClient()
            .WithEndpoint(s.Endpoint)
            .WithCredentials(s.AccessKey, s.SecretKey)
            .WithSSL(s.UseSsl)
            .Build();

    public async Task EnsureBucketsAsync(CancellationToken ct = default)
    {
        foreach (var bucket in new[]
                 {
                     _settings.BucketIfc,
                     _settings.BucketGlb,
                     _settings.BucketThumbnails,
                     _settings.BucketQrcodes,
                 })
        {
            var exists = await _client.BucketExistsAsync(new BucketExistsArgs().WithBucket(bucket), ct);
            if (!exists)
            {
                await _client.MakeBucketAsync(new MakeBucketArgs().WithBucket(bucket), ct);
                _logger.LogInformation("Created MinIO bucket {Bucket}", bucket);
            }
        }
    }

    public async Task UploadStreamAsync(string bucket, string key, Stream content, string contentType, CancellationToken ct = default)
    {
        await _client.PutObjectAsync(new PutObjectArgs()
            .WithBucket(bucket)
            .WithObject(key)
            .WithStreamData(content)
            .WithObjectSize(content.Length - content.Position)
            .WithContentType(contentType), ct);
    }

    public async Task<byte[]> DownloadAsync(string bucket, string key, CancellationToken ct = default)
    {
        using var ms = new MemoryStream();
        await _client.GetObjectAsync(new GetObjectArgs()
            .WithBucket(bucket)
            .WithObject(key)
            .WithCallbackStream(stream => stream.CopyTo(ms)), ct);
        return ms.ToArray();
    }

    public async Task<string> GetPresignedUrlAsync(string bucket, string key, CancellationToken ct = default)
    {
        var args = new PresignedGetObjectArgs()
            .WithBucket(bucket)
            .WithObject(key)
            .WithExpiry(_settings.PresignTtlSeconds);
        var url = await _client.PresignedGetObjectAsync(args);
        if (!string.IsNullOrEmpty(_settings.PublicEndpoint))
        {
            var uri = new UriBuilder(url);
            uri.Scheme = "https";
            uri.Host = _settings.PublicEndpoint.Split(':')[0];
            uri.Port = -1;
            url = uri.ToString();
        }
        return url;
    }
}
