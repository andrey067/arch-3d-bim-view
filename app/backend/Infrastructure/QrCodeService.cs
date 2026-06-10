using QRCoder;

namespace Arch3DAr.Backend.Infrastructure;

public class QrCodeService
{
    public string GenerateSvg(string url, int pixelsPerModule = 8)
    {
        using var generator = new QRCodeGenerator();
        using var data = generator.CreateQrCode(url, QRCodeGenerator.ECCLevel.Q);
        var svg = new SvgQRCode(data);
        return svg.GetGraphic(pixelsPerModule);
    }
}
