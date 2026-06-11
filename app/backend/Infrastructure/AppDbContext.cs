using Arch3DAr.Backend.Domain;
using Microsoft.EntityFrameworkCore;

namespace Arch3DAr.Backend.Infrastructure;

public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

    public DbSet<Project> Projects => Set<Project>();

    protected override void OnModelCreating(ModelBuilder b)
    {
        b.Entity<Project>(e =>
        {
            e.ToTable("projects");
            e.HasKey(x => x.Id);
            e.Property(x => x.PublicToken).HasMaxLength(32).IsRequired();
            e.Property(x => x.Name).HasMaxLength(200).IsRequired();
            e.Property(x => x.Status).HasMaxLength(32).HasConversion<string>().IsRequired();
            e.Property(x => x.SourceFormat).HasMaxLength(8).HasConversion<string>().IsRequired();
            e.Property(x => x.ErrorMessage).HasMaxLength(500);
            e.Property(x => x.DataDirectory).HasMaxLength(512).IsRequired();
            e.HasIndex(x => x.PublicToken).IsUnique().HasDatabaseName("ux_projects_public_token");
            e.HasIndex(x => x.CreatedAt).HasDatabaseName("ix_projects_created_at");
        });
    }
}
