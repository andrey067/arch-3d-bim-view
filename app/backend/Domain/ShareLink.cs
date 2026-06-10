namespace Arch3DAr.Backend.Domain;

public class ShareLink
{
    public Guid Id { get; private set; } = Guid.NewGuid();
    public Guid ProjectId { get; private set; }
    public Guid PublicToken { get; private set; }
    public string? QrCodeObjectKey { get; private set; }
    public DateTimeOffset CreatedAt { get; private set; } = DateTimeOffset.UtcNow;

    private ShareLink() { }

    public static ShareLink Create(Guid projectId, Guid publicToken, DateTimeOffset now)
    {
        return new ShareLink
        {
            ProjectId = projectId,
            PublicToken = publicToken,
            CreatedAt = now,
        };
    }

    public void AttachQrCode(string qrCodeObjectKey)
    {
        QrCodeObjectKey = qrCodeObjectKey;
    }
}
