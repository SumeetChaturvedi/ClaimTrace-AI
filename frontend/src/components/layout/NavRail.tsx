import { NavLink } from 'react-router-dom'
import styles from './NavRail.module.css'

export function NavRail() {
  return (
    <nav className={styles.rail} aria-label="Primary">
      <div className={styles.brand}>ClaimTrace</div>
      <NavLink to="/" end className={({ isActive }) => (isActive ? styles.activeLink : styles.link)}>
        Home
      </NavLink>
      <NavLink to="/projects" className={({ isActive }) => (isActive ? styles.activeLink : styles.link)}>
        Projects
      </NavLink>
    </nav>
  )
}
