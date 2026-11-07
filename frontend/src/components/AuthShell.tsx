import type { ReactNode } from 'react'
import { Icon } from './ui'

/* Ported from templates/auth_base.html - same split-screen layout, same
   feature list copy. */
export default function AuthShell({
  heading, desc, children, switchLink,
}: { heading: string; desc: string; children: ReactNode; switchLink: ReactNode }) {
  return (
    <div className="auth">
      <aside className="auth__aside">
        <a className="brand" href="/login">
          <span className="brand__mark"><Icon name="leaf" /></span>
          <span className="brand__text">
            <span className="brand__name">JIMGAF</span>
            <span className="brand__sub">Traceability</span>
          </span>
        </a>
        <h2 className="auth__headline">Every kilo, traced back to a <em>registered farmer</em>.</h2>
        <p className="auth__lead">Turn a broker lot's total weight and receipt range into a quota-respecting farmer list — ready to export in seconds.</p>
        <p className="auth__foot">JIMGAF Traceability</p>
      </aside>

      <main className="auth__main">
        <div className="auth__panel">
          <div className="auth__mobile-brand">
            <a className="brand" href="/login">
              <span className="brand__mark"><Icon name="leaf" /></span>
              <span className="brand__text"><span className="brand__name">JIMGAF</span><span className="brand__sub">Traceability</span></span>
            </a>
          </div>
          <h1 className="auth__title">{heading}</h1>
          <p className="auth__desc">{desc}</p>
          {children}
          <p className="auth__switch">{switchLink}</p>
        </div>
      </main>
    </div>
  )
}
