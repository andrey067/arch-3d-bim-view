using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Arch3DAr.Backend.Migrations;

public partial class AddSourceFormat : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.AddColumn<string>(
            name: "SourceFormat",
            table: "projects",
            type: "character varying(8)",
            maxLength: 8,
            nullable: false,
            defaultValue: "Ifc");
    }

    protected override void Down(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.DropColumn(name: "SourceFormat", table: "projects");
    }
}
