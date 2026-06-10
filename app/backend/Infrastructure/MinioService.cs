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
    public int PresignTtlSeconds { get; set; } = 3600;
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
        foreach (var bucket in new[] { _settings.BucketIfc, _settings.BucketGlb, _settings.BucketThumbnails })
        {
            var exists = await _client.BucketExistsAsync(new BucketExistsArgs().WithBucket(bucket), ct);
            if (!exists)
            {
                await _client.MakeBucketAsync(new MakeBucketArgs().WithBucket(bucket), ct);
                _logger.LogInformation("Created MinIO bucket {Bucket}", bucket);
            }
        }
    }

    public async Task UploadBytesAsync(string bucket, string key, byte[] data, string contentType, CancellationToken ct = default)
    {
        using var ms = new MemoryStream(data);
        await _client.PutObjectAsync(new PutObjectArgs()
            .WithBucket(bucket)
            .WithObject(key)
            .WithStreamData(ms)
            .WithObjectSize(data.Length)
            .WithContentType(contentType), ct);
    }

    public async Task<string> GetPresignedUrlAsync(string bucket, string key, CancellationToken ct = default)
    {
        // For query-string presigned URLs, AWS SigV4 includes the Host header in the
        // canonical request. If we sign with one host and the browser sends a different
        // one, MinIO rejects it with SignatureDoesNotMatch.
        //
        // nginx now terminates TLS and proxies to MinIO on HTTPS (port 443).
        // We create a signing client with the public endpoint + SSL=true so the
        // signature matches what the browser will send.
        var host = _settings.PublicEndpoint.Split(':')[0];
        using var signingClient = new MinioClient()
            .WithEndpoint(host)
            .WithCredentials(_settings.AccessKey, _settings.SecretKey)
            .WithSSL(true)
            .Build();
        var args = new PresignedGetObjectArgs()
            .WithBucket(bucket)
            .WithObject(key)
            .WithExpiry(_settings.PresignTtlSeconds);
        return await signingClient.PresignedGetObjectAsync(args);
    }
}
