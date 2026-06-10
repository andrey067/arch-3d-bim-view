import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <div className="empty-state">
      <h1>We couldn&apos;t find that page</h1>
      <p>The link may be invalid, expired, or the project may not be published yet.</p>
      <Link to="/" className="button">
        Go to dashboard
      </Link>
    </div>
  );
}
