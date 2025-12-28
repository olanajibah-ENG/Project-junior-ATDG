import React from 'react';
import { Edit, Trash2, Calendar, User } from 'lucide-react';
import type { Project } from '../../services/api.service';
import LoadingSpinner from './LoadingSpinner';
import './ProjectList.css';

interface ProjectsListProps {
    projects: Project[] | null;
    isLoading: boolean;
    error: string | null;
    onEdit: (projectId: string) => void;
    onDelete: (projectId: string) => void;
}

const ProjectsList: React.FC<ProjectsListProps> = ({ projects, isLoading, error, onEdit, onDelete }) => {
    const formatDate = (dateString: string) => {
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'short', 
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch {
            return dateString;
        }
    };

    if (isLoading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '300px' }}>
                <LoadingSpinner size="large" message="Loading projects..." />
            </div>
        );
    }

    if (error) {
        return (
            <div className="error-message" style={{ padding: '20px', margin: '20px 0' }}>
                <strong>Error loading projects:</strong> {error}
            </div>
        );
    }

    if (!projects || projects.length === 0) {
        return (
            <div style={{ 
                textAlign: 'center', 
                padding: '60px 20px',
                color: 'var(--secondary-color)'
            }}>
                <h3 style={{ marginBottom: '10px', color: 'var(--text-color)' }}>No Projects Yet</h3>
                <p>Get started by creating your first project!</p>
            </div>
        );
    }

    return (
        <div className="projects-list-container">
            <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                marginBottom: '20px'
            }}>
                <h2 style={{ margin: 0, color: 'var(--text-color)' }}>
                    Your Projects ({projects.length})
                </h2>
            </div>
            
            <div className="projects-table-wrapper">
                <table className="projects-table">
                    <thead>
                        <tr>
                            <th>Title</th>
                            <th>Description</th>
                            <th>Owner</th>
                            <th>Created</th>
                            <th>Updated</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {projects.map(project => (
                            <tr key={project.id}>
                                <td className="project-title-cell">
                                    <strong>{project.title}</strong>
                                </td>
                                <td className="project-description-cell">
                                    {project.description || <em style={{ color: 'var(--secondary-color)' }}>No description</em>}
                                </td>
                                <td className="project-owner-cell">
                                    <User size={14} style={{ marginRight: '5px', verticalAlign: 'middle' }} />
                                    {project.username || `User ${project.user}`}
                                </td>
                                <td className="project-date-cell">
                                    <Calendar size={14} style={{ marginRight: '5px', verticalAlign: 'middle' }} />
                                    {formatDate(project.created_at)}
                                </td>
                                <td className="project-date-cell">
                                    <Calendar size={14} style={{ marginRight: '5px', verticalAlign: 'middle' }} />
                                    {formatDate(project.updated_at)}
                                </td>
                                <td className="project-actions-cell">
                                    <button 
                                        onClick={() => onEdit(project.id)} 
                                        title="Edit Project"
                                        className="btn-icon btn-edit"
                                    >
                                        <Edit size={16} />
                                    </button>
                                    <button 
                                        onClick={() => onDelete(project.id)} 
                                        title="Delete Project"
                                        className="btn-icon btn-delete"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default ProjectsList;