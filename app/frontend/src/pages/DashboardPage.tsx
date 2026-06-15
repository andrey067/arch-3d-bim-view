/**
 * Sprint 2 — Dashboard with project list and creation modal.
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  useProjects,
  useCreateProject,
  useDeleteProject,
  useArchiveProject,
  type ProjectListItem,
} from '@/features/projects/useProjects';
import { Button, Card, Input, Spinner } from '@/shared/components';

export const DashboardPage = () => {
  const navigate = useNavigate();
  const { data: projects, isLoading, error } = useProjects();
  const createProject = useCreateProject();
  const deleteProject = useDeleteProject();
  const archiveProject = useArchiveProject();

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [createError, setCreateError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!newName.trim()) {
      setCreateError('Nome do projeto é obrigatório.');
      return;
    }
    setCreateError(null);
    try {
      await createProject.mutateAsync({
        name: newName.trim(),
        description: newDescription.trim() || undefined,
      });
      setShowCreateModal(false);
      setNewName('');
      setNewDescription('');
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Erro ao criar projeto.');
    }
  };

  const handleDelete = async (projectId: string, projectName: string) => {
    if (window.confirm(`Tem certeza que deseja excluir o projeto "${projectName}"? Esta ação não pode ser desfeita.`)) {
      try {
        await deleteProject.mutateAsync(projectId);
      } catch {
        // Error handled by mutation
      }
    }
  };

  const handleArchive = async (projectId: string) => {
    try {
      await archiveProject.mutateAsync(projectId);
    } catch {
      // Error handled by mutation
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ fontSize: 'var(--font-size-xl)', margin: 0 }}>Meus Projetos</h1>
        <Button onClick={() => setShowCreateModal(true)}>Novo Projeto</Button>
      </div>

      {/* Error state */}
      {error && (
        <Card style={{ background: 'var(--color-danger)', color: '#fff' }}>
          <p style={{ margin: 0 }}>Erro ao carregar projetos. Tente novamente.</p>
        </Card>
      )}

      {/* Loading state */}
      {isLoading && (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--space-6)' }}>
          <Spinner size={32} />
        </div>
      )}

      {/* Empty state */}
      {!isLoading && projects && projects.length === 0 && (
        <Card>
          <div style={{ textAlign: 'center', padding: 'var(--space-4)' }}>
            <p style={{ margin: '0 0 var(--space-4)', color: 'var(--color-text-muted)' }}>
              Você ainda não tem projetos.
            </p>
            <Button onClick={() => setShowCreateModal(true)}>Criar primeiro projeto</Button>
          </div>
        </Card>
      )}

      {/* Project list */}
      {!isLoading && projects && projects.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {projects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              onView={() => navigate(`/projects/${project.id}`)}
              onArchive={() => handleArchive(project.id)}
              onDelete={() => handleDelete(project.id, project.name)}
            />
          ))}
        </div>
      )}

      {/* Create modal */}
      {showCreateModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowCreateModal(false);
          }}
          onKeyDown={(e) => {
            if (e.key === 'Escape') setShowCreateModal(false);
          }}
        >
          <Card style={{ width: '100%', maxWidth: 480, margin: 'var(--space-4)' }}>
            <h2 style={{ margin: '0 0 var(--space-4)', fontSize: 'var(--font-size-lg)' }}>
              Novo Projeto
            </h2>

            {createError && (
              <p style={{ color: 'var(--color-danger)', margin: '0 0 var(--space-3)', fontSize: 'var(--font-size-sm)' }}>
                {createError}
              </p>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              <Input
                label="Nome do projeto"
                placeholder="Ex: Casa de Praia"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                maxLength={120}
                autoFocus
              />
              <Input
                label="Descrição (opcional)"
                placeholder="Descrição breve do projeto"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                maxLength={2000}
              />
            </div>

            <div style={{ display: 'flex', gap: 'var(--space-2)', justifyContent: 'flex-end', marginTop: 'var(--space-4)' }}>
              <Button variant="ghost" onClick={() => setShowCreateModal(false)}>
                Cancelar
              </Button>
              <Button onClick={handleCreate} disabled={createProject.isPending}>
                {createProject.isPending ? <Spinner size={16} /> : 'Criar Projeto'}
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  Project Card                                                       */
/* ------------------------------------------------------------------ */

interface ProjectCardProps {
  project: ProjectListItem;
  onView: () => void;
  onArchive: () => void;
  onDelete: () => void;
}

const ProjectCard = ({ project, onView, onArchive, onDelete }: ProjectCardProps) => (
  <Card
    style={{
      cursor: 'pointer',
      transition: 'border-color 0.15s ease',
    }}
    onClick={onView}
    onKeyDown={(e) => {
      if (e.key === 'Enter' || e.key === ' ') onView();
    }}
    tabIndex={0}
    role="button"
    aria-label={`Abrir projeto ${project.name}`}
  >
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
      <div style={{ flex: 1 }}>
        <h3 style={{ margin: '0 0 var(--space-1)', fontSize: 'var(--font-size-lg)' }}>
          {project.name}
        </h3>
        {project.description && (
          <p style={{ margin: '0 0 var(--space-2)', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
            {project.description}
          </p>
        )}
        <div style={{ display: 'flex', gap: 'var(--space-4)', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
          <span>{project.fileCount} arquivo{project.fileCount !== 1 ? 's' : ''}</span>
          <span>Criado em {new Date(project.createdAt).toLocaleDateString('pt-BR')}</span>
        </div>
      </div>
      <div
        style={{ display: 'flex', gap: 'var(--space-2)' }}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
      >
        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            onArchive();
          }}
          title="Arquivar projeto"
        >
          Arquivar
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          title="Excluir projeto"
          style={{ color: 'var(--color-danger)' }}
        >
          Excluir
        </Button>
      </div>
    </div>
  </Card>
);
