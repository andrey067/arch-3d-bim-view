using Arch3DAr.Backend.Domain;
using Microsoft.EntityFrameworkCore;

namespace Arch3DAr.Backend.Infrastructure;

public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options)
        : base(options)
    {
    }

    public DbSet<Project> Projects => Set<Project>();
    public DbSet<ShareLink> ShareLinks => Set<ShareLink>();

    protected override void OnModelCreating(ModelBuilder b)
    {
        b.Entity<Project>(e =>
        {
            e.ToTable("projects");
            e.HasKey(x => x.Id);
            e.Property(x => x.OwnerId).IsRequired();
            e.Property(x => x.Name).HasMaxLength(200).IsRequired();
            e.Property(x => x.Description).HasMaxLength(2000);
            e.Property(x => x.ClientLabel).HasMaxLength(200);
            e.Property(x => x.Status).HasMaxLength(32).HasConversion<string>().IsRequired();
            e.Property(x => x.ErrorMessage).HasMaxLength(500);
            e.Property(x => x.IfcObjectKey).HasMaxLength(512);
            e.Property(x => x.GlbObjectKey).HasMaxLength(512);
            e.Property(x => x.ThumbnailObjectKey).HasMaxLength(512);
            e.HasIndex(x => x.OwnerId).HasDatabaseName("ix_projects_owner_id");
            e.HasIndex(x => x.Status).HasDatabaseName("ix_projects_status");
            e.HasIndex(x => new { x.OwnerId, x.CreatedAt })
                .HasDatabaseName("ix_projects_owner_id_created_at")
                .IsDescending(false, true);
        });

        b.Entity<ShareLink>(e =>
        {
            e.ToTable("share_links");
            e.HasKey(x => x.Id);
            e.Property(x => x.PublicToken).IsRequired();
            e.Property(x => x.QrCodeObjectKey).HasMaxLength(512);
            e.HasIndex(x => x.ProjectId).IsUnique().HasDatabaseName("ux_share_links_project_id");
            e.HasIndex(x => x.PublicToken).IsUnique().HasDatabaseName("ux_share_links_public_token");
        });
    }
}
