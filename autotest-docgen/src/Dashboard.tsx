
import React, { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, Settings, PlusCircle, List, Home } from 'lucide-react';

import { ApiService, type Project, type PaginatedResponse, type CreateProjectData, type UpdateProjectData, formatApiError } from './services/api.service'; 
import { AuthContext } from './context/AuthContext';
import ProjectsList from './compoents/ProjectCutomizationModal/ProjectList';
import { useAlert } from './compoents/Alert/useAlert';
import './Dashboard.css';
import './compoents/Modal/Modal.css';

// ----------------------------------------------------
// مكون نموذج إنشاء المشروع (Modal)
// ----------------------------------------------------
const CreateProjectForm: React.FC<{ 
    onSubmit: (data: CreateProjectData) => void;
    onClose: () => void;
    isLoading: boolean;
    apiError: string | null;
}> = ({ onSubmit, onClose, isLoading, apiError }) => {
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [validationError, setValidationError] = useState<string | null>(null);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setValidationError(null);
        
        if (!title.trim()) {
            setValidationError('Title is required.');
            return;
        }
        
        if (title.trim().length > 255) {
            setValidationError('Title must be 255 characters or less.');
            return;
        }
        
        onSubmit({ title: title.trim(), description: description.trim() });
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <h3>Create New Project</h3>
                {(apiError || validationError) && (
                    <div className="error-message" style={{ marginBottom: '15px' }}>
                        {apiError || validationError}
                    </div>
                )}
                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="title">Title *</label>
                        <input
                            type="text"
                            id="title"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            placeholder="Enter project title"
                            disabled={isLoading}
                            required
                            maxLength={255}
                        />
                    </div>
                    <div className="form-group">
                        <label htmlFor="description">Description</label>
                        <textarea
                            id="description"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder="Enter project description (optional)"
                            disabled={isLoading}
                            rows={4}
                        />
                    </div>
                    <div className="modal-actions">
                        <button type="submit" disabled={isLoading} className="btn-primary">
                            {isLoading ? 'Creating...' : 'Create Project'}
                        </button>
                        <button type="button" onClick={onClose} disabled={isLoading} className="btn-secondary">
                            Cancel
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

// Edit Project Form Component
const EditProjectForm: React.FC<{
    project: Project;
    onSubmit: (data: UpdateProjectData) => void;
    onClose: () => void;
    isLoading: boolean;
    apiError: string | null;
}> = ({ project, onSubmit, onClose, isLoading, apiError }) => {
    const [title, setTitle] = useState(project.title);
    const [description, setDescription] = useState(project.description);
    const [validationError, setValidationError] = useState<string | null>(null);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setValidationError(null);
        
        if (!title.trim()) {
            setValidationError('Title is required.');
            return;
        }
        
        if (title.trim().length > 255) {
            setValidationError('Title must be 255 characters or less.');
            return;
        }
        
        onSubmit({ title: title.trim(), description: description.trim() });
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <h3>Edit Project</h3>
                {(apiError || validationError) && (
                    <div className="error-message" style={{ marginBottom: '15px' }}>
                        {apiError || validationError}
                    </div>
                )}
                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="edit-title">Title *</label>
                        <input
                            type="text"
                            id="edit-title"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            placeholder="Enter project title"
                            disabled={isLoading}
                            required
                            maxLength={255}
                        />
                    </div>
                    <div className="form-group">
                        <label htmlFor="edit-description">Description</label>
                        <textarea
                            id="edit-description"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder="Enter project description (optional)"
                            disabled={isLoading}
                            rows={4}
                        />
                    </div>
                    <div className="modal-actions">
                        <button type="submit" disabled={isLoading} className="btn-primary">
                            {isLoading ? 'Updating...' : 'Update Project'}
                        </button>
                        <button type="button" onClick={onClose} disabled={isLoading} className="btn-secondary">
                            Cancel
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

// ----------------------------------------------------
// المكون الرئيسي Dashboard
// ----------------------------------------------------

const Dashboard = () => {
    const navigate = useNavigate();
    const { logout, user } = useContext(AuthContext);
    const apiService = new ApiService(); // Create instance once
    const { showAlert, showConfirm, AlertComponent } = useAlert();

    // Main dashboard states
    const [activeAction, setActiveAction] = useState('projects');
    const [projects, setProjects] = useState<Project[] | null>(null);
    const [isProjectsLoading, setIsProjectsLoading] = useState(false);
    const [projectsError, setProjectsError] = useState<string | null>(null);
    
    // Create modal states
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [createError, setCreateError] = useState<string | null>(null);
    
    // Edit modal states
    const [showEditModal, setShowEditModal] = useState(false);
    const [editingProject, setEditingProject] = useState<Project | null>(null);
    const [isUpdating, setIsUpdating] = useState(false);
    const [updateError, setUpdateError] = useState<string | null>(null);
    
    // ----------------------------------------------------
    // دوال API
    // ----------------------------------------------------
    
    // Fetch projects
    const fetchProjects = async () => {
        setIsProjectsLoading(true);
        setProjectsError(null);
        try {
            const response: PaginatedResponse<Project> = await apiService.getProjects(); 
            if (response && Array.isArray(response.results)) {
                setProjects(response.results); 
            } else {
                console.error("API response missing 'results' array or invalid structure:", response);
                setProjectsError('Received invalid data from server structure.');
            }
        } catch (err: any) {
            console.error('Failed to fetch projects:', err);
            setProjectsError(formatApiError(err));
            setProjects([]);
        } finally {
            setIsProjectsLoading(false);
        }
    };
    
    // Create project
    const handleCreateProject = async (projectData: CreateProjectData) => {
        setIsSubmitting(true);
        setCreateError(null);
        try {
            await apiService.createProject(projectData);
            setShowCreateModal(false);
            // Refresh the projects list after successful creation
            await fetchProjects();
            // Show success alert
            await showAlert({
                type: 'success',
                title: 'Success!',
                message: 'Project created successfully!',
            });
        } catch (err: any) {
            console.error('Project creation failed:', err);
            const errorMessage = formatApiError(err);
            setCreateError(errorMessage);
            // Show error alert
            await showAlert({
                type: 'error',
                title: 'Error',
                message: errorMessage,
            });
        } finally {
            setIsSubmitting(false);
        }
    };
    
    // Delete project
    const handleDeleteProject = async (id: string) => {
        const confirmed = await showConfirm({
            title: 'Delete Project',
            message: 'Are you sure you want to delete this project? This action cannot be undone.',
            confirmText: 'Delete',
            cancelText: 'Cancel',
        });
        
        if (!confirmed) return;
        
        try {
            await apiService.deleteProject(id);
            await fetchProjects();
            // Show success alert
            await showAlert({
                type: 'success',
                title: 'Success!',
                message: 'Project deleted successfully!',
            });
        } catch (err: any) {
            console.error('Deletion failed:', err);
            const errorMessage = formatApiError(err);
            setProjectsError(errorMessage);
            // Show error alert
            await showAlert({
                type: 'error',
                title: 'Error',
                message: errorMessage,
            });
        }
    };
    
    // Edit project - open modal with project data
    const handleEditProject = (id: string) => {
        const project = projects?.find(p => p.id === id);
        if (project) {
            setEditingProject(project);
            setUpdateError(null);
            setShowEditModal(true);
        }
    };
    
    // Update project
    const handleUpdateProject = async (projectData: UpdateProjectData) => {
        if (!editingProject) return;
        
        setIsUpdating(true);
        setUpdateError(null);
        try {
            await apiService.updateProject(editingProject.id, projectData);
            setShowEditModal(false);
            setEditingProject(null);
            await fetchProjects();
            // Show success alert
            await showAlert({
                type: 'success',
                title: 'Success!',
                message: 'Project updated successfully!',
            });
        } catch (err: any) {
            console.error('Project update failed:', err);
            const errorMessage = formatApiError(err);
            setUpdateError(errorMessage);
            // Show error alert
            await showAlert({
                type: 'error',
                title: 'Error',
                message: errorMessage,
            });
        } finally {
            setIsUpdating(false);
        }
    };
    
    // ----------------------------------------------------
    // منطق التنفيذ
    // ----------------------------------------------------
    
    useEffect(() => {
        if (activeAction === 'projects') {
            fetchProjects();
        }
    }, [activeAction]); 

    const handleActionClick = (action: string) => {
        if (action === 'add-project') {
            // Open modal without changing active view - stay on projects list
            setCreateError(null);
            setShowCreateModal(true);
        } else if (action === 'logout') {
            logout();
            navigate('/');
        } else {
            // For other actions (like 'projects', 'settings'), change active view
            setActiveAction(action);
        }
    };
    
    const renderMainContent = () => {
        switch (activeAction) {
            case 'projects':
                return (
                    // 👈 استخدام المكون المنفصل هنا
                    <ProjectsList 
                        projects={projects} 
                        isLoading={isProjectsLoading}
                        error={projectsError}
                        onEdit={handleEditProject} 
                        onDelete={handleDeleteProject} 
                    />
                );
            case 'settings':
                return <h2>Settings Page</h2>;
            default:
                return <h2>Welcome to AutoTest & DocGen Dashboard!</h2>;
        }
    }

    return (
        <div className="dashboard-layout">
            {/* Top header */}
            <header className="header">
                <div className="logo">
                    <Home size={24} style={{ marginRight: '10px', verticalAlign: 'middle' }} />
                    AutoTest & DocGen
                </div>
                <div className="user-info">
                    {user && (
                        <span className="user-name" style={{ marginRight: '15px', color: 'var(--text-color)' }}>
                            {user.username}
                        </span>
                    )}
                    <a href="#" onClick={(e) => { e.preventDefault(); handleActionClick('settings'); }} className="header-link">
                        <Settings size={18} style={{ marginRight: '5px' }} /> Settings
                    </a>
                    <a href="#" onClick={(e) => { e.preventDefault(); handleActionClick('logout'); }} className="header-link">
                        <LogOut size={18} style={{ marginRight: '5px' }} /> Log Out
                    </a>
                </div>
            </header>

            {/* Sidebar */}
            <aside className="sidebar">
                <nav>
                    <a 
                        href="#" 
                        onClick={(e) => { 
                            e.preventDefault(); 
                            handleActionClick('projects'); 
                        }} 
                        className={activeAction === 'projects' ? 'active' : ''}
                    >
                        <List size={18} style={{ marginRight: '10px', verticalAlign: 'middle' }} /> 
                        Projects List
                    </a>
                    
                    <a 
                        href="#" 
                        onClick={(e) => { 
                            e.preventDefault(); 
                            handleActionClick('add-project'); 
                        }}
                    >
                        <PlusCircle size={18} style={{ marginRight: '10px', verticalAlign: 'middle' }} /> 
                        New Project
                    </a>
                </nav>
            </aside>

            {/* Main Content */}
            <main className="main-content">
                {renderMainContent()}
            </main>
            
            {/* Create Project Modal */}
            {showCreateModal && (
                <CreateProjectForm 
                    onSubmit={handleCreateProject} 
                    onClose={() => {
                        setShowCreateModal(false);
                        setCreateError(null);
                    }}
                    isLoading={isSubmitting}
                    apiError={createError}
                />
            )}
            
            {/* Edit Project Modal */}
            {showEditModal && editingProject && (
                <EditProjectForm
                    project={editingProject}
                    onSubmit={handleUpdateProject}
                    onClose={() => {
                        setShowEditModal(false);
                        setEditingProject(null);
                        setUpdateError(null);
                    }}
                    isLoading={isUpdating}
                    apiError={updateError}
                />
            )}
            
            {/* Alert Component */}
            {AlertComponent}
        </div>
    );
};

export default Dashboard;