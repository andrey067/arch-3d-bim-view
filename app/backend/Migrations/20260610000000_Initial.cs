using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Arch3DAr.Backend.Migrations
{
    public partial class Initial : Migration
    {
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "projects",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uuid", nullable: false),
                    PublicToken = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: false),
                    Name = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                    Status = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: false),
                    ErrorMessage = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    IfcObjectKey = table.Column<string>(type: "character varying(512)", maxLength: 512, nullable: false),
                    GlbObjectKey = table.Column<string>(type: "character varying(512)", maxLength: 512, nullable: true),
                    ThumbnailObjectKey = table.Column<string>(type: "character varying(512)", maxLength: 512, nullable: true),
                    IfcSizeBytes = table.Column<long>(type: "bigint", nullable: false),
                    ConversionDurationMs = table.Column<long>(type: "bigint", nullable: true),
                    CreatedAt = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    UpdatedAt = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                },
                constraints: table => table.PrimaryKey("PK_projects", x => x.Id));

            migrationBuilder.CreateIndex(
                name: "ux_projects_public_token",
                table: "projects",
                column: "PublicToken",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_projects_created_at",
                table: "projects",
                column: "CreatedAt");
        }

        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(name: "projects");
        }
    }
}
