import { Link, Outlet } from 'react-router-dom';
import styles from './AppShell.module.css';

export const AppShell = () => (
  <div className={styles.shell}>
    <header className={styles.header}>
      <Link to="/" className={styles.brand}>
        App 3D Viewer
      </Link>
      <nav className={styles.nav}>
        <Link to="/dashboard" className={styles.navLink}>
          Dashboard
        </Link>
      </nav>
    </header>
    <main className={styles.main}>
      <Outlet />
    </main>
  </div>
);
