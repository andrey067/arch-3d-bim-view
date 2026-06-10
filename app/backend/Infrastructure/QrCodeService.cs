using QRCoder;

namespace Arch3DAr.Backend.Infrastructure;

public class QrCodeService
{
    public byte[] GeneratePng(string url, int pixelsPerModule = 20)
    {
        using var generator = new QRCodeGenerator();
        using var data = generator.CreateQrCode(url, QRCodeGenerator.ECCLevel.Q);
        var png = new PngByteQRCode(data);
        return png.GetGraphic(pixelsPerModule);
    }
}
