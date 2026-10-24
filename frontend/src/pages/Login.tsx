import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await axios.post('/api/login', { email, password });
      localStorage.setItem('token', res.data.token);
      navigate('/');
    } catch (err) {
      setError('ログインに失敗しました。');
    }
  };

  return (
    <div style={{ padding: '50px', maxWidth: '400px', margin: '0 auto' }}>
      <h2>Project Honjin - ログイン</h2>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
        <input 
          type="email" placeholder="Email (test@example.com)" 
          value={email} onChange={e => setEmail(e.target.value)} required 
        />
        <input 
          type="password" placeholder="Password (password)" 
          value={password} onChange={e => setPassword(e.target.value)} required 
        />
        <button type="submit" style={{ padding: '10px', background: '#333', color: '#fff' }}>
          入陣する
        </button>
      </form>
    </div>
  );
}
