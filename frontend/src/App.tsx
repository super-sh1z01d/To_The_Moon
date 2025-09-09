import { Link, NavLink, Route, Routes } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Settings from './pages/Settings'
import TokenDetail from './pages/TokenDetail'

export default function App(){
  return (
    <div className="container">
      <header>
        <h1><Link to="/">To The Moon</Link></h1>
        <nav>
          <NavLink to="/" end className={({isActive})=> isActive ? 'active' : ''}>Дашборд</NavLink>
          <NavLink to="/settings" className={({isActive})=> isActive ? 'active' : ''}>Настройки</NavLink>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Dashboard/>} />
          <Route path="/settings" element={<Settings/>} />
          <Route path="/token/:mint" element={<TokenDetail/>} />
          <Route path="*" element={<div>Страница не найдена</div>} />
        </Routes>
      </main>
    </div>
  )
}
