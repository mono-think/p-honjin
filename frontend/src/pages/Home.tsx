import { useNavigate } from 'react-router-dom';

export default function Home() {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  return (
    <div style={{ padding: '50px', textAlign: 'center' }}>
      <h1>本陣へようこそ</h1>
      <p>フロントエンドとバックエンドの連携に成功しました。</p>
      <button onClick={handleLogout} style={{ marginTop: '20px', padding: '10px' }}>
        ログアウト（退陣）
      </button>
    </div>
  );
}
