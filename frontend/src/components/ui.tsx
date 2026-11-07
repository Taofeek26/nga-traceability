import type { ReactNode } from 'react'
import { NavLink as RouterNavLink } from 'react-router-dom'

/* Component library - ported 1:1 from templates/macros.html. Same markup,
   same class names from lba-ui.css, same conditional logic; only the
   templating engine changed. See html/frontend-backend-split-plan.html §5. */

export function Icon({ name, size = '', label = '' }: { name: string; size?: '' | 'sm' | 'lg'; label?: string }) {
  const cls = 'icon' + (size ? ` icon--${size}` : '')
  return label
    ? <svg className={cls} role="img" aria-label={label}><use href={`#i-${name}`} /></svg>
    : <svg className={cls} aria-hidden="true"><use href={`#i-${name}`} /></svg>
}

export function NavLink({ to, label, iconName }: { to: string; label: string; iconName: string }) {
  return (
    <RouterNavLink to={to} className={({ isActive }) => 'nav__link' + (isActive ? ' is-active' : '')} end>
      <Icon name={iconName} /><span>{label}</span>
    </RouterNavLink>
  )
}

export function PageHeader({ title, desc = '', eyebrow = '', children }: {
  title: string; desc?: string; eyebrow?: string; children?: ReactNode
}) {
  return (
    <header className="page-header">
      <div>
        {eyebrow && <div className="page-header__eyebrow">{eyebrow}</div>}
        <h1 className="page-header__title">{title}</h1>
        {desc && <p className="page-header__desc">{desc}</p>}
      </div>
      {children && <div className="page-header__actions">{children}</div>}
    </header>
  )
}

export function StatTile({ label, value, unit = '', iconName = '', meta = '', tone = '', highlight = false }: {
  label: string; value: ReactNode; unit?: string; iconName?: string; meta?: string; tone?: string; highlight?: boolean
}) {
  return (
    <div className={'stat' + (highlight ? ' stat--highlight' : '')}>
      <div className="stat__top">
        <span className="stat__label">{label}</span>
        {iconName && <span className={'stat__icon' + (tone ? ` stat__icon--${tone}` : '')}><Icon name={iconName} size="sm" /></span>}
      </div>
      <div className="stat__value">{value}{unit && <span className="stat__unit">{unit}</span>}</div>
      {meta && <div className="stat__meta">{meta}</div>}
    </div>
  )
}

const ALERT_ICONS: Record<string, string> = {
  success: 'check-circle', error: 'alert-circle', warning: 'alert-triangle', info: 'info',
}

export function Alert({ message, kind = 'success', title = '' }: { message: string; kind?: string; title?: string }) {
  return (
    <div className={`alert alert--${kind}`} role={kind === 'error' ? 'alert' : 'status'}>
      <Icon name={ALERT_ICONS[kind]} />
      <div className="alert__body">
        {title && <div className="alert__title">{title}</div>}
        <p>{message}</p>
      </div>
    </div>
  )
}

export function FarmerStatusBadge({ active, pct }: { active: boolean; pct: number }) {
  if (!active) return <span className="badge badge--inactive">Inactive</span>
  if (pct >= 100) return <span className="badge badge--full">At limit</span>
  if (pct >= 90) return <span className="badge badge--warn">Near limit</span>
  return <span className="badge badge--ok">OK</span>
}

export function LotStatusBadge({ status }: { status: string }) {
  if (status === 'accepted') return <span className="badge badge--ok">Accepted</span>
  if (status === 'rejected') return <span className="badge badge--full">Rejected</span>
  return <span className="badge badge--warn">Pending review</span>
}

export function ProgressBar({ pct, size = '' }: { pct: number; size?: '' | 'sm' }) {
  const tone = pct >= 100 ? 'danger' : pct >= 90 ? 'warn' : ''
  const cls = 'progress' + (tone ? ` progress--${tone}` : '') + (size ? ` progress--${size}` : '')
  return (
    <div className={cls} role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100}>
      <div className="progress__bar" style={{ width: `${Math.min(pct, 100)}%` }} />
    </div>
  )
}

export function MiniMeter({ pct }: { pct: number }) {
  return (
    <div className="mini-meter">
      <ProgressBar pct={pct} size="sm" />
      <span className="mini-meter__pct">{Math.round(pct)}%</span>
    </div>
  )
}

export function Avatar({ fullName, size = '', tone = '' }: { fullName: string; size?: string; tone?: string }) {
  const parts = (fullName || '?').split(' ')
  const initials = (parts[0]?.[0] || '?') + (parts.length > 1 ? parts[parts.length - 1]?.[0] ?? '' : '')
  const cls = 'avatar' + (size ? ` avatar--${size}` : '') + (tone ? ` avatar--${tone}` : '')
  return <span className={cls} aria-hidden="true">{initials}</span>
}

export function EmptyState({ title, text = '', iconName = 'package', actionHref = '', actionLabel = '' }: {
  title: string; text?: string; iconName?: string; actionHref?: string; actionLabel?: string
}) {
  return (
    <div className="empty-state">
      <div className="empty-state__icon"><Icon name={iconName} /></div>
      <div className="empty-state__title">{title}</div>
      {text && <p className="empty-state__text">{text}</p>}
      {actionHref && (
        <a className="btn btn--primary" href={actionHref}><Icon name="plus" />{actionLabel}</a>
      )}
    </div>
  )
}

export function BackLink({ href, label }: { href: string; label: string }) {
  return (
    <a className="link-arrow" href={href} style={{ marginBottom: 'var(--space-4)', display: 'inline-flex' }}>
      <Icon name="arrow-left" size="sm" />{label}
    </a>
  )
}
