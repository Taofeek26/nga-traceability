import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Icon, NavLink as UiNavLink } from './ui'
import AccountMenu from './AccountMenu'

const COLLAPSE_KEY = 'lba_sidebar_collapsed'

/* Ported from templates/base.html - same sidebar sections, same
   role-gated links. The account block moved from the sidebar footer into
   a topbar dropdown (AccountMenu) to match the requested layout. */
export default function AppShell() {
  const { user } = useAuth()
  const location = useLocation()
  const role = user?.role
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem(COLLAPSE_KEY) === '1' } catch { return false }
  })

  useEffect(() => {
    try { localStorage.setItem(COLLAPSE_KEY, collapsed ? '1' : '0') } catch { /* ignore */ }
  }, [collapsed])

  return (
    <div className="app">
      <input type="checkbox" id="nav-toggle" className="nav-toggle" aria-label="Toggle navigation" />

      <aside className={'sidebar' + (collapsed ? ' sidebar--collapsed' : '')} aria-label="Main navigation">
        <a className="brand" href="/">
          <span className="brand__mark"><Icon name="leaf" /></span>
          <span className="brand__text">
            <span className="brand__name">JIMGAF</span>
            <span className="brand__sub">Traceability</span>
          </span>
        </a>

        <nav className="nav">
          <div className="nav__section">Overview</div>
          <UiNavLink to="/" label="Dashboard" iconName="dashboard" />

          <div className="nav__section">Traceability</div>
          {(role === 'admin' || role === 'to') && <UiNavLink to="/lots/new" label="New Lot" iconName="plus-circle" />}
          <UiNavLink to="/lots" label="Lot History" iconName="history" />
          <UiNavLink to="/farmers" label="Farmers" iconName="users" />
          <UiNavLink to="/documents" label="Documents" iconName="file-sheet" />

          {role === 'admin' && (
            <>
              <div className="nav__section">Administration</div>
              <UiNavLink to="/upload" label="Master Data" iconName="database" />
              <UiNavLink to="/users" label="Team" iconName="shield" />
              <UiNavLink to="/audit-log" label="Audit Log" iconName="history" />
              <UiNavLink to="/settings" label="Settings" iconName="settings" />
            </>
          )}
        </nav>

        <button
          type="button"
          className="sidebar__collapse-toggle"
          onClick={() => setCollapsed((c) => !c)}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <Icon name={collapsed ? 'arrow-right' : 'arrow-left'} size="sm" />
          <span>Collapse</span>
        </button>
      </aside>
      <label htmlFor="nav-toggle" className="sidebar-overlay" aria-hidden="true" />

      <div className={'main' + (collapsed ? ' main--sidebar-collapsed' : '')}>
        <header className="topbar">
          <label htmlFor="nav-toggle" className="btn btn--ghost btn--icon btn--sm topbar__menu" aria-label="Open menu">
            <Icon name="menu" />
          </label>
          <nav className="breadcrumbs" aria-label="Breadcrumb">
            <a href="/">Home</a>
          </nav>
          <div className="topbar__end">
            <AccountMenu />
          </div>
        </header>
        <main className="content">
          <Outlet key={location.pathname} />
        </main>
      </div>
    </div>
  )
}
