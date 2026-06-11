using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Arch3DAr.Backend.Migrations;

public partial class AddSourceFormat : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.Sql("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'projects'
                      AND column_name = 'SourceFormat'
                ) THEN
                    ALTER TABLE projects
                        ADD COLUMN "SourceFormat" character varying(8) NOT NULL DEFAULT 'Ifc';
                END IF;
            END $$;
            """);
    }

    protected override void Down(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.DropColumn(name: "SourceFormat", table: "projects");
    }
}
