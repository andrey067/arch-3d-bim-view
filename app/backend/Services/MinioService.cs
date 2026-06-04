using Minio;
using Minio.DataModel.Args;

namespace Backend.Services;

public class MinioService
{
    private readonly MinioClient _minioClient;
    private readonly IConfiguration _configuration;
    private readonly ILogger<MinioService> _logger;

    public MinioService(MinioClient minioClient, IConfiguration configuration, ILogger<MinioService> logger)
    {
        _minioClient = minioClient;
        _configuration = configuration;
        _logger = logger;
    }

    private string GetBucketName(string key) =>
        _configuration[$"MinIO__Bucket__{key}"] ?? throw new InvalidOperationException($"Bucket configuration MinIO__Bucket__{key} not found");

    public string IfcFilesBucket => GetBucketName("IfcFiles");
    public string GlbFilesBucket => GetBucketName("GlbFiles");
    public string ThumbnailsBucket => GetBucketName("Thumbnails");

    public async Task EnsureBucketsExistAsync()
    {
        var buckets = new[] { IfcFilesBucket, GlbFilesBucket, ThumbnailsBucket };

        foreach (var bucketName in buckets)
        {
            try
            {
                var bucketExistsArgs = new BucketExistsArgs().WithBucket(bucketName);
                var exists = await _minioClient.BucketExistsAsync(bucketExistsArgs);
                if (!exists)
                {
                    var makeBucketArgs = new MakeBucketArgs().WithBucket(bucketName);
                    await _minioClient.MakeBucketAsync(makeBucketArgs);
                    _logger.LogInformation("Created bucket: {BucketName}", bucketName);
                }
                else
                {
                    _logger.LogInformation("Bucket already exists: {BucketName}", bucketName);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error ensuring bucket exists: {BucketName}", bucketName);
                throw;
            }
        }
    }

    public async Task UploadFileAsync(string bucketName, string objectKey, Stream stream, string contentType)
    {
        try
        {
            var putObjectArgs = new PutObjectArgs()
                .WithBucket(bucketName)
                .WithObject(objectKey)
                .WithStreamData(stream)
                .WithObjectSize(stream.Length)
                .WithContentType(contentType);

            await _minioClient.PutObjectAsync(putObjectArgs);
            _logger.LogInformation("Uploaded file to {BucketName}/{ObjectKey}", bucketName, objectKey);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error uploading file to {BucketName}/{ObjectKey}", bucketName, objectKey);
            throw;
        }
    }

    public async Task<string> GetPresignedUrlAsync(string bucketName, string objectKey, int expirySeconds = 3600)
    {
        try
        {
            var presignedGetObjectArgs = new PresignedGetObjectArgs()
                .WithBucket(bucketName)
                .WithObject(objectKey)
                .WithExpiry(expirySeconds);

            var url = await _minioClient.PresignedGetObjectAsync(presignedGetObjectArgs);
            _logger.LogInformation("Generated presigned URL for {BucketName}/{ObjectKey} with expiry {Expiry}s", bucketName, objectKey, expirySeconds);
            return url;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error generating presigned URL for {BucketName}/{ObjectKey}", bucketName, objectKey);
            throw;
        }
    }
}
