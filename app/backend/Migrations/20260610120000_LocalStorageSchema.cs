using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Arch3DAr.Backend.Migrations;

public partial class LocalStorageSchema : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.Sql("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'projects'
                      AND column_name = 'IfcObjectKey'
                ) THEN
                    ALTER TABLE projects ADD COLUMN IF NOT EXISTS "DataDirectory" character varying(512);
                    UPDATE projects
                    SET "DataDirectory" = 'projects/' || "Id"::text
                    WHERE "DataDirectory" IS NULL;
                    ALTER TABLE projects ALTER COLUMN "DataDirectory" SET NOT NULL;
                    ALTER TABLE projects DROP COLUMN IF EXISTS "IfcObjectKey";
                    ALTER TABLE projects DROP COLUMN IF EXISTS "GlbObjectKey";
                    ALTER TABLE projects DROP COLUMN IF EXISTS "UsdzObjectKey";
                    ALTER TABLE projects DROP COLUMN IF EXISTS "ThumbnailObjectKey";
                END IF;
            END $$;
            """);
    }

    protected override void Down(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.Sql("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'projects'
                      AND column_name = 'DataDirectory'
                ) THEN
                    ALTER TABLE projects ADD COLUMN IF NOT EXISTS "IfcObjectKey" character varying(512);
                    UPDATE projects SET "IfcObjectKey" = '' WHERE "IfcObjectKey" IS NULL;
                    ALTER TABLE projects ALTER COLUMN "IfcObjectKey" SET NOT NULL;
                    ALTER TABLE projects DROP COLUMN IF EXISTS "DataDirectory";
                END IF;
            END $$;
            """);
    }
}
