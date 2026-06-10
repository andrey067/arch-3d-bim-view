using Microsoft.EntityFrameworkCore;

namespace Arch3DAr.Backend.Infrastructure;

public static class DatabaseMigrator
{
    public static async Task ApplyAsync(AppDbContext db, CancellationToken ct = default)
    {
        if (!db.Database.IsRelational())
        {
            return;
        }

        if (await ProjectsTableExistsAsync(db, ct) && !await MigrationHistoryExistsAsync(db, ct))
        {
            await db.Database.ExecuteSqlRawAsync("""
                CREATE TABLE IF NOT EXISTS "__EFMigrationsHistory" (
                    "MigrationId" character varying(150) NOT NULL,
                    "ProductVersion" character varying(32) NOT NULL,
                    CONSTRAINT "PK___EFMigrationsHistory" PRIMARY KEY ("MigrationId")
                );
                INSERT INTO "__EFMigrationsHistory" ("MigrationId", "ProductVersion")
                SELECT '20260610000000_Initial', '9.0.0'
                WHERE NOT EXISTS (
                    SELECT 1 FROM "__EFMigrationsHistory"
                    WHERE "MigrationId" = '20260610000000_Initial'
                );
                """, ct);
        }

        await db.Database.MigrateAsync(ct);
    }

    private static async Task<bool> ProjectsTableExistsAsync(AppDbContext db, CancellationToken ct)
    {
        await db.Database.OpenConnectionAsync(ct);
        try
        {
            await using var cmd = db.Database.GetDbConnection().CreateCommand();
            cmd.CommandText = """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'projects'
                );
                """;
            var result = await cmd.ExecuteScalarAsync(ct);
            return result is bool b && b;
        }
        finally
        {
            await db.Database.CloseConnectionAsync();
        }
    }

    private static async Task<bool> MigrationHistoryExistsAsync(AppDbContext db, CancellationToken ct)
    {
        await db.Database.OpenConnectionAsync(ct);
        try
        {
            await using var cmd = db.Database.GetDbConnection().CreateCommand();
            cmd.CommandText = """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = '__EFMigrationsHistory'
                );
                """;
            var result = await cmd.ExecuteScalarAsync(ct);
            return result is bool b && b;
        }
        finally
        {
            await db.Database.CloseConnectionAsync();
        }
    }
}
