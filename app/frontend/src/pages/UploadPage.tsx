import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';

const MAX_FILE_SIZE = 500 * 1024 * 1024; // 500 MB

export default function UploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      validateAndSetFile(droppedFile);
    }
  }, [name]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      validateAndSetFile(selectedFile);
    }
  }, []);

  const validateAndSetFile = (selectedFile: File) => {
    setError(null);
    if (!selectedFile.name.toLowerCase().endsWith('.ifc')) {
      setError('Please select a valid IFC file (.ifc)');
      return;
    }
    if (selectedFile.size > MAX_FILE_SIZE) {
      setError('File size exceeds 500 MB limit');
      return;
    }
    setFile(selectedFile);
    if (!name) {
      setName(selectedFile.name.replace(/\.ifc$/i, ''));
    }
  };

  const handleUpload = async () => {
    if (!file || !name.trim()) {
      setError('Please provide a project name and select a file');
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const project = await api.uploadProject(file, name.trim(), (progress) => {
        setUploadProgress(progress.percentage);
      });
      navigate(`/view/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const styles: Record<string, React.CSSProperties> = {
    container: {
      maxWidth: '600px',
      margin: '0 auto',
      padding: '2rem',
    },
    card: {
      background: 'white',
      borderRadius: '0.75rem',
      boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
      padding: '2rem',
    },
    title: {
      fontSize: '1.875rem',
      fontWeight: 700,
      marginBottom: '1.5rem',
      color: '#1e293b',
    },
    dropZone: {
      border: `2px dashed ${isDragging ? '#2563eb' : '#e2e8f0'}`,
      borderRadius: '0.75rem',
      padding: '3rem',
      textAlign: 'center' as const,
      cursor: 'pointer',
      transition: 'all 0.2s',
      background: isDragging ? '#f0f7ff' : 'white',
    },
    dropZoneIcon: {
      fontSize: '3rem',
      marginBottom: '1rem',
      color: '#64748b',
    },
    dropZoneText: {
      fontSize: '1.125rem',
      fontWeight: 500,
      color: '#1e293b',
      marginBottom: '0.5rem',
    },
    dropZoneHint: {
      fontSize: '0.875rem',
      color: '#64748b',
    },
    fileInput: {
      display: 'none',
    },
    fileInfo: {
      marginTop: '1rem',
      padding: '1rem',
      background: '#f8fafc',
      borderRadius: '0.5rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
    },
    fileName: {
      fontWeight: 500,
      color: '#1e293b',
    },
    fileSize: {
      fontSize: '0.875rem',
      color: '#64748b',
    },
    formGroup: {
      marginTop: '1.5rem',
    },
    label: {
      display: 'block',
      marginBottom: '0.5rem',
      fontWeight: 500,
      color: '#1e293b',
    },
    input: {
      width: '100%',
      padding: '0.75rem',
      border: '1px solid #e2e8f0',
      borderRadius: '0.5rem',
      fontSize: '1rem',
    },
    uploadBtn: {
      width: '100%',
      marginTop: '1.5rem',
      padding: '0.75rem',
      background: '#2563eb',
      color: 'white',
      border: 'none',
      borderRadius: '0.5rem',
      fontSize: '1rem',
      fontWeight: 500,
      cursor: isUploading ? 'not-allowed' : 'pointer',
      opacity: isUploading ? 0.7 : 1,
    },
    progressContainer: {
      marginTop: '1rem',
    },
    progressBar: {
      width: '100%',
      height: '0.5rem',
      background: '#e2e8f0',
      borderRadius: '9999px',
      overflow: 'hidden',
    },
    progressFill: {
      height: '100%',
      background: '#2563eb',
      transition: 'width 0.3s ease',
      width: `${uploadProgress}%`,
    },
    progressText: {
      marginTop: '0.5rem',
      fontSize: '0.875rem',
      color: '#64748b',
      textAlign: 'center' as const,
    },
    errorMessage: {
      background: '#fee2e2',
      border: '1px solid #fecaca',
      color: '#991b1b',
      padding: '0.75rem 1rem',
      borderRadius: '0.5rem',
      marginTop: '1rem',
      fontSize: '0.875rem',
    },
    removeFile: {
      background: 'none',
      border: 'none',
      color: '#ef4444',
      cursor: 'pointer',
      fontSize: '0.875rem',
    },
  };

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>Upload IFC File</h1>
      <div style={styles.card}>
        <div
          style={styles.dropZone}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => document.getElementById('file-input')?.click()}
        >
          <div style={styles.dropZoneIcon}>📁</div>
          <div style={styles.dropZoneText}>
            Drag and drop your IFC file here
          </div>
          <div style={styles.dropZoneHint}>
            or click to browse (max 500 MB)
          </div>
          <input
            id="file-input"
            type="file"
            accept=".ifc"
            onChange={handleFileSelect}
            style={styles.fileInput}
          />
        </div>

        {file && (
          <div style={styles.fileInfo}>
            <div>
              <div style={styles.fileName}>{file.name}</div>
              <div style={styles.fileSize}>
                {(file.size / (1024 * 1024)).toFixed(2)} MB
              </div>
            </div>
            <button
              style={styles.removeFile}
              onClick={(e) => {
                e.stopPropagation();
                setFile(null);
              }}
            >
              Remove
            </button>
          </div>
        )}

        <div style={styles.formGroup}>
          <label style={styles.label}>Project Name (required)</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter project name"
            style={styles.input}
            disabled={isUploading}
          />
        </div>

        {error && <div style={styles.errorMessage}>{error}</div>}

        {isUploading && (
          <div style={styles.progressContainer}>
            <div style={styles.progressBar}>
              <div style={styles.progressFill} />
            </div>
            <div style={styles.progressText}>{uploadProgress}% uploaded</div>
          </div>
        )}

        <button
          style={styles.uploadBtn}
          onClick={handleUpload}
          disabled={isUploading || !file || !name.trim()}
        >
          {isUploading ? 'Uploading...' : 'Upload Project'}
        </button>
      </div>
    </div>
  );
}
