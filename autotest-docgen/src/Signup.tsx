import React, { useState } from 'react';
import { useAuth } from './context/AuthContext';
import apiService from './services/api.service';
import { Eye, EyeOff, Check, AlertCircle, LogIn, UserPlus, Mail, User, Lock, Loader2 } from 'lucide-react';
import './Signup.css';

export default function SignUp() {
  const [isLoginView, setIsLoginView] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [loginIdentifier, setLoginIdentifier] = useState(''); // username or email
  const [signUpEmail, setSignUpEmail] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [agreeToTerms, setAgreeToTerms] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const { login } = useAuth();

  // simple field validation for UI only
  const validateField = (field: string, value: string): string => {
    if (field === 'username' && value.length < 2) return 'User Name must be at least 2 characters';
    if (field === 'loginIdentifier') {
      if (!value) return 'Username or email is required';
      if (value.includes('@')) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) ? '' : 'Invalid email address';
      }
      return value.length >= 2 ? '' : 'Username must be at least 2 characters';
    }
    if (field === 'signUpEmail' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) return 'Invalid email address';
    if (field === 'password' && value.length < 6) return 'Password must be at least 6 characters';
    return '';
  };

  const handleFieldChange = (field: string, value: string) => {
    switch (field) {
      case 'username': setFullName(value); break;
      case 'loginIdentifier': setLoginIdentifier(value); break;
      case 'signUpEmail': setSignUpEmail(value); break;
      case 'password': setPassword(value); break;
    }
    if (fieldErrors[field]) setFieldErrors(prev => ({ ...prev, [field]: '' }));
    if (error) setError('');
  };

  const validateForm = () => {
    const errors: Record<string, string> = {};
    if (isLoginView) {
        const v = loginIdentifier.trim();
        const err = validateField('loginIdentifier', v);
        if (err) { errors.loginIdentifier = err; }
    } else {
        if (!fullName.trim()) { errors.fullName = 'Full name is required'; } 
        else if (validateField('fullName', fullName)) { errors.fullName = validateField('fullName', fullName); }
 
        if (!signUpEmail.trim()) { errors.signUpEmail = 'Email is required'; } 
        else if (validateField('signUpEmail', signUpEmail)) { errors.signUpEmail = validateField('signUpEmail', signUpEmail); }
        
        if (!agreeToTerms) { errors.agreeToTerms = 'You must agree to terms and conditions'; }
    }
    if (!password) { errors.password = 'Password is required'; } 
    else if (validateField('password', password)) { errors.password = validateField('password', password); }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (isLoading) return;
    setError('');
    setSuccess('');
    if(!validateForm()) return;
    setIsLoading(true);
    try {
      if (isLoginView) {
        await login({ username: loginIdentifier.trim(), password: password });
        setSuccess('Welcome back! Redirecting...');
      } else {
        await apiService.auth.signup({ 
          username: fullName.trim().replace(/\s+/g, '').toLowerCase() || loginIdentifier.trim(),
          password: password,
          email: signUpEmail.trim()
        });
        setSuccess('Account created successfully! Please sign in.');
        setTimeout(() => { setIsLoginView(true); setPassword(''); setSuccess(''); }, 2000);
      }
    } catch (err: any) {
        const errorMessage = err.response?.data?.detail || err.message || 'Authentication failed. Please check your details.';
        setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTabSwitch = (loginView: boolean) => {
    setIsLoginView(loginView);
    setError('');
    setSuccess('');
    setFieldErrors({});
    if (loginView) { setSignUpEmail(''); setFullName(''); setAgreeToTerms(false); setLoginIdentifier(''); } 
    else { setLoginIdentifier(''); setRememberMe(false); }
    setPassword('');
  };

  const getFieldClassName = (field: string) => {
    if (fieldErrors[field]) return 'error';
    if (
      (field === 'username' && fullName) ||
      (field === 'loginIdentifier' && loginIdentifier) ||
      (field === 'password' && password) ||
      (field === 'signUpEmail' && signUpEmail)
    ) return 'success';
    return '';
  };

  return (
    <div className="signup-container">
      <div className="signup-card">
        <div className="signup-header">
          <h1>AutoTest & DocGen Manager</h1>
          <p>{isLoginView ? 'Welcome back! Please sign in to your account' : 'Create your account to start using the intelligent system'}</p>
        </div>

        <div className="tab-buttons">
          <button 
            className={isLoginView ? 'active' : ''} 
            onClick={() => handleTabSwitch(true)} 
            type="button"
            disabled={isLoading}
          >
            <LogIn size={18} /> Sign In
          </button>
          <button 
            className={!isLoginView ? 'active' : ''} 
            onClick={() => handleTabSwitch(false)} 
            type="button"
            disabled={isLoading}
          >
            <UserPlus size={18} /> Sign Up
          </button>
        </div>

        {error && (
          <div className="error-message">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}
        {success && (
          <div className="success-message">
            <Check size={18} />
            <span>{success}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="signup-form">
          {!isLoginView && (
            <div className="form-group">
              <label htmlFor="username">Full Name</label>
              <div className="input-wrapper">
                <User size={18} className="input-icon" />
                <input 
                  type="text" 
                  id="username" 
                  value={fullName} 
                  onChange={(e) => handleFieldChange('username', e.target.value)} 
                  placeholder="Enter your full name" 
                  className={getFieldClassName('username')} 
                  disabled={isLoading} 
                  required
                />
              </div>
              {fieldErrors['username'] && (
                <small className="field-error">{fieldErrors['username']}</small>
              )}
            </div>
          )}

          <div className="form-group">
            <label htmlFor={isLoginView ? 'loginIdentifier' : 'email'}>
              {isLoginView ? 'Username or Email' : 'Email'}
            </label>
            {isLoginView ? (
              <>
                <div className="input-wrapper">
                  <Mail size={18} className="input-icon" />
                  <input 
                    type="text" 
                    id="loginIdentifier" 
                    value={loginIdentifier} 
                    onChange={(e) => handleFieldChange('loginIdentifier', e.target.value)} 
                    placeholder="Enter username or email" 
                    className={getFieldClassName('loginIdentifier')} 
                    disabled={isLoading} 
                    required
                  />
                </div>
                {fieldErrors['loginIdentifier'] && (
                  <small className="field-error">{fieldErrors['loginIdentifier']}</small>
                )}
              </>
            ) : (
              <>
                <div className="input-wrapper">
                  <Mail size={18} className="input-icon" />
                  <input 
                    type="email" 
                    id="email" 
                    value={signUpEmail} 
                    onChange={(e) => handleFieldChange('signUpEmail', e.target.value)} 
                    placeholder="Enter your email address" 
                    className={getFieldClassName('signUpEmail')} 
                    disabled={isLoading} 
                    required
                  />
                </div>
                {fieldErrors['signUpEmail'] && (
                  <small className="field-error">{fieldErrors['signUpEmail']}</small>
                )}
              </>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <div className="input-wrapper password-input">
              <Lock size={18} className="input-icon" />
              <input 
                type={showPassword ? 'text' : 'password'} 
                id="password" 
                value={password} 
                onChange={(e) => handleFieldChange('password', e.target.value)} 
                placeholder="Enter your password" 
                className={getFieldClassName('password')} 
                disabled={isLoading} 
                required
              />
              <button 
                type="button" 
                className="password-toggle" 
                onClick={() => setShowPassword(!showPassword)} 
                disabled={isLoading}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
            {fieldErrors['password'] && (
              <small className="field-error">{fieldErrors['password']}</small>
            )}
          </div>

          <div className="form-options">
            {isLoginView ? (
              <>
                <label className="checkbox-label">
                  <input type="checkbox" checked={rememberMe} onChange={(e) => setRememberMe(e.target.checked)} disabled={isLoading}/> Remember me
                </label>
                <a href="#" className="forgot-password" onClick={(e) => e.preventDefault()}>Forgot password?</a>
              </>
            ) : (
              <label className="checkbox-label">
                <input type="checkbox" checked={agreeToTerms} onChange={(e) => setAgreeToTerms(e.target.checked)} disabled={isLoading} required/> I agree to the terms and conditions
              </label>
            )}
          </div>

          {fieldErrors['agreeToTerms'] && (
            <small className="field-error" style={{ marginTop: '-10px', marginBottom: '10px', display: 'block' }}>
              {fieldErrors['agreeToTerms']}
            </small>
          )}

          <button type="submit" className={`submit-button ${isLoading ? 'loading' : ''}`} disabled={isLoading}>
            {isLoading ? (
              <>
                <Loader2 size={18} className="button-spinner" />
                Processing...
              </>
            ) : (
              isLoginView ? 'Sign In' : 'Sign Up'
            )}
          </button>
        </form>

        <div className="signup-footer">
          <p>
            {isLoginView ? "Don't have an account? " : "Already have an account? "}
            <button className="link-button" onClick={() => handleTabSwitch(!isLoginView)} type="button" disabled={isLoading}>
              {isLoginView ? 'Sign up' : 'Sign in here'}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}